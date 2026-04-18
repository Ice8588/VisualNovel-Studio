"""測試 text_parser.py：解析規則與邊緣案例。"""

from pathlib import Path

import pytest

from src.core.text_parser import _classify_lines, _is_dialogue_line, parse_file

SAMPLES_DIR = Path(__file__).parent / "samples"


class TestIsDialogueLine:
    def test_pure_dialogue(self):
        assert _is_dialogue_line("「你好嗎？」") is True

    def test_narration(self):
        assert _is_dialogue_line("他走了。") is False

    def test_mixed_line_with_quotes(self):
        """中間有「」但整行不是純台詞。"""
        assert _is_dialogue_line("這行中間有「引號」但不是純台詞。") is False

    def test_says_colon_line(self):
        """「說：」行是旁白。"""
        assert _is_dialogue_line("他轉過身，說：") is False

    def test_empty_quotes(self):
        """「」空引號仍算台詞（長度剛好 2）。"""
        assert _is_dialogue_line("「」") is True

    def test_empty_string(self):
        assert _is_dialogue_line("") is False


class TestClassifyLines:
    def test_basic_classification(self):
        lines = [
            "他站在窗邊。",
            "「你好嗎？」",
            "",
            "她走了。",
        ]
        result = _classify_lines(lines)
        assert len(result) == 3  # 空行跳過
        assert result[0].type == "narration"
        assert result[0].text == "他站在窗邊。"
        assert result[1].type == "dialogue"
        assert result[1].text == "「你好嗎？」"  # 保留「」
        assert result[2].type == "narration"

    def test_consecutive_blank_lines(self):
        """連續空行等同一個空行，不產生任何條目。"""
        lines = ["旁白", "", "", "", "「台詞」"]
        result = _classify_lines(lines)
        assert len(result) == 2

    def test_says_colon_pattern(self):
        """「說：」接台詞的情形：每行獨立判斷。"""
        lines = [
            "他轉過身，說：",
            "「你知道嗎？」",
        ]
        result = _classify_lines(lines)
        assert result[0].type == "narration"
        assert result[0].text == "他轉過身，說："
        assert result[1].type == "dialogue"
        assert result[1].text == "「你知道嗎？」"  # 保留「」

    def test_dialogue_text_keeps_brackets(self):
        """台詞的 text 保留「」符號。"""
        lines = ["「我已經決定了。」"]
        result = _classify_lines(lines)
        assert result[0].text == "「我已經決定了。」"

    def test_narration_default_fields(self):
        """旁白的 character 和 sprite 預設為 None。"""
        lines = ["這是旁白。"]
        result = _classify_lines(lines)
        assert result[0].character is None
        assert result[0].sprite is None

    def test_whitespace_only_lines_skipped(self):
        lines = ["  ", "\t", "旁白"]
        result = _classify_lines(lines)
        assert len(result) == 1


class TestParseFile:
    def test_parse_basic_txt(self):
        result = parse_file(SAMPLES_DIR / "sample_basic.txt")
        # sample_basic.txt 內容：
        # 旁白 → 台詞 → 旁白 → 台詞 → (空行) → 旁白 → 台詞
        assert len(result) == 6
        assert result[0].type == "narration"
        assert result[1].type == "dialogue"
        assert result[1].text.replace("「", "").replace("」", "") == "你真的要走嗎？"
        assert result[2].type == "narration"
        assert result[3].type == "dialogue"
        assert result[3].text.replace("「", "").replace("」", "") == "我已經決定了。"
        assert result[4].type == "narration"
        assert result[5].type == "dialogue"

    def test_parse_edge_txt(self):
        result = parse_file(SAMPLES_DIR / "sample_edge.txt")
        # 他轉過身，說：        → narration
        # 「你知道嗎？」          → dialogue
        # (空行x2)               → 跳過
        # 「這是連續空行後的台詞。」→ dialogue
        # 這行中間有「引號」...    → narration
        # 「」                    → dialogue (空引號)
        # (空行)                  → 跳過
        # 最後一段旁白。          → narration
        assert len(result) == 6
        assert result[0].type == "narration"
        assert result[0].text == "他轉過身，說："
        assert result[1].type == "dialogue"
        assert result[1].text == "「你知道嗎？」"
        assert result[2].type == "dialogue"
        assert result[2].text == "「這是連續空行後的台詞。」"
        assert result[3].type == "narration"
        assert result[4].type == "dialogue"
        assert result[4].text == "「」"  # 空引號保留
        assert result[5].type == "narration"

    def test_unsupported_format(self):
        with pytest.raises(ValueError, match="不支援的檔案格式"):
            parse_file(Path("test.pdf"))
