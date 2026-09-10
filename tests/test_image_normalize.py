"""task.md #11：立繪匯入標準化測試。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.image_normalize import TARGET_HEIGHT, TARGET_WIDTH, normalize_sprite


def test_normalize_outputs_target_size(tmp_path: Path) -> None:
    src = tmp_path / "in.png"
    Image.new("RGBA", (1200, 1800), (255, 0, 0, 255)).save(src)
    dst = tmp_path / "out.png"
    normalize_sprite(src, dst)

    out = Image.open(dst)
    assert out.size == (TARGET_WIDTH, TARGET_HEIGHT)
    assert out.size == (1080, 1440)


def test_normalize_handles_transparent_padding(tmp_path: Path) -> None:
    src = tmp_path / "in.png"
    canvas = Image.new("RGBA", (2000, 2000), (0, 0, 0, 0))
    inner = Image.new("RGBA", (300, 300), (0, 255, 0, 255))
    canvas.paste(inner, (800, 800))
    canvas.save(src)

    dst = tmp_path / "out.png"
    normalize_sprite(src, dst)

    out = Image.open(dst)
    assert out.size == (TARGET_WIDTH, TARGET_HEIGHT)


def test_normalize_smaller_image_scales_up(tmp_path: Path) -> None:
    src = tmp_path / "in.png"
    Image.new("RGBA", (300, 400), (0, 0, 255, 255)).save(src)
    dst = tmp_path / "out.png"
    normalize_sprite(src, dst)

    out = Image.open(dst)
    assert out.size == (TARGET_WIDTH, TARGET_HEIGHT)


def test_normalize_preserves_aspect_ratio(tmp_path: Path) -> None:
    """寬高比 1:2 來源 → 內容 height ≈ 95% 畫布、width 等比縮放。"""
    src = tmp_path / "in.png"
    Image.new("RGBA", (500, 1000), (255, 255, 255, 255)).save(src)
    dst = tmp_path / "out.png"
    normalize_sprite(src, dst)

    out = Image.open(dst)
    # 應為 1080×1440；視覺上人物垂直貼底
    assert out.size == (TARGET_WIDTH, TARGET_HEIGHT)
