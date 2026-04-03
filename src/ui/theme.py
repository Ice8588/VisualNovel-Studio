"""主題系統：深色/淺色主題切換，字體大小調整。"""

from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

_DARK_TEMPLATE = """
QWidget {{
    background-color: #2b2b2b;
    color: #ddd;
    font-size: {font_size}px;
    font-family: "Microsoft JhengHei", "Noto Sans TC", sans-serif;
}}

QMainWindow {{
    background-color: #1e1e1e;
}}

QMenuBar {{
    background-color: #2b2b2b;
    color: #ddd;
    border-bottom: 1px solid #3c3c3c;
}}

QMenuBar::item:selected {{
    background-color: #3c3c3c;
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

QListWidget {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    alternate-background-color: #252525;
}}

QListWidget::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}

QTableWidget {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    gridline-color: #3c3c3c;
    alternate-background-color: #252525;
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
}}

QComboBox {{
    background-color: #3c3c3c;
    color: #ddd;
    border: 1px solid #555;
    padding: 4px 8px;
    border-radius: 3px;
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

QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 4px;
    border-radius: 3px;
    selection-background-color: #4682B4;
}}

QLineEdit:focus, QPlainTextEdit:focus {{
    border-color: #4682B4;
}}

QGroupBox {{
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #aaa;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}

QSplitter::handle {{
    background-color: #3c3c3c;
}}

QProgressDialog {{
    background-color: #2b2b2b;
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

QLabel {{
    background-color: transparent;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 3px;
    border-radius: 3px;
}}

QRadioButton, QCheckBox {{
    color: #ddd;
    spacing: 6px;
}}

QDialogButtonBox QPushButton {{
    min-width: 70px;
}}

QTabWidget::pane {{
    border: 1px solid #3c3c3c;
    background-color: #2b2b2b;
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
"""

_LIGHT_TEMPLATE = """
QWidget {{
    background-color: #f5f5f5;
    color: #333;
    font-size: {font_size}px;
    font-family: "Microsoft JhengHei", "Noto Sans TC", sans-serif;
}}

QMainWindow {{
    background-color: #eee;
}}

QMenuBar {{
    background-color: #f5f5f5;
    color: #333;
    border-bottom: 1px solid #ccc;
}}

QMenuBar::item:selected {{
    background-color: #ddd;
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

QListWidget {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    alternate-background-color: #f8f8f8;
}}

QListWidget::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}

QTableWidget {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    gridline-color: #ddd;
    alternate-background-color: #f8f8f8;
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
}}

QComboBox {{
    background-color: #fff;
    color: #333;
    border: 1px solid #bbb;
    padding: 4px 8px;
    border-radius: 3px;
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

QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    padding: 4px;
    border-radius: 3px;
    selection-background-color: #4682B4;
    selection-color: #fff;
}}

QLineEdit:focus, QPlainTextEdit:focus {{
    border-color: #4682B4;
}}

QGroupBox {{
    border: 1px solid #ccc;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #666;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}

QSplitter::handle {{
    background-color: #ccc;
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

QLabel {{
    background-color: transparent;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    padding: 3px;
    border-radius: 3px;
}}

QRadioButton, QCheckBox {{
    color: #333;
    spacing: 6px;
}}

QDialogButtonBox QPushButton {{
    min-width: 70px;
}}

QTabWidget::pane {{
    border: 1px solid #ccc;
    background-color: #fff;
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
"""

_SETTINGS_ORG = "VisualNovelStudio"
_SETTINGS_APP = "VNStudio"


def apply_theme(app: QApplication, theme_name: str, font_size: int) -> None:
    """套用指定主題和字體大小。"""
    font_size = max(8, int(font_size))
    template = _DARK_TEMPLATE if theme_name == "dark" else _LIGHT_TEMPLATE
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
