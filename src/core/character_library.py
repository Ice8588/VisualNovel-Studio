"""角色卡：將 Character 連同立繪打包為 .vncard（zip）檔，跨專案共享。

儲存位置：`~/.vnstudio/character_cards/`（跨平台）。
每張卡為 zip，結構：
    character.json    # Character.to_dict() 結果
    assets/           # 所有引用的立繪檔案（檔名同 SpriteVariant.filename）
"""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path

from src.core.models import Character

CARD_EXTENSION = ".vncard"


def get_library_dir() -> Path:
    """回傳使用者角色卡目錄（必要時自動建立）。"""
    d = Path.home() / ".vnstudio" / "character_cards"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename(name: str) -> str:
    """把角色名過濾成檔名安全字串（中文允許，移除 / \\ : * ? " < > |）。"""
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return cleaned or "未命名"


def save_card(character: Character, assets_dir: Path, target_dir: Path | None = None) -> Path:
    """把角色連同立繪打包為 .vncard；若目標檔已存在則加數字後綴。

    Args:
        character: 要匯出的角色。
        assets_dir: 專案的 assets 目錄（例如 `project_dir/assets`）。
        target_dir: 儲存位置，預設為 `get_library_dir()`。

    Returns:
        實際寫入的檔案路徑。
    """
    target_dir = target_dir or get_library_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = _safe_filename(character.name)
    card_path = target_dir / f"{base_name}{CARD_EXTENSION}"
    # 衝突時加 _1, _2...
    counter = 1
    while card_path.exists():
        card_path = target_dir / f"{base_name}_{counter}{CARD_EXTENSION}"
        counter += 1

    # 收集所有立繪檔名
    sprite_files: set[str] = set()
    for costume in character.costumes:
        for sv in costume.expressions:
            if sv.filename:
                sprite_files.add(sv.filename)

    with zipfile.ZipFile(card_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 寫入 character.json
        zf.writestr(
            "character.json",
            json.dumps(character.to_dict(), ensure_ascii=False, indent=2),
        )
        # 寫入立繪
        for filename in sorted(sprite_files):
            src = assets_dir / filename
            if src.exists() and src.is_file():
                zf.write(src, arcname=f"assets/{filename}")
    return card_path


def list_cards(source_dir: Path | None = None) -> list[Path]:
    """列出指定目錄下所有 .vncard，預設為使用者角色卡庫。"""
    source_dir = source_dir or get_library_dir()
    if not source_dir.exists():
        return []
    return sorted(source_dir.glob(f"*{CARD_EXTENSION}"))


def load_card(card_path: Path, target_assets_dir: Path) -> tuple[Character, list[str]]:
    """讀取 .vncard 並把立繪複製到目標 assets 目錄；立繪檔名衝突時加數字後綴並改寫 SpriteVariant.filename。

    Args:
        card_path: 角色卡檔案路徑。
        target_assets_dir: 目的專案的 assets 目錄（會自動建立）。

    Returns:
        (載入後的 Character, 實際寫入 assets 的檔名清單)

    Raises:
        FileNotFoundError: card_path 不存在。
        ValueError: card 內容格式不合法。
    """
    card_path = Path(card_path)
    if not card_path.exists():
        raise FileNotFoundError(f"角色卡不存在：{card_path}")

    target_assets_dir = Path(target_assets_dir)
    target_assets_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(card_path, "r") as zf:
        try:
            raw = zf.read("character.json").decode("utf-8")
        except KeyError as e:
            raise ValueError("角色卡缺少 character.json") from e
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"character.json 解析失敗：{e}") from e

        character = Character.from_dict(data)

        # 抽出 assets/* 到目的目錄；衝突時 rename
        rename_map: dict[str, str] = {}
        written: list[str] = []
        for info in zf.infolist():
            if not info.filename.startswith("assets/") or info.is_dir():
                continue
            orig_name = Path(info.filename).name
            if not orig_name:
                continue
            dest = target_assets_dir / orig_name
            final_name = orig_name
            if dest.exists():
                stem = dest.stem
                suffix = dest.suffix
                counter = 1
                while dest.exists():
                    final_name = f"{stem}_{counter}{suffix}"
                    dest = target_assets_dir / final_name
                    counter += 1
            with zf.open(info) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
            rename_map[orig_name] = final_name
            written.append(final_name)

        # 同步更新 Character 中的 filename
        for costume in character.costumes:
            for sv in costume.expressions:
                if sv.filename and sv.filename in rename_map:
                    sv.filename = rename_map[sv.filename]

    return character, written


def delete_card(card_path: Path) -> None:
    """刪除指定角色卡檔；不存在時忽略。"""
    card_path = Path(card_path)
    if card_path.exists():
        card_path.unlink()
