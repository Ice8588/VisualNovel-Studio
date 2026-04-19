"""Phase 3 ADR-003：CAPTURE_MODE 下多立繪必須照常渲染。

建立一個左槽紅色 / 右槽藍色的 mock Project，用 v2 webengine capture 截出單幀，
用 PIL 在左 1/4 / 右 3/4 位置抽色斷言。

若 QtWebEngine 在此環境不可用（offscreen + GPU 不支援、Vulkan 初始化失敗等），
skip 並交由 user 手動驗收 MP4 端到端。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image


# 紅/藍立繪是大色塊；避免透明邊緣誤判
LEFT_COLOR = (220, 40, 40)
RIGHT_COLOR = (40, 80, 220)


def _build_project_with_two_sprites(assets_dir: Path):
    from src.core.models import (
        Character,
        Costume,
        Dialogue,
        Project,
        Scene,
        SpriteVariant,
        StageSegment,
    )
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 左立繪：整張紅色，右立繪：整張藍色（含 alpha 以通過 png convert）
    Image.new("RGBA", (256, 512), LEFT_COLOR + (255,)).save(assets_dir / "left.png")
    Image.new("RGBA", (256, 512), RIGHT_COLOR + (255,)).save(assets_dir / "right.png")

    proj = Project(
        title="MultiSprite",
        characters=[
            Character(
                name="L", name_color="#FF0000",
                costumes=[Costume(name="d", expressions=[SpriteVariant("n", "left.png")])],
            ),
            Character(
                name="R", name_color="#0000FF",
                costumes=[Costume(name="d", expressions=[SpriteVariant("n", "right.png")])],
            ),
        ],
    )
    scene = Scene(
        id="s1",
        dialogues=[Dialogue(type="dialogue", text="hi", character="L")],
    )
    scene.stage_left.append(StageSegment(0, 0, "L", costume="d", sprite="n"))
    scene.stage_right.append(StageSegment(0, 0, "R", costume="d", sprite="n"))
    proj.scenes.append(scene)
    # 讓 _resolve_asset 找得到：project_path 指向 assets_dir 的上層
    proj.project_path = assets_dir.parent / "proj.vnsproj"
    return proj


def _within_tolerance(actual, expected, tol=60):
    return all(abs(a - e) <= tol for a, e in zip(actual[:3], expected[:3]))


def _webengine_available() -> bool:
    """環境檢查：能否建立 QWebEngineView + 最小渲染。"""
    if sys.platform.startswith("win"):
        return True  # 假定 Windows 開發環境可用
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    except Exception:
        return False
    # Linux offscreen + 無 GPU：QtWebEngine 常會 fallback 成 SwiftShader 並 flaky；
    # 以環境變數 VNSTUDIO_E2E=1 顯式啟用才跑。
    import os
    return os.environ.get("VNSTUDIO_E2E") == "1"


requires_webengine = pytest.mark.skipif(
    not _webengine_available(),
    reason="QtWebEngine 端到端截圖測試：設 VNSTUDIO_E2E=1 才執行；平時由 user 手動跑 MP4 驗收。",
)


@requires_webengine
def test_capture_renders_both_stage_sprites(qapp, tmp_path):
    """左槽 L + 右槽 R 同時渲染：左 1/4 點樣本應含紅色、右 3/4 點樣本應含藍色。"""
    from src.ui.webengine_capture import WebEngineVideoExporter

    assets_dir = tmp_path / "assets"
    proj = _build_project_with_two_sprites(assets_dir)

    out_mp4 = tmp_path / "out.mp4"
    captured_frame: dict[str, Path] = {}

    # 攔 _encode_video：跳過 ffmpeg，只把第 1 幀 PNG 搬出來供檢查
    original_capture = WebEngineVideoExporter._capture_all_frames

    def wrapped_capture(self, view, temp_dir, progress_callback, total):
        result = original_capture(self, view, temp_dir, progress_callback, total)
        # 複製第一幀到 tmp_path（稍後 rmtree 就清掉原位置）
        first_frame_src = temp_dir / "frame_000000.png"
        if first_frame_src.exists():
            dst = tmp_path / "captured_frame.png"
            dst.write_bytes(first_frame_src.read_bytes())
            captured_frame["path"] = dst
        return result

    with patch.object(WebEngineVideoExporter, "_capture_all_frames", wrapped_capture), \
         patch.object(WebEngineVideoExporter, "_encode_video", lambda *a, **kw: None), \
         patch("src.core.ffmpeg_manager.ensure_ffmpeg_or_raise", return_value=Path("ffmpeg")):
        exporter = WebEngineVideoExporter(proj, out_mp4, resolution=(1280, 720))
        exporter.export()

    assert "path" in captured_frame, "截幀未產生 frame_000000.png"
    img = Image.open(captured_frame["path"]).convert("RGB")
    w, h = img.size
    # 取中高度的 1/4 與 3/4 位置
    left_px = img.getpixel((w // 4, h // 2))
    right_px = img.getpixel(((3 * w) // 4, h // 2))

    assert _within_tolerance(left_px, LEFT_COLOR), (
        f"左側期望紅色 ~{LEFT_COLOR}，實際 {left_px}"
    )
    assert _within_tolerance(right_px, RIGHT_COLOR), (
        f"右側期望藍色 ~{RIGHT_COLOR}，實際 {right_px}"
    )
