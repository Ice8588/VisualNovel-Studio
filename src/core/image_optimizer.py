"""圖片優化：縮放至 1080p + 轉換為 WebP 格式。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def optimize_image(
    src: Path, dst: Path, max_size: int = 1920, quality: int = 85
) -> Path:
    """縮放圖片至 max_size px（長邊），轉 WebP 格式。

    Args:
        src: 來源圖片路徑。
        dst: 目標路徑（副檔名會被改為 .webp）。
        max_size: 長邊最大像素數。
        quality: WebP 壓縮品質（1-100）。

    Returns:
        實際寫入的檔案路徑（.webp）。
    """
    img = Image.open(src)

    # RGBA → RGB（WebP 支援 RGBA，但轉 RGB 可縮小檔案）
    if img.mode == "RGBA":
        # 保留透明度，WebP 原生支援
        pass
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 縮放
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    # 寫入 WebP
    dst = dst.with_suffix(".webp")
    img.save(dst, "WEBP", quality=quality)
    return dst


def estimate_base64_size(file_paths: list[Path]) -> int:
    """估算所有檔案 Base64 編碼後的總大小（bytes）。

    Base64 編碼會使資料膨脹約 1.37 倍。
    """
    total = 0
    for p in file_paths:
        if p.exists():
            total += p.stat().st_size
    return int(total * 1.37)
