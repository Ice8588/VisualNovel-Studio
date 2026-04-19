"""單一 HTML 導出：所有素材內嵌為 Base64，產生一個可獨立運行的 .html 檔案。"""

from __future__ import annotations

import base64
import json
import mimetypes
import sys
import tempfile
from pathlib import Path

from src.core.models import Project


def _get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent


ENGINE_DIR = _get_base_path() / "src" / "engine"

# 30 MB 閾值（警告用）
SIZE_THRESHOLD = 30 * 1024 * 1024


def estimate_export_size(project: Project) -> int:
    """估算單一 HTML 導出後的大小（bytes）。

    Base64 編碼使資料膨脹約 1.37 倍，加上 HTML/JS/CSS 開銷。
    """
    total = 0
    assets_dir = _get_assets_dir(project)
    if assets_dir:
        for category in ("backgrounds", "sprites", "music"):
            for filename in project.assets.get(category, []):
                src = assets_dir / filename
                if src.exists():
                    total += src.stat().st_size
    # Base64 膨脹 + HTML/JS 開銷
    return int(total * 1.37) + 50_000


def export_single_html(
    project: Project,
    output_path: Path,
    optimize_images: bool = True,
    max_image_size: int = 1920,
) -> None:
    """將專案打包為單一 .html 檔案，所有素材內嵌為 Base64 data URI。

    Args:
        project: 專案資料。
        output_path: 輸出 .html 路徑。
        optimize_images: 是否壓縮圖片（WebP + 縮放）。
        max_image_size: 圖片長邊最大像素。
    """
    output_path = Path(output_path)

    # 讀取 engine 檔案
    index_html = (ENGINE_DIR / "index.html").read_text(encoding="utf-8")
    engine_js = (ENGINE_DIR / "engine.js").read_text(encoding="utf-8")
    style_css = (ENGINE_DIR / "style.css").read_text(encoding="utf-8")

    # 移除 qrc:// QWebChannel 腳本（僅在 PyQt6 WebEngine 預覽環境有效，瀏覽器不可用）
    index_html = index_html.replace(
        '  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>\n', ""
    )

    # 讀取 effects.js（如果存在）
    effects_js = ""
    effects_path = ENGINE_DIR / "effects.js"
    if effects_path.exists():
        effects_js = effects_path.read_text(encoding="utf-8")

    # 產生 script data
    script_data = project.to_script_json()

    # 建立素材 data URI 映射
    assets_dir = _get_assets_dir(project)
    asset_map = {}  # filename → data URI
    if assets_dir:
        asset_map = _build_asset_map(
            project, assets_dir, optimize_images, max_image_size
        )

    # 替換 script_data 中的素材路徑為 data URI
    _replace_asset_paths(script_data, asset_map)

    # 組裝 HTML
    # 1. CSS 內嵌
    index_html = index_html.replace(
        '<link rel="stylesheet" href="style.css">',
        f"<style>\n{style_css}\n</style>",
    )

    # 2. JS + data 內嵌
    inline_scripts = []
    inline_scripts.append(
        "<script>var SCRIPT_DATA = "
        + json.dumps(script_data, ensure_ascii=False)
        + ";</script>"
    )
    inline_scripts.append(f"<script>\n{engine_js}\n</script>")
    if effects_js:
        inline_scripts.append(f"<script>\n{effects_js}\n</script>")

    # 移除外部 script 引用，改為內嵌
    index_html = index_html.replace('<script src="engine.js"></script>', "")
    index_html = index_html.replace('<script src="effects.js"></script>', "")
    index_html = index_html.replace(
        "</head>", "\n".join(inline_scripts) + "\n</head>"
    )

    # 寫入
    output_path.write_text(index_html, encoding="utf-8")


def _build_asset_map(
    project: Project,
    assets_dir: Path,
    optimize_images: bool,
    max_image_size: int,
) -> dict[str, str]:
    """建立 filename → data URI 的映射。"""
    result = {}
    temp_dir = None

    for category in ("backgrounds", "sprites", "music"):
        for filename in project.assets.get(category, []):
            src = assets_dir / filename
            if not src.exists():
                continue

            if optimize_images and category in ("backgrounds", "sprites"):
                # 圖片壓縮
                if temp_dir is None:
                    temp_dir = tempfile.mkdtemp(prefix="vnstudio_opt_")
                from src.core.image_optimizer import optimize_image

                dst = Path(temp_dir) / filename
                dst.parent.mkdir(parents=True, exist_ok=True)
                optimized = optimize_image(src, dst, max_size=max_image_size)
                data = optimized.read_bytes()
                mime = "image/webp"
            else:
                data = src.read_bytes()
                mime = _guess_mime(src)

            b64 = base64.b64encode(data).decode("ascii")
            result[filename] = f"data:{mime};base64,{b64}"

    return result


def _replace_asset_paths(script_data: dict, asset_map: dict[str, str]) -> None:
    """將 script_data 中的素材檔名替換為 data URI。"""
    for scene in script_data.get("scenes", []):
        # 背景
        bg = scene.get("background")
        if bg and bg in asset_map:
            scene["background"] = asset_map[bg]

        # BGM
        bgm = scene.get("bgm")
        if bgm and bgm in asset_map:
            scene["bgm"] = asset_map[bgm]

        # Phase 3：dialogue 已無 top-level sprite 欄位；stage 槽位僅存放 sprite label，
        # 實際檔名到 data URI 的映射透過下方 characters[].sprites 處理。

    # Characters 中的 sprites
    for char_data in script_data.get("characters", {}).values():
        sprites = char_data.get("sprites", {})
        for label, filename in list(sprites.items()):
            if filename in asset_map:
                sprites[label] = asset_map[filename]


def _guess_mime(path: Path) -> str:
    """猜測檔案的 MIME type。"""
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        return mime
    suffix = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
    }.get(suffix, "application/octet-stream")


def _get_assets_dir(project: Project) -> Path | None:
    """取得專案素材所在目錄。"""
    if project.project_path:
        d = project.project_path.parent / "assets"
        if d.exists():
            return d
    unsaved = Path(tempfile.gettempdir()) / "vnstudio_unsaved" / "assets"
    if unsaved.exists():
        return unsaved
    return None
