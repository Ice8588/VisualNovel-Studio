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
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QMenu {{
    background-color: #2b2b2b;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 18px;
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
    padding: 7px 16px;
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
    padding: 6px 28px 6px 12px;
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
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 20px;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QLineEdit {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 7px 10px;
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
    padding: 6px 10px;
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
    padding: 6px 24px 6px 10px;
    border-radius: 3px;
    font-size: {font_size}px;
    min-height: 22px;
}}
/* Phase 4 修 #5：不再 override up-button/down-button；讓原生 Qt style 畫上下箭頭，
   使用者才能用上下調節，不必只靠手動輸入。 */
QCheckBox, QRadioButton {{
    color: #ddd;
    spacing: 8px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #3c3c3c;
    padding: 8px 10px;
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
    padding: 4px 8px;
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
QPushButton#dashedButton {{
    border: 2px dashed #555;
    border-radius: 4px;
    color: #888;
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: #888;
    color: #bbb;
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: #888;
    background: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: #e05555;
}}
QSplitter::handle:hover {{
    background-color: #4682B4;
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
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: #4682B4;
    color: #fff;
}}
QMenu {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 18px;
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
    padding: 7px 16px;
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
    padding: 6px 28px 6px 12px;
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
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 20px;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QLineEdit {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    padding: 7px 10px;
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
    padding: 6px 10px;
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
    padding: 6px 24px 6px 10px;
    border-radius: 3px;
    font-size: {font_size}px;
    min-height: 22px;
}}
/* Phase 4 修 #5：見深色主題同段註解。 */
QCheckBox, QRadioButton {{
    color: #333;
    spacing: 8px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    padding: 8px 10px;
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
    padding: 4px 8px;
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
QPushButton#dashedButton {{
    border: 2px dashed #bbb;
    border-radius: 4px;
    color: #888;
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: #666;
    color: #333;
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: #999;
    background: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: #c43434;
}}
QSplitter::handle:hover {{
    background-color: #4682B4;
}}
"""

# ---------------------------------------------------------------------------
# Parchment Poetry 羊皮紙詩歌
# ---------------------------------------------------------------------------
_PARCHMENT_OVERRIDES = """
QMainWindow {{
    background-color: #F5ECD7;
}}
QMenuBar {{
    background-color: #EADFBF;
    color: #2B2416;
    border-bottom: 1px solid #C9B98E;
    font-size: {font_size}px;
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: #3A4A6B;
    color: #F5ECD7;
}}
QMenu {{
    background-color: #F5ECD7;
    color: #2B2416;
    border: 1px solid #C9B98E;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 18px;
}}
QMenu::item:selected {{
    background-color: #3A4A6B;
    color: #F5ECD7;
}}
QToolBar {{
    background-color: #EADFBF;
    border-bottom: 1px solid #C9B98E;
    spacing: 6px;
    padding: 4px;
}}
QPushButton {{
    background-color: #EADFBF;
    color: #2B2416;
    border: 1px solid #C9B98E;
    padding: 7px 16px;
    border-radius: 4px;
    font-size: {font_size}px;
}}
QPushButton:hover {{
    background-color: #DBCBA0;
}}
QPushButton:pressed {{
    background-color: #C15F3C;
    color: #F5ECD7;
    border-color: #C15F3C;
}}
QPushButton:disabled {{
    background-color: #EADFBF;
    color: #8A7B5C;
    border-color: #C9B98E;
}}
QComboBox {{
    background-color: #F5ECD7;
    color: #2B2416;
    border: 1px solid #C9B98E;
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
    font-size: {font_size}px;
}}
QComboBox:hover {{
    border-color: #3A4A6B;
}}
QComboBox QAbstractItemView {{
    background-color: #F5ECD7;
    color: #2B2416;
    selection-background-color: #3A4A6B;
    selection-color: #F5ECD7;
    border: 1px solid #C9B98E;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 20px;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QLineEdit {{
    background-color: #F5ECD7;
    color: #2B2416;
    border: 1px solid #C9B98E;
    padding: 7px 10px;
    border-radius: 4px;
    selection-background-color: #C8CEDB;
    font-size: {font_size}px;
}}
QLineEdit:focus {{
    border-color: #3A4A6B;
}}
QSplitter::handle {{
    background-color: #C9B98E;
}}
QGroupBox {{
    border: 1px solid #C9B98E;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #5A4E36;
    font-size: {font_size}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QTabBar::tab {{
    background-color: #DBCBA0;
    color: #5A4E36;
    padding: 6px 14px;
    border: 1px solid #C9B98E;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: #F5ECD7;
    color: #2B2416;
}}
QTableWidget {{
    background-color: #F5ECD7;
    color: #2B2416;
    border: 1px solid #C9B98E;
    gridline-color: #DBCBA0;
    alternate-background-color: #EADFBF;
    font-size: {font_size}px;
}}
QTableWidget::item:selected {{
    background-color: #C8CEDB;
    color: #2B2416;
}}
QHeaderView::section {{
    background-color: #DBCBA0;
    color: #2B2416;
    border: 1px solid #C9B98E;
    padding: 6px 10px;
    font-size: {font_size}px;
}}
QScrollBar:vertical {{
    background: #F5ECD7;
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #DBCBA0;
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #8A7B5C;
}}
QScrollBar:horizontal {{
    background: #F5ECD7;
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: #DBCBA0;
    min-width: 20px;
    border-radius: 5px;
}}
QLabel {{
    background-color: transparent;
    color: #2B2416;
    font-size: {font_size}px;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: #F5ECD7;
    color: #2B2416;
    border: 1px solid #C9B98E;
    padding: 6px 24px 6px 10px;
    border-radius: 4px;
    font-size: {font_size}px;
    min-height: 22px;
}}
QCheckBox, QRadioButton {{
    color: #2B2416;
    spacing: 8px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: #F5ECD7;
    color: #2B2416;
    border: 1px solid #C9B98E;
    padding: 8px 10px;
    border-radius: 4px;
    selection-background-color: #C8CEDB;
    font-size: {font_size}px;
}}
QTreeWidget {{
    background-color: #F5ECD7;
    color: #2B2416;
    border: 1px solid #C9B98E;
    font-size: {font_size}px;
}}
QTreeWidget::item:selected {{
    background-color: #C8CEDB;
    color: #2B2416;
}}
QProgressDialog {{
    background-color: #EADFBF;
    color: #2B2416;
}}
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 4px 8px;
    color: #2B2416;
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: #DBCBA0;
    border: 1px solid #C9B98E;
    border-radius: 4px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: #F5ECD7;
    color: #2B2416;
    border: 1px solid #C9B98E;
    selection-background-color: #3A4A6B;
    selection-color: #F5ECD7;
    outline: none;
}}
QPushButton#dashedButton {{
    border: 2px dashed #C9B98E;
    border-radius: 4px;
    color: #8A7B5C;
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: #5A4E36;
    color: #2B2416;
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: #8A7B5C;
    background: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: #C15F3C;
}}
QSplitter::handle:hover {{
    background-color: #3A4A6B;
}}
"""

# ---------------------------------------------------------------------------
# Midnight Ink 墨夜
# ---------------------------------------------------------------------------
_MIDNIGHT_OVERRIDES = """
QMainWindow {{
    background-color: #141414;
}}
QMenuBar {{
    background-color: #1A1A1A;
    color: #C0C0C0;
    border-bottom: 1px solid #2A2A2A;
    font-size: {font_size}px;
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: #5A6A8B;
    color: #F0F0F0;
}}
QMenu {{
    background-color: #1E1E1E;
    color: #C0C0C0;
    border: 1px solid #2A2A2A;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 18px;
}}
QMenu::item:selected {{
    background-color: #5A6A8B;
    color: #F0F0F0;
}}
QToolBar {{
    background-color: #1A1A1A;
    border-bottom: 1px solid #2A2A2A;
    spacing: 6px;
    padding: 4px;
}}
QPushButton {{
    background-color: #1E1E1E;
    color: #C0C0C0;
    border: 1px solid #303030;
    padding: 7px 16px;
    border-radius: 4px;
    font-size: {font_size}px;
}}
QPushButton:hover {{
    background-color: #252525;
    color: #F0F0F0;
    border-color: #7090A0;
}}
QPushButton:pressed {{
    background-color: #7090A0;
    color: #141414;
    border-color: #527080;
}}
QPushButton:disabled {{
    background-color: #1A1A1A;
    color: #505050;
    border-color: #2A2A2A;
}}
QComboBox {{
    background-color: #1A1A1A;
    color: #C0C0C0;
    border: 1px solid #2E2E2E;
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
    font-size: {font_size}px;
}}
QComboBox:hover {{
    border-color: #7090A0;
}}
QComboBox QAbstractItemView {{
    background-color: #1E1E1E;
    color: #C0C0C0;
    selection-background-color: #5A6A8B;
    selection-color: #F0F0F0;
    border: 1px solid #2E2E2E;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 20px;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QLineEdit {{
    background-color: #141414;
    color: #D0D0D0;
    border: 1px solid #2A2A2A;
    padding: 7px 10px;
    border-radius: 4px;
    selection-background-color: #1E2535;
    font-size: {font_size}px;
}}
QLineEdit:focus {{
    border-color: #7090A0;
}}
QSplitter::handle {{
    background-color: #2A2A2A;
}}
QGroupBox {{
    border: 1px solid #2A2A2A;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #7A7A7A;
    font-size: {font_size}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QTabBar::tab {{
    background-color: #1A1A1A;
    color: #7A7A7A;
    padding: 6px 14px;
    border: 1px solid #2A2A2A;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: #141414;
    color: #F0F0F0;
}}
QTableWidget {{
    background-color: #141414;
    color: #D0D0D0;
    border: 1px solid #2A2A2A;
    gridline-color: #1E1E1E;
    alternate-background-color: #181818;
    font-size: {font_size}px;
}}
QTableWidget::item:selected {{
    background-color: #1E2535;
    color: #F0F0F0;
}}
QHeaderView::section {{
    background-color: #1A1A1A;
    color: #B0B0B0;
    border: 1px solid #2A2A2A;
    padding: 6px 10px;
    font-size: {font_size}px;
}}
QScrollBar:vertical {{
    background: #141414;
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #2E2E2E;
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #7090A0;
}}
QScrollBar:horizontal {{
    background: #141414;
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: #2E2E2E;
    min-width: 20px;
    border-radius: 5px;
}}
QLabel {{
    background-color: transparent;
    color: #C0C0C0;
    font-size: {font_size}px;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: #141414;
    color: #D0D0D0;
    border: 1px solid #2A2A2A;
    padding: 6px 24px 6px 10px;
    border-radius: 4px;
    font-size: {font_size}px;
    min-height: 22px;
}}
QCheckBox, QRadioButton {{
    color: #C0C0C0;
    spacing: 8px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: #141414;
    color: #D0D0D0;
    border: 1px solid #2A2A2A;
    padding: 8px 10px;
    border-radius: 4px;
    selection-background-color: #1E2535;
    font-size: {font_size}px;
}}
QTreeWidget {{
    background-color: #141414;
    color: #D0D0D0;
    border: 1px solid #2A2A2A;
    font-size: {font_size}px;
}}
QTreeWidget::item:selected {{
    background-color: #1E2535;
    color: #F0F0F0;
}}
QProgressDialog {{
    background-color: #1A1A1A;
    color: #C0C0C0;
}}
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 4px 8px;
    color: #C0C0C0;
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: #1E1E1E;
    border: 1px solid #2E2E2E;
    border-radius: 4px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: #1A1A1A;
    color: #C0C0C0;
    border: 1px solid #2E2E2E;
    selection-background-color: #5A6A8B;
    selection-color: #F0F0F0;
    outline: none;
}}
QPushButton#dashedButton {{
    border: 2px dashed #303030;
    border-radius: 4px;
    color: #505050;
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: #7090A0;
    color: #B0B0B0;
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: #505050;
    background: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: #CC3A3A;
}}
QSplitter::handle:hover {{
    background-color: #7090A0;
}}
"""

# ---------------------------------------------------------------------------
# Figma Dark 飽和深色
# ---------------------------------------------------------------------------
_FIGMA_DARK_OVERRIDES = """
QMainWindow {{
    background-color: #16151E;
}}
QMenuBar {{
    background-color: #1C1B26;
    color: #9090B8;
    border-bottom: 1px solid #2A2738;
    font-size: {font_size}px;
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: #B06EF7;
    color: #F4EEFF;
}}
QMenu {{
    background-color: #1C1B26;
    color: #9090B8;
    border: 1px solid #30304A;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 18px;
}}
QMenu::item:selected {{
    background-color: #B06EF7;
    color: #F4EEFF;
}}
QToolBar {{
    background-color: #1C1B26;
    border-bottom: 1px solid #2A2738;
    spacing: 6px;
    padding: 4px;
}}
QPushButton {{
    background-color: #221F32;
    color: #9090B8;
    border: 1px solid #30304A;
    padding: 7px 16px;
    border-radius: 4px;
    font-size: {font_size}px;
}}
QPushButton:hover {{
    background-color: #2A2840;
    color: #D0D0E8;
    border-color: #B06EF7;
}}
QPushButton:pressed {{
    background-color: #B06EF7;
    color: #F4EEFF;
    border-color: #8E50D4;
}}
QPushButton:disabled {{
    background-color: #1C1B26;
    color: #404060;
    border-color: #252338;
}}
QComboBox {{
    background-color: #1A1928;
    color: #B0B0C8;
    border: 1px solid #30304A;
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
    font-size: {font_size}px;
}}
QComboBox:hover {{
    border-color: #B06EF7;
}}
QComboBox QAbstractItemView {{
    background-color: #1C1B26;
    color: #9090B8;
    selection-background-color: #B06EF7;
    selection-color: #F4EEFF;
    border: 1px solid #30304A;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 20px;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QLineEdit {{
    background-color: #1A1928;
    color: #B0AACE;
    border: 1px solid #30304A;
    padding: 7px 10px;
    border-radius: 4px;
    selection-background-color: #231B38;
    font-size: {font_size}px;
}}
QLineEdit:focus {{
    border-color: #B06EF7;
}}
QSplitter::handle {{
    background-color: #20203A;
}}
QGroupBox {{
    border: 1px solid #30304A;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #4A4868;
    font-size: {font_size}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QTabBar::tab {{
    background-color: #1C1B26;
    color: #4A4868;
    padding: 6px 14px;
    border: 1px solid #30304A;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: #16151E;
    color: #F0F0FF;
}}
QTableWidget {{
    background-color: #16151E;
    color: #B0AACE;
    border: 1px solid #30304A;
    gridline-color: #1E1D2A;
    alternate-background-color: #1A1928;
    font-size: {font_size}px;
}}
QTableWidget::item:selected {{
    background-color: #231B38;
    color: #F0F0FF;
}}
QHeaderView::section {{
    background-color: #1C1B26;
    color: #9090B8;
    border: 1px solid #30304A;
    padding: 6px 10px;
    font-size: {font_size}px;
}}
QScrollBar:vertical {{
    background: #16151E;
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #30304A;
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #B06EF7;
}}
QScrollBar:horizontal {{
    background: #16151E;
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: #30304A;
    min-width: 20px;
    border-radius: 5px;
}}
QLabel {{
    background-color: transparent;
    color: #9090B8;
    font-size: {font_size}px;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: #1A1928;
    color: #B0AACE;
    border: 1px solid #30304A;
    padding: 6px 24px 6px 10px;
    border-radius: 4px;
    font-size: {font_size}px;
    min-height: 22px;
}}
QCheckBox, QRadioButton {{
    color: #9090B8;
    spacing: 8px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: #1A1928;
    color: #B0AACE;
    border: 1px solid #30304A;
    padding: 8px 10px;
    border-radius: 4px;
    selection-background-color: #231B38;
    font-size: {font_size}px;
}}
QTreeWidget {{
    background-color: #16151E;
    color: #B0AACE;
    border: 1px solid #30304A;
    font-size: {font_size}px;
}}
QTreeWidget::item:selected {{
    background-color: #231B38;
    color: #F0F0FF;
}}
QProgressDialog {{
    background-color: #1C1B26;
    color: #9090B8;
}}
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 4px 8px;
    color: #9090B8;
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: #221F32;
    border: 1px solid #30304A;
    border-radius: 4px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: #1C1B26;
    color: #9090B8;
    border: 1px solid #30304A;
    selection-background-color: #B06EF7;
    selection-color: #F4EEFF;
    outline: none;
}}
QPushButton#dashedButton {{
    border: 2px dashed #30304A;
    border-radius: 4px;
    color: #4A4868;
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: #B06EF7;
    color: #9090B8;
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: #4A4868;
    background: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: #CC3A3A;
}}
QSplitter::handle:hover {{
    background-color: #B06EF7;
}}
"""

# ---------------------------------------------------------------------------
# Ivory Titanium 象牙白鈦
# tokens: paper #FDFDFC / paper-2 #F4F3EF / ink #1C1B19 / accent #3A75D9 / rule #DCDAD3
# ---------------------------------------------------------------------------
_IVORY_OVERRIDES = """
QMainWindow {{
    background-color: #FDFDFC;
}}
QMenuBar {{
    background-color: #F4F3EF;
    color: #1C1B19;
    border-bottom: 1px solid #DCDAD3;
    font-size: {font_size}px;
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: #3A75D9;
    color: #FDFDFC;
}}
QMenu {{
    background-color: #FDFDFC;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 18px;
}}
QMenu::item:selected {{
    background-color: #3A75D9;
    color: #FDFDFC;
}}
QToolBar {{
    background-color: #F4F3EF;
    border-bottom: 1px solid #DCDAD3;
    spacing: 6px;
    padding: 4px;
}}
QPushButton {{
    background-color: #F4F3EF;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    padding: 7px 16px;
    border-radius: 4px;
    font-size: {font_size}px;
}}
QPushButton:hover {{
    background-color: #ECEAE3;
    border-color: #3A75D9;
}}
QPushButton:pressed {{
    background-color: #3A75D9;
    color: #FDFDFC;
    border-color: #2E62B8;
}}
QPushButton:disabled {{
    background-color: #F4F3EF;
    color: #A8A6A0;
    border-color: #DCDAD3;
}}
QComboBox {{
    background-color: #FDFDFC;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
    font-size: {font_size}px;
}}
QComboBox:hover {{
    border-color: #3A75D9;
}}
QComboBox QAbstractItemView {{
    background-color: #FDFDFC;
    color: #1C1B19;
    selection-background-color: #3A75D9;
    selection-color: #FDFDFC;
    border: 1px solid #DCDAD3;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 20px;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QLineEdit {{
    background-color: #FDFDFC;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    padding: 7px 10px;
    border-radius: 4px;
    selection-background-color: #3A75D9;
    selection-color: #FDFDFC;
    font-size: {font_size}px;
}}
QLineEdit:focus {{
    border-color: #3A75D9;
}}
QSplitter::handle {{
    background-color: #DCDAD3;
}}
QGroupBox {{
    border: 1px solid #DCDAD3;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #5C5A53;
    font-size: {font_size}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QTabBar::tab {{
    background-color: #F4F3EF;
    color: #5C5A53;
    padding: 6px 14px;
    border: 1px solid #DCDAD3;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: #FDFDFC;
    color: #1C1B19;
}}
QTableWidget {{
    background-color: #FDFDFC;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    gridline-color: #ECEAE3;
    alternate-background-color: #F8F7F4;
    font-size: {font_size}px;
}}
QTableWidget::item:selected {{
    background-color: #3A75D9;
    color: #FDFDFC;
}}
QHeaderView::section {{
    background-color: #F4F3EF;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    padding: 6px 10px;
    font-size: {font_size}px;
}}
QScrollBar:vertical {{
    background: #FDFDFC;
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #DCDAD3;
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #3A75D9;
}}
QScrollBar:horizontal {{
    background: #FDFDFC;
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: #DCDAD3;
    min-width: 20px;
    border-radius: 5px;
}}
QLabel {{
    background-color: transparent;
    color: #1C1B19;
    font-size: {font_size}px;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: #FDFDFC;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    padding: 6px 24px 6px 10px;
    border-radius: 4px;
    font-size: {font_size}px;
    min-height: 22px;
}}
QCheckBox, QRadioButton {{
    color: #1C1B19;
    spacing: 8px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: #FDFDFC;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    padding: 8px 10px;
    border-radius: 4px;
    selection-background-color: #3A75D9;
    selection-color: #FDFDFC;
    font-size: {font_size}px;
}}
QTreeWidget {{
    background-color: #FDFDFC;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    font-size: {font_size}px;
}}
QTreeWidget::item:selected {{
    background-color: #3A75D9;
    color: #FDFDFC;
}}
QProgressDialog {{
    background-color: #F4F3EF;
    color: #1C1B19;
}}
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 4px 8px;
    color: #1C1B19;
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: #ECEAE3;
    border: 1px solid #DCDAD3;
    border-radius: 4px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: #FDFDFC;
    color: #1C1B19;
    border: 1px solid #DCDAD3;
    selection-background-color: #3A75D9;
    selection-color: #FDFDFC;
    outline: none;
}}
QPushButton#dashedButton {{
    border: 2px dashed #DCDAD3;
    border-radius: 4px;
    color: #8A8880;
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: #5C5A53;
    color: #1C1B19;
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: #A8A6A0;
    background: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: #C43434;
}}
QSplitter::handle:hover {{
    background-color: #3A75D9;
}}
"""

# 主題名稱 → QSS template 的對照表
_OVERRIDES_MAP = {
    "dark":        _DARK_OVERRIDES,
    "light":       _LIGHT_OVERRIDES,
    "parchment":   _PARCHMENT_OVERRIDES,
    "midnight":    _MIDNIGHT_OVERRIDES,
    "figma-dark":  _FIGMA_DARK_OVERRIDES,
    "ivory":       _IVORY_OVERRIDES,
}

# qfluentwidgets 只支援 DARK / LIGHT；其他主題一律用 DARK 作底
_FLUENT_THEME_MAP = {
    "dark":       Theme.DARK,
    "light":      Theme.LIGHT,
    "parchment":  Theme.LIGHT,
    "midnight":   Theme.DARK,
    "figma-dark": Theme.DARK,
    "ivory":      Theme.LIGHT,
}


def apply_theme(app: QApplication, theme_name: str, font_size: int) -> None:
    """套用指定主題和字體大小。"""
    font_size = max(8, int(font_size))
    setTheme(_FLUENT_THEME_MAP.get(theme_name, Theme.DARK))
    font = QFont()
    font.setFamilies(["Microsoft JhengHei", "Noto Sans TC", "sans-serif"])
    font.setPixelSize(font_size)
    app.setFont(font)
    apply_custom_overrides(app, theme_name, font_size)


def apply_custom_overrides(app: QApplication, theme_name: str, font_size: int) -> None:
    """為原生 Qt 元件（非 qfluentwidgets）補充樣式。"""
    template = _OVERRIDES_MAP.get(theme_name, _DARK_OVERRIDES)
    app.setStyleSheet(template.format(font_size=font_size))


def save_preference(theme_name: str, font_size: int) -> None:
    """將主題偏好儲存到 QSettings。"""
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    settings.setValue("theme", theme_name)
    settings.setValue("font_size", font_size)


def load_preference() -> tuple[str, int]:
    """從 QSettings 讀取主題偏好，預設 Ivory Titanium 18px；上限夾至 28。"""
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    theme = settings.value("theme", "ivory")
    try:
        font_size = int(settings.value("font_size", 18))
    except (TypeError, ValueError):
        font_size = 18
    # UI 字體上限 28px（避免元件裁切）；低於 14 也視為不合理，夾回 14
    font_size = max(14, min(28, font_size))
    return theme, font_size
