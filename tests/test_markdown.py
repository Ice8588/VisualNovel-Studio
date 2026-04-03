"""測試 Markdown 轉換功能。"""

import unittest

from src.core.markdown_helper import md_to_html, strip_markdown


class TestMdToHtml(unittest.TestCase):
    def test_bold(self):
        self.assertEqual(md_to_html("**粗體**"), "<strong>粗體</strong>")

    def test_italic(self):
        self.assertEqual(md_to_html("*斜體*"), "<em>斜體</em>")

    def test_strikethrough(self):
        self.assertEqual(md_to_html("~~刪除~~"), "<del>刪除</del>")

    def test_mixed(self):
        result = md_to_html("這是**粗體**和*斜體*和~~刪除~~的文字")
        self.assertEqual(
            result,
            "這是<strong>粗體</strong>和<em>斜體</em>和<del>刪除</del>的文字",
        )

    def test_no_markdown(self):
        self.assertEqual(md_to_html("普通文字"), "普通文字")

    def test_empty(self):
        self.assertEqual(md_to_html(""), "")

    def test_bold_inside_sentence(self):
        self.assertEqual(md_to_html("他說了一句**很重要**的話"), "他說了一句<strong>很重要</strong>的話")

    def test_multiple_bold(self):
        result = md_to_html("**A**和**B**")
        self.assertEqual(result, "<strong>A</strong>和<strong>B</strong>")


class TestStripMarkdown(unittest.TestCase):
    def test_strip_bold(self):
        self.assertEqual(strip_markdown("**粗體**"), "粗體")

    def test_strip_italic(self):
        self.assertEqual(strip_markdown("*斜體*"), "斜體")

    def test_strip_strikethrough(self):
        self.assertEqual(strip_markdown("~~刪除~~"), "刪除")

    def test_strip_mixed(self):
        self.assertEqual(
            strip_markdown("這是**粗體**和*斜體*"),
            "這是粗體和斜體",
        )

    def test_strip_plain(self):
        self.assertEqual(strip_markdown("普通文字"), "普通文字")


if __name__ == "__main__":
    unittest.main()
