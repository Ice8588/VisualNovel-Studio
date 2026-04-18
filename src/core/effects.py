"""文字效果常量：Python / JS 雙端維護，命名需字面對齊（rg 互查）。

新增效果時：
1. 於此加一筆 (key, display_name) 到 TEXT_EFFECTS。
2. 同步修改 `src/engine/engine.js::TEXT_EFFECTS` 與對應的 CSS / keyframe。
3. 補 `tests/test_effects_sync.py`。

鍵（key）是資料模型中 `Dialogue.effects` 儲存的識別字串；
顯示字（display）僅供 UI ComboBox/Menu 呈現，engine 端不直接使用。
"""

from __future__ import annotations

# 順序即 UI 顯示順序
TEXT_EFFECTS: list[tuple[str, str]] = [
    ("bold",          "粗體"),
    ("italic",        "斜體"),
    ("underline",     "底線"),
    ("strikethrough", "刪除線"),
    ("shake",         "顫抖"),
    ("blink",         "閃爍"),
]

# key set，用於驗證
TEXT_EFFECT_KEYS: set[str] = {k for k, _ in TEXT_EFFECTS}


def display_name(key: str) -> str:
    """回傳效果 key 對應的繁中顯示名；未知 key 直接回傳 key 自己。"""
    for k, v in TEXT_EFFECTS:
        if k == key:
            return v
    return key
