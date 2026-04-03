"""簡易 Markdown 轉換：支援粗體、斜體、刪除線。不引入第三方庫。"""

from __future__ import annotations

import re


def md_to_html(text: str) -> str:
    """將文字中的基礎 Markdown 語法轉換為 HTML 標籤。

    支援：
    - **粗體** → <strong>粗體</strong>
    - *斜體* → <em>斜體</em>
    - ~~刪除線~~ → <del>刪除線</del>
    """
    # 先處理粗體（**），再處理斜體（*），避免衝突
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    result = re.sub(r"\*(.+?)\*", r"<em>\1</em>", result)
    result = re.sub(r"~~(.+?)~~", r"<del>\1</del>", result)
    return result


def strip_markdown(text: str) -> str:
    """移除 Markdown 標記，回傳純文字。用於 Pillow 文字渲染。"""
    result = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    result = re.sub(r"\*(.+?)\*", r"\1", result)
    result = re.sub(r"~~(.+?)~~", r"\1", result)
    return result
