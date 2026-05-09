"""共用常數與座標換算。POC 用固定列高，避免動態高度的同步複雜度。

色票主題感知：常量在 module 載入時為深色預設；呼叫 `refresh_palette()`
根據 qfluentwidgets 當前主題重新綁定。所有 paint 端使用 `shared.X` 屬性
存取方式才能拿到最新值。
"""

from PyQt6.QtGui import QColor

ROW_HEIGHT = 52
GUTTER_WIDTH = 36
LANE_WIDTH = 110
EDGE_HIT = 7
DRAG_THRESHOLD = 5

# 主題不變色（兩主題共用）
CURSOR_LINE = QColor("#FFB300")
DROP_INDICATOR = QColor("#00B7C3")

# 主題感知色 — 每個主題各自一份 palette，跟 QSS overrides 對齊
_PALETTE_DARK = {
    "BG_DARK":           QColor("#1E1E1E"),
    "BG_PANEL":          QColor("#252526"),
    "BG_ROW_ALT":        QColor(255, 255, 255, 6),
    "GRID_LINE":         QColor(255, 255, 255, 18),
    "TEXT_PRIMARY":      QColor("#E8E8E8"),
    "TEXT_MUTED":        QColor("#9AA0A6"),
    "CARD_DIALOGUE_BG":  QColor("#2E3440"),
    "CARD_NARRATION_BG": QColor("#2D2D30"),
}
_PALETTE_LIGHT = {
    "BG_DARK":           QColor("#EEEEEE"),
    "BG_PANEL":          QColor("#F5F5F5"),
    "BG_ROW_ALT":        QColor(0, 0, 0, 8),
    "GRID_LINE":         QColor(0, 0, 0, 32),
    "TEXT_PRIMARY":      QColor("#1E1E1E"),
    "TEXT_MUTED":        QColor("#6E6E73"),
    "CARD_DIALOGUE_BG":  QColor("#E5EFFA"),
    "CARD_NARRATION_BG": QColor("#F5F5F5"),
}
_PALETTE_PARCHMENT = {
    "BG_DARK":           QColor("#F5ECD7"),
    "BG_PANEL":          QColor("#EADFBF"),
    "BG_ROW_ALT":        QColor(120, 90, 40, 14),
    "GRID_LINE":         QColor(120, 90, 40, 60),
    "TEXT_PRIMARY":      QColor("#2B2416"),
    "TEXT_MUTED":        QColor("#6B5B3F"),
    "CARD_DIALOGUE_BG":  QColor("#FCF6E3"),
    "CARD_NARRATION_BG": QColor("#EADFBF"),
}
_PALETTE_IVORY = {
    "BG_DARK":           QColor("#FDFDFC"),
    "BG_PANEL":          QColor("#F4F3EF"),
    "BG_ROW_ALT":        QColor(0, 0, 0, 8),
    "GRID_LINE":         QColor(0, 0, 0, 28),
    "TEXT_PRIMARY":      QColor("#1C1B19"),
    "TEXT_MUTED":        QColor("#6F6E69"),
    "CARD_DIALOGUE_BG":  QColor("#EAF1FA"),
    "CARD_NARRATION_BG": QColor("#F4F3EF"),
}
_PALETTE_MIDNIGHT = {
    "BG_DARK":           QColor("#141414"),
    "BG_PANEL":          QColor("#1A1A1A"),
    "BG_ROW_ALT":        QColor(255, 255, 255, 5),
    "GRID_LINE":         QColor(255, 255, 255, 16),
    "TEXT_PRIMARY":      QColor("#E0E0E0"),
    "TEXT_MUTED":        QColor("#888888"),
    "CARD_DIALOGUE_BG":  QColor("#1F2533"),
    "CARD_NARRATION_BG": QColor("#1A1A1A"),
}
_PALETTE_FIGMA_DARK = {
    "BG_DARK":           QColor("#1E1E1E"),
    "BG_PANEL":          QColor("#2C2C2C"),
    "BG_ROW_ALT":        QColor(255, 255, 255, 6),
    "GRID_LINE":         QColor(255, 255, 255, 20),
    "TEXT_PRIMARY":      QColor("#E5E5E5"),
    "TEXT_MUTED":        QColor("#A0A0A0"),
    "CARD_DIALOGUE_BG":  QColor("#2E3440"),
    "CARD_NARRATION_BG": QColor("#2C2C2C"),
}

_PALETTES = {
    "dark":       _PALETTE_DARK,
    "light":      _PALETTE_LIGHT,
    "parchment":  _PALETTE_PARCHMENT,
    "midnight":   _PALETTE_MIDNIGHT,
    "figma-dark": _PALETTE_FIGMA_DARK,
    "ivory":      _PALETTE_IVORY,
}

BG_DARK           = _PALETTE_DARK["BG_DARK"]
BG_PANEL          = _PALETTE_DARK["BG_PANEL"]
BG_ROW_ALT        = _PALETTE_DARK["BG_ROW_ALT"]
GRID_LINE         = _PALETTE_DARK["GRID_LINE"]
TEXT_PRIMARY      = _PALETTE_DARK["TEXT_PRIMARY"]
TEXT_MUTED        = _PALETTE_DARK["TEXT_MUTED"]
CARD_DIALOGUE_BG  = _PALETTE_DARK["CARD_DIALOGUE_BG"]
CARD_NARRATION_BG = _PALETTE_DARK["CARD_NARRATION_BG"]


_current_theme: str = "dark"


def is_light() -> bool:
    """查當前主題是否為淺色（依 _current_theme 字串判斷）。"""
    return _current_theme in ("light", "parchment", "ivory")


def current_theme() -> str:
    return _current_theme


def refresh_palette(theme_name: str | None = None) -> None:
    """根據主題名稱重新綁定色票常量。
    theme_name 為 None → 用 qfluentwidgets isDarkTheme 推斷 light / dark fallback。
    """
    global BG_DARK, BG_PANEL, BG_ROW_ALT, GRID_LINE
    global TEXT_PRIMARY, TEXT_MUTED, CARD_DIALOGUE_BG, CARD_NARRATION_BG
    global _current_theme

    if theme_name is None:
        try:
            from qfluentwidgets import isDarkTheme
            theme_name = "dark" if isDarkTheme() else "light"
        except ImportError:
            theme_name = "dark"

    _current_theme = theme_name
    pal = _PALETTES.get(theme_name, _PALETTE_DARK)
    BG_DARK           = pal["BG_DARK"]
    BG_PANEL          = pal["BG_PANEL"]
    BG_ROW_ALT        = pal["BG_ROW_ALT"]
    GRID_LINE         = pal["GRID_LINE"]
    TEXT_PRIMARY      = pal["TEXT_PRIMARY"]
    TEXT_MUTED        = pal["TEXT_MUTED"]
    CARD_DIALOGUE_BG  = pal["CARD_DIALOGUE_BG"]
    CARD_NARRATION_BG = pal["CARD_NARRATION_BG"]

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
