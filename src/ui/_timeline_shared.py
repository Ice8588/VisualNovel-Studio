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

# 主題感知色 — 兩個 palette + 預設綁深色
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
    "BG_DARK":           QColor("#F2F2F4"),
    "BG_PANEL":          QColor("#FAFAFA"),
    "BG_ROW_ALT":        QColor(0, 0, 0, 8),
    "GRID_LINE":         QColor(0, 0, 0, 32),
    "TEXT_PRIMARY":      QColor("#1E1E1E"),
    "TEXT_MUTED":        QColor("#6E6E73"),
    "CARD_DIALOGUE_BG":  QColor("#E5EFFA"),
    "CARD_NARRATION_BG": QColor("#F2F2F4"),
}

BG_DARK           = _PALETTE_DARK["BG_DARK"]
BG_PANEL          = _PALETTE_DARK["BG_PANEL"]
BG_ROW_ALT        = _PALETTE_DARK["BG_ROW_ALT"]
GRID_LINE         = _PALETTE_DARK["GRID_LINE"]
TEXT_PRIMARY      = _PALETTE_DARK["TEXT_PRIMARY"]
TEXT_MUTED        = _PALETTE_DARK["TEXT_MUTED"]
CARD_DIALOGUE_BG  = _PALETTE_DARK["CARD_DIALOGUE_BG"]
CARD_NARRATION_BG = _PALETTE_DARK["CARD_NARRATION_BG"]


def is_light() -> bool:
    """查當前 qfluentwidgets 主題是否為淺色。"""
    try:
        from qfluentwidgets import isDarkTheme
        return not isDarkTheme()
    except ImportError:
        return False


def refresh_palette() -> None:
    """根據當前主題重新綁定色票常量；所有 paint 端透過 shared.X 存取會立即拿到新值。"""
    global BG_DARK, BG_PANEL, BG_ROW_ALT, GRID_LINE
    global TEXT_PRIMARY, TEXT_MUTED, CARD_DIALOGUE_BG, CARD_NARRATION_BG
    pal = _PALETTE_LIGHT if is_light() else _PALETTE_DARK
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
