"""共用常數與座標換算。POC 用固定列高，避免動態高度的同步複雜度。

色票管理已集中到 `src/ui/palette.py`。本模組透過 module-level `__getattr__`
動態 forward `BG_DARK` / `BG_PANEL` / `TEXT_PRIMARY` 等常量到 `palette.current()`，
維持既有 `from src.ui import _timeline_shared as shared; shared.BG_DARK` 用法。
"""

from PyQt6.QtGui import QColor

from src.ui import palette as _palette

ROW_HEIGHT = 52
GUTTER_WIDTH = 36
LANE_WIDTH = 110
EDGE_HIT = 7
DRAG_THRESHOLD = 5

# 名稱 → palette 屬性的對照（給 module-level __getattr__）
_FORWARD_MAP = {
    "BG_DARK":           "bg",
    "BG_PANEL":          "surface",
    "BG_ROW_ALT":        "row_alt",
    "GRID_LINE":         "grid_line",
    "TEXT_PRIMARY":      "text_primary",
    "TEXT_MUTED":        "text_secondary",
    "CARD_DIALOGUE_BG":  "card_dialogue_bg",
    "CARD_NARRATION_BG": "card_narration_bg",
    "CURSOR_LINE":       "cursor",
    "DROP_INDICATOR":    "drop_indicator",
}


def __getattr__(name: str):
    """PEP 562 module-level __getattr__：動態回傳當前主題的 palette 屬性。"""
    if name in _FORWARD_MAP:
        return getattr(_palette.current(), _FORWARD_MAP[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def is_light() -> bool:
    return _palette.is_light()


def current_theme() -> str:
    return _palette.current_theme()


def refresh_palette(theme_name: str | None = None) -> None:
    """[backward-compat] forward 到 palette.set_theme。"""
    if theme_name is None:
        try:
            from qfluentwidgets import isDarkTheme
            theme_name = "dark" if isDarkTheme() else "light"
        except ImportError:
            theme_name = "dark"
    _palette.set_theme(theme_name)

CHARACTER_COLORS = {
    "小明": "#4682B4",
    "小華": "#C85A54",
    "阿姨": "#8E6FB8",
    "店員": "#4A8F6E",
}

EFFECT_COLORS = {
    "rain": "#4A7BB7",
    "snow": "#B0BEC5",
    "shake-screen": "#D9534F",
    "screen_shake": "#D9534F",
    "crt": "#8E44AD",
    "pixel-dark": "#616161",
    "pixel_dark": "#616161",
}


def idx_to_y(idx: int) -> int:
    return idx * ROW_HEIGHT


def y_to_idx(y: int, max_idx: int) -> int:
    idx = y // ROW_HEIGHT
    return max(0, min(idx, max_idx))


def idx_range_to_rect_y(start: int, end: int) -> tuple[int, int]:
    """segment [start, end] inclusive → 像素 y 的 (top, bottom)"""
    return start * ROW_HEIGHT, (end + 1) * ROW_HEIGHT


def character_color(name: str | None, fallback: str | None = None) -> QColor:
    """回傳角色色卡；`fallback` 為使用者在 Character.name_color 設定的顏色，
    會覆寫 POC 內建的 CHARACTER_COLORS。"""
    if not name:
        return QColor("#666666")
    if fallback:
        return QColor(fallback)
    return QColor(CHARACTER_COLORS.get(name, "#5F6368"))
