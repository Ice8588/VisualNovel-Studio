"""驗證 Python / JS 兩端 TEXT_EFFECTS 鍵集合一致。

engine.js 端用 JS 陣列 `var TEXT_EFFECTS = [{key: "...", display: "..."}, ...]`。
此測試用 regex 抽 key 清單，與 Python 端比對。
"""

from __future__ import annotations

import re
from pathlib import Path

from src.core.effects import TEXT_EFFECT_KEYS

ENGINE_JS = Path(__file__).parent.parent / "src" / "engine" / "engine.js"


def _extract_js_effect_keys() -> set[str]:
    """讀 engine.js，抽出 TEXT_EFFECTS 內所有 key 字串。"""
    text = ENGINE_JS.read_text(encoding="utf-8")
    m = re.search(r"var\s+TEXT_EFFECTS\s*=\s*\[(.*?)\];", text, re.DOTALL)
    assert m, "engine.js 中找不到 `var TEXT_EFFECTS = [...]` 宣告"
    body = m.group(1)
    return set(re.findall(r'key\s*:\s*"([^"]+)"', body))


def test_python_and_js_effect_keys_aligned():
    js_keys = _extract_js_effect_keys()
    assert js_keys == TEXT_EFFECT_KEYS, (
        f"Python/JS 文字效果鍵不一致。\n"
        f"Python: {sorted(TEXT_EFFECT_KEYS)}\n"
        f"JS    : {sorted(js_keys)}"
    )
