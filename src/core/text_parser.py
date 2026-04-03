"""文字解析器：讀取 .txt/.docx，依「」規則分類為台詞或旁白。"""

from __future__ import annotations

from pathlib import Path

from src.core.models import Dialogue


def parse_file(path: Path) -> list[Dialogue]:
    """根據副檔名分派解析，回傳分類後的 Dialogue 列表。"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".txt":
        lines = _parse_txt(path)
    elif suffix == ".docx":
        lines = _parse_docx(path)
    else:
        raise ValueError(f"不支援的檔案格式：{suffix}")
    return _classify_lines(lines)


def _parse_txt(path: Path) -> list[str]:
    """讀取 .txt 檔案，回傳每行文字。"""
    text = path.read_text(encoding="utf-8")
    return text.splitlines()


def _parse_docx(path: Path) -> list[str]:
    """讀取 .docx 檔案，每個 paragraph 視為一行。"""
    import docx

    doc = docx.Document(str(path))
    return [para.text for para in doc.paragraphs]


def _classify_lines(lines: list[str]) -> list[Dialogue]:
    """逐行套用「」規則分類。空行跳過。"""
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _is_dialogue_line(stripped):
            result.append(Dialogue(type="dialogue", text=stripped[1:-1]))
        else:
            result.append(Dialogue(type="narration", text=stripped))
    return result


def _is_dialogue_line(line: str) -> bool:
    """判斷整行是否僅由「」包圍（行首為「、行尾為」、長度 > 2）。"""
    return len(line) >= 2 and line[0] == "「" and line[-1] == "」"
