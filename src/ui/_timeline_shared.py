"""共用常數與座標換算。POC 用固定列高，避免動態高度的同步複雜度。"""

from PyQt6.QtGui import QColor

ROW_HEIGHT = 52
GUTTER_WIDTH = 36
LANE_WIDTH = 110
EDGE_HIT = 7
DRAG_THRESHOLD = 5

# 主視覺色
BG_DARK = QColor("#1E1E1E")
BG_PANEL = QColor("#252526")
BG_ROW_ALT = QColor(255, 255, 255, 6)
GRID_LINE = QColor(255, 255, 255, 18)
CURSOR_LINE = QColor("#FFB300")
DROP_INDICATOR = QColor("#00B7C3")

TEXT_PRIMARY = QColor("#E8E8E8")
TEXT_MUTED = QColor("#9AA0A6")

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
