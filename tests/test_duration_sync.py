"""驗證 Python / JS 兩端 Auto duration 公式一致。

engine.js 端：`Math.max(MIN_MS, Math.min(BASE_MS + text.length * PER_CHAR_MS, CAP_MS))`（毫秒）。
Python 端：`exporter_video.calc_auto_duration`（秒）。
此測試用 regex 抽 JS 端四個常數，逐長度比對兩端結果。
"""

from __future__ import annotations

import re
from pathlib import Path

from src.core.exporter_video import calc_auto_duration

ENGINE_JS = Path(__file__).parent.parent / "src" / "engine" / "engine.js"


def _extract_js_duration_constants() -> tuple[int, int, int, int]:
    """讀 engine.js，抽出 getAutoDuration 的 (min_ms, base_ms, per_char_ms, cap_ms)。"""
    text = ENGINE_JS.read_text(encoding="utf-8")
    m = re.search(
        r"function\s+getAutoDuration\s*\(text\)\s*\{.*?"
        r"Math\.max\(\s*(\d+)\s*,\s*Math\.min\(\s*(\d+)\s*\+\s*text\.length\s*\*\s*(\d+)\s*,\s*(\d+)\s*\)\s*\)",
        text,
        re.DOTALL,
    )
    assert m, (
        "engine.js 中找不到預期形狀的 getAutoDuration "
        "（Math.max(min, Math.min(base + text.length * per_char, cap))）；"
        "若公式改了，請同步更新 exporter_video.calc_auto_duration 與本測試"
    )
    return tuple(int(g) for g in m.groups())


def test_python_and_js_duration_formula_aligned():
    min_ms, base_ms, per_char_ms, cap_ms = _extract_js_duration_constants()
    for length in [0, 1, 3, 10, 33, 34, 46, 47, 48, 60, 100, 500]:
        text = "字" * length
        js_seconds = max(min_ms, min(base_ms + length * per_char_ms, cap_ms)) / 1000.0
        py_seconds = calc_auto_duration(text)
        assert abs(js_seconds - py_seconds) < 1e-9, (
            f"長度 {length}：JS {js_seconds}s != Python {py_seconds}s"
        )
