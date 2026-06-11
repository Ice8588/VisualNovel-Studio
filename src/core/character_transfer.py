"""跨作品角色搬運：從其他作品（.vnsproj）讀出的角色複製進目標專案。

純邏輯模組（無 Qt）。「角色卡」概念對使用者不可見；
.vncard 分享格式（character_library.py）為獨立休眠後端，與此模組無耦合。
"""

from __future__ import annotations

import copy
from pathlib import Path

from src.core.models import Character


def copy_file_dedup(src: Path, target_dir: Path) -> str:
    """把 src 複製進 target_dir：同名同內容重用既有檔；同名異內容加 _1, _2… 後綴。

    Returns:
        最終落在 target_dir 內的檔名。
    """
    src = Path(src)
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    dest = target_dir / src.name
    counter = 1
    while dest.exists() and dest.read_bytes() != data:
        dest = target_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    if not dest.exists():
        dest.write_bytes(data)
    return dest.name


def import_character(
    char: Character, source_assets: Path, target_assets: Path
) -> tuple[Character, list[str]]:
    """深拷貝角色並把引用的立繪複製到 target_assets。

    Returns:
        (filename 已改寫的新 Character, 來源缺檔清單)
        缺檔差分保留原 filename 不複製，由呼叫端決定如何提示。
    """
    source_assets = Path(source_assets)
    new_char = copy.deepcopy(char)
    missing: list[str] = []
    for costume in new_char.costumes:
        for sv in costume.expressions:
            if not sv.filename:
                continue
            src_file = source_assets / sv.filename
            if not src_file.is_file():
                missing.append(sv.filename)
                continue
            sv.filename = copy_file_dedup(src_file, target_assets)
    return new_char, missing
