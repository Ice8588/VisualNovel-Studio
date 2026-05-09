"""Design 資源載入：dev / PyInstaller 兩種模式皆可。"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer


def resource_root() -> Path:
    """支援 dev 與 PyInstaller 兩種模式的資源根目錄。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def design_icon(name: str) -> QIcon:
    """從 assets/design/icons/ 載入 SVG icon；缺檔回空 QIcon（不致命）。

    SVG 內 `stroke="currentColor"` 會被 Qt 渲染為黑色；要在暗色背景顯示
    可見的 icon，請改用 design_icon_tinted。
    """
    path = resource_root() / "assets" / "design" / "icons" / f"{name}.svg"
    return QIcon(str(path)) if path.is_file() else QIcon()


def design_icon_tinted(name: str, color: str, size: int = 24) -> QIcon:
    """載入 SVG 並把 `currentColor` 換成指定 hex 色（給固定背景的 popup 用）。"""
    path = resource_root() / "assets" / "design" / "icons" / f"{name}.svg"
    if not path.is_file():
        return QIcon()
    svg_text = path.read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(svg_text.encode("utf-8"))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def design_asset(*relative: str) -> Path:
    """取得 assets/design/ 下的資源完整路徑（不檢查存在）。"""
    return resource_root() / "assets" / "design" / Path(*relative)


def themed_icon(name: str, size: int = 24) -> QIcon:
    """依當前主題（深 / 淺）回傳染色 SVG icon。

    深色主題 → 接近白；淺色主題 → 接近黑。
    主題切換後呼叫端需重新呼叫此函式以取得正確顏色。
    """
    try:
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
    except ImportError:
        is_dark = True
    color = "#E8E8E8" if is_dark else "#1E1E1E"
    return design_icon_tinted(name, color, size)
