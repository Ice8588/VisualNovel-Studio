"""素材管理：驗證、複製素材到專案目錄。"""

from __future__ import annotations

import shutil
from pathlib import Path

VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
VALID_AUDIO_EXTENSIONS = {".mp3", ".wav"}

CATEGORY_EXTENSIONS = {
    "backgrounds": VALID_IMAGE_EXTENSIONS,
    "sprites": VALID_IMAGE_EXTENSIONS,
    "music": VALID_AUDIO_EXTENSIONS,
}


def import_asset(source: Path, category: str, project_dir: Path) -> str:
    """複製素材到 project_dir/assets/，驗證副檔名，回傳目標檔名。

    Args:
        source: 來源檔案路徑
        category: 素材分類（"backgrounds", "sprites", "music"）
        project_dir: 專案目錄

    Returns:
        複製後的檔案名稱（不含路徑）

    Raises:
        ValueError: 不支援的分類或副檔名
        FileNotFoundError: 來源檔案不存在
    """
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"找不到檔案：{source}")

    if category not in CATEGORY_EXTENSIONS:
        raise ValueError(f"不支援的素材分類：{category}")

    valid_exts = CATEGORY_EXTENSIONS[category]
    if source.suffix.lower() not in valid_exts:
        raise ValueError(
            f"不支援的檔案格式：{source.suffix}（{category} 僅支援 {', '.join(valid_exts)}）"
        )

    assets_dir = project_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # task.md #11：sprites 走標準化（PNG 透明畫布 1080×1440），其餘類別維持 copy。
    if category == "sprites":
        from src.core.image_normalize import normalize_sprite

        # 標準化輸出統一為 .png（避免 jpg 透明問題）
        dest = assets_dir / (source.stem + ".png")
        # 檔名重複處理（與既有檔不同檔才重命名）
        if dest.exists() and not dest.samefile(source):
            stem = source.stem
            counter = 1
            while dest.exists():
                dest = assets_dir / f"{stem}_{counter}.png"
                counter += 1
        normalize_sprite(source, dest)
        return dest.name

    dest = assets_dir / source.name
    # 若檔名重複，加上數字後綴
    if dest.exists() and not dest.samefile(source):
        stem = source.stem
        suffix = source.suffix
        counter = 1
        while dest.exists():
            dest = assets_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.copy2(source, dest)
    return dest.name


def get_asset_filename(path: Path) -> str:
    """回傳檔案名稱，供 script.json 引用。"""
    return Path(path).name
