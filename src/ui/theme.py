"""主題系統：使用 qfluentwidgets 深色/淺色主題，補充原生元件樣式。"""

from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

_SETTINGS_ORG = "VisualNovelStudio"
_SETTINGS_APP = "VNStudio"

# 原生 Qt 元件（非 qfluentwidgets）的補充樣式
_DARK_OVERRIDES = """
QMainWindow {{
    background-color: #1e1e1e;
}}
QMenuBar {{
    background-color: #2b2b2b;
    color: #ddd;
    border-bottom: 1px solid #3c3c3c;
    font-size: {font_size}px;
}}
QMenuBar::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QMenu {{
    background-color: #2b2b2b;
    color: #ddd;
    border: 1px solid #3c3c3c;
}}
QMenu::item:selected {{
    background-color: #4682B4;
}}
QToolBar {{
    background-color: #2b2b2b;
    border-bottom: 1px solid #3c3c3c;
    spacing: 6px;
    padding: 4px;
}}
QPushButton {{
    background-color: #3c3c3c;
    color: #ddd;
    border: 1px solid #555;
    padding: 5px 12px;
    border-radius: 3px;
    font-size: {font_size}px;
}}
QPushButton:hover {{
    background-color: #4a4a4a;
    border-color: #4682B4;
}}
QPushButton:pressed {{
    background-color: #4682B4;
}}
QPushButton:disabled {{
    background-color: #2b2b2b;
    color: #666;
    border-color: #3c3c3c;
}}
QComboBox {{
    background-color: #3c3c3c;
    color: #ddd;
    border: 1px solid #555;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: {font_size}px;
}}
QComboBox:hover {{
    border-color: #4682B4;
}}
QComboBox QAbstractItemView {{
    background-color: #2b2b2b;
    color: #ddd;
    selection-background-color: #4682B4;
    border: 1px solid #555;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QLineEdit {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 4px;
    border-radius: 3px;
    selection-background-color: #4682B4;
    font-size: {font_size}px;
}}
QLineEdit:focus {{
    border-color: #4682B4;
}}
QSplitter::handle {{
    background-color: #3c3c3c;
}}
QGroupBox {{
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #aaa;
    font-size: {font_size}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QTabBar::tab {{
    background-color: #2b2b2b;
    color: #aaa;
    padding: 6px 14px;
    border: 1px solid #3c3c3c;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: #1e1e1e;
    color: #ddd;
}}
QTableWidget {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    gridline-color: #3c3c3c;
    alternate-background-color: #252525;
    font-size: {font_size}px;
}}
QTableWidget::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QHeaderView::section {{
    background-color: #2b2b2b;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 4px;
    font-size: {font_size}px;
}}
QScrollBar:vertical {{
    background: #1e1e1e;
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #555;
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4682B4;
}}
QScrollBar:horizontal {{
    background: #1e1e1e;
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: #555;
    min-width: 20px;
    border-radius: 5px;
}}
QLabel {{
    background-color: transparent;
    color: #ddd;
    font-size: {font_size}px;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 3px;
    border-radius: 3px;
    font-size: {font_size}px;
}}
QCheckBox, QRadioButton {{
    color: #ddd;
    spacing: 6px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 4px;
    border-radius: 3px;
    selection-background-color: #4682B4;
    font-size: {font_size}px;
}}
QTreeWidget {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    font-size: {font_size}px;
}}
QTreeWidget::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QProgressDialog {{
    background-color: #2b2b2b;
    color: #ddd;
}}
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 1px 4px;
    color: #ddd;
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: #2a2a2a;
    border: 1px solid #555;
    border-radius: 3px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #555;
    selection-background-color: #4682B4;
    outline: none;
}}
"""

_LIGHT_OVERRIDES = """
QMainWindow {{
    background-color: #eee;
}}
QMenuBar {{
    background-color: #f5f5f5;
    color: #333;
    border-bottom: 1px solid #ccc;
    font-size: {font_size}px;
}}
QMenuBar::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QMenu {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
}}
QMenu::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QToolBar {{
    background-color: #f5f5f5;
    border-bottom: 1px solid #ccc;
    spacing: 6px;
    padding: 4px;
}}
QPushButton {{
    background-color: #e8e8e8;
    color: #333;
    border: 1px solid #bbb;
    padding: 5px 12px;
    border-radius: 3px;
    font-size: {font_size}px;
}}
QPushButton:hover {{
    background-color: #ddd;
    border-color: #4682B4;
}}
QPushButton:pressed {{
    background-color: #4682B4;
    color: #fff;
}}
QPushButton:disabled {{
    background-color: #f0f0f0;
    color: #aaa;
    border-color: #ddd;
}}
QComboBox {{
    background-color: #fff;
    color: #333;
    border: 1px solid #bbb;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: {font_size}px;
}}
QComboBox:hover {{
    border-color: #4682B4;
}}
QComboBox QAbstractItemView {{
    background-color: #fff;
    color: #333;
    selection-background-color: #4682B4;
    selection-color: #fff;
    border: 1px solid #ccc;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QLineEdit {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    padding: 4px;
    border-radius: 3px;
    selection-background-color: #4682B4;
    selection-color: #fff;
    font-size: {font_size}px;
}}
QLineEdit:focus {{
    border-color: #4682B4;
}}
QSplitter::handle {{
    background-color: #ccc;
}}
QGroupBox {{
    border: 1px solid #ccc;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #666;
    font-size: {font_size}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QTabBar::tab {{
    background-color: #f0f0f0;
    color: #666;
    padding: 6px 14px;
    border: 1px solid #ccc;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: #fff;
    color: #333;
}}
QTableWidget {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    gridline-color: #ddd;
    alternate-background-color: #f8f8f8;
    font-size: {font_size}px;
}}
QTableWidget::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QHeaderView::section {{
    background-color: #f0f0f0;
    color: #333;
    border: 1px solid #ccc;
    padding: 4px;
    font-size: {font_size}px;
}}
QScrollBar:vertical {{
    background: #f0f0f0;
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #bbb;
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4682B4;
}}
QScrollBar:horizontal {{
    background: #f0f0f0;
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: #bbb;
    min-width: 20px;
    border-radius: 5px;
}}
QLabel {{
    background-color: transparent;
    color: #333;
    font-size: {font_size}px;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    padding: 3px;
    border-radius: 3px;
    font-size: {font_size}px;
}}
QCheckBox, QRadioButton {{
    color: #333;
    spacing: 6px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    padding: 4px;
    border-radius: 3px;
    selection-background-color: #4682B4;
    selection-color: #fff;
    font-size: {font_size}px;
}}
QTreeWidget {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    font-size: {font_size}px;
}}
QTreeWidget::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QProgressDialog {{
    background-color: #f5f5f5;
    color: #333;
}}
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 1px 4px;
    color: #333;
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: #f0f0f0;
    border: 1px solid #bbb;
    border-radius: 3px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    selection-background-color: #4682B4;
    selection-color: #fff;
    outline: none;
}}
"""


def apply_theme(app: QApplication, theme_name: str, font_size: int) -> None:
    """套用指定主題和字體大小。"""
    font_size = max(8, int(font_size))
    setTheme(Theme.DARK if theme_name == "dark" else Theme.LIGHT)
    font = QFont()
    font.setFamilies(["Microsoft JhengHei", "Noto Sans TC", "sans-serif"])
    font.setPixelSize(font_size)
    app.setFont(font)
    apply_custom_overrides(app, theme_name, font_size)


def apply_custom_overrides(app: QApplication, theme_name: str, font_size: int) -> None:
    """為原生 Qt 元件（非 qfluentwidgets）補充樣式。"""
    template = _DARK_OVERRIDES if theme_name == "dark" else _LIGHT_OVERRIDES
    app.setStyleSheet(template.format(font_size=font_size))


def save_preference(theme_name: str, font_size: int) -> None:
    """將主題偏好儲存到 QSettings。"""
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    settings.setValue("theme", theme_name)
    settings.setValue("font_size", font_size)


def load_preference() -> tuple[str, int]:
    """從 QSettings 讀取主題偏好，預設深色 14px。"""
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    theme = settings.value("theme", "dark")
    font_size = int(settings.value("font_size", 14))
    return theme, font_size
