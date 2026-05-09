"""主題系統：以 qfluentwidgets 深 / 淺色主題為底，再用本檔的 QSS 模板補上原生 Qt
元件的樣式。所有顏色由 `src.ui.palette.Palette` 注入，本檔只負責結構與字體大小。

設計演進
--------
- v1：6 主題各自一份 ~280 行 QSS 模板（_DARK_OVERRIDES … _IVORY_OVERRIDES），
  總共 ~1670 行；新增主題或調色都要改 6 個地方。
- v2（current）：一份 `_QSS_TEMPLATE`（~280 行），裡面用 `{accent}` `{bg}`
  `{text_primary}` 等占位符；切主題時用 `palette.qss_substitutions()` 填值。
  Single source of truth = palette.py。
"""

from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

from src.ui import palette as _palette

_SETTINGS_ORG = "VisualNovelStudio"
_SETTINGS_APP = "VNStudio"

# QSS 模板：所有顏色用 `{name}` 占位（由 palette.qss_substitutions() 填）；
# `{font_size}` 由本檔的 apply_custom_overrides 直接填。
# 雙大括號 `{{` / `}}` 是 .format() 的 escape，最終輸出會變成 `{` / `}`。
_QSS_TEMPLATE = """
QMainWindow {{
    background-color: {bg};
}}
QMenuBar {{
    background-color: {title_bar};
    color: {text_primary};
    border-bottom: 1px solid {border};
    font-size: {font_size}px;
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: {accent};
    color: {accent_text};
}}
QMenu {{
    background-color: {surface};
    color: {text_primary};
    border: 1px solid {border};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 18px;
}}
QMenu::item:selected {{
    background-color: {accent};
    color: {accent_text};
}}
QToolBar {{
    background-color: {title_bar};
    border-bottom: 1px solid {border};
    spacing: 6px;
    padding: 4px;
}}
QPushButton {{
    background-color: {button_bg};
    color: {text_primary};
    border: 1px solid {border};
    padding: 7px 16px;
    border-radius: 3px;
    font-size: {font_size}px;
}}
QPushButton:hover {{
    background-color: {button_hover};
    border-color: {border_focus};
}}
QPushButton:pressed {{
    background-color: {accent};
    color: {accent_text};
}}
QPushButton:disabled {{
    background-color: {surface};
    color: {text_disabled};
    border-color: {border};
}}
QComboBox {{
    background-color: {button_bg};
    color: {text_primary};
    border: 1px solid {border};
    padding: 6px 28px 6px 12px;
    border-radius: 3px;
    font-size: {font_size}px;
}}
QComboBox:hover {{
    border-color: {border_focus};
}}
QComboBox QAbstractItemView {{
    background-color: {surface};
    color: {text_primary};
    selection-background-color: {accent};
    selection-color: {accent_text};
    border: 1px solid {border};
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
    background-color: {input_bg};
    color: {text_primary};
    border: 1px solid {border};
    padding: 7px 10px;
    border-radius: 3px;
    selection-background-color: {accent};
    selection-color: {accent_text};
    font-size: {font_size}px;
}}
QLineEdit:focus {{
    border-color: {border_focus};
}}
QSplitter::handle {{
    background-color: {border};
}}
QSplitter::handle:hover {{
    background-color: {border_focus};
}}
QGroupBox {{
    border: 1px solid {border};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: {text_secondary};
    font-size: {font_size}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QTabBar::tab {{
    background-color: {surface};
    color: {text_secondary};
    padding: 6px 14px;
    border: 1px solid {border};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: {bg};
    color: {text_primary};
}}
QTableWidget {{
    background-color: {input_bg};
    color: {text_primary};
    border: 1px solid {border};
    gridline-color: {border};
    alternate-background-color: {surface};
    font-size: {font_size}px;
}}
QTableWidget::item:selected {{
    background-color: {accent};
    color: {accent_text};
}}
QHeaderView::section {{
    background-color: {surface};
    color: {text_primary};
    border: 1px solid {border};
    padding: 6px 10px;
    font-size: {font_size}px;
}}
QScrollBar:vertical {{
    background: {bg};
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {border};
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {border_focus};
}}
QScrollBar:horizontal {{
    background: {bg};
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {border};
    min-width: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {border_focus};
}}
QLabel {{
    background-color: transparent;
    color: {text_primary};
    font-size: {font_size}px;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: {input_bg};
    color: {text_primary};
    border: 1px solid {border};
    padding: 6px 24px 6px 10px;
    border-radius: 3px;
    font-size: {font_size}px;
    min-height: 22px;
}}
QCheckBox, QRadioButton {{
    color: {text_primary};
    spacing: 8px;
    font-size: {font_size}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: {input_bg};
    color: {text_primary};
    border: 1px solid {border};
    padding: 8px 10px;
    border-radius: 3px;
    selection-background-color: {accent};
    selection-color: {accent_text};
    font-size: {font_size}px;
}}
QTreeWidget {{
    background-color: {input_bg};
    color: {text_primary};
    border: 1px solid {border};
    font-size: {font_size}px;
}}
QTreeWidget::item:selected {{
    background-color: {accent};
    color: {accent_text};
}}
QProgressDialog {{
    background-color: {surface};
    color: {text_primary};
}}
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 4px 8px;
    color: {text_primary};
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: {surface_alt};
    border: 1px solid {border};
    border-radius: 3px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: {input_bg};
    color: {text_primary};
    border: 1px solid {border};
    selection-background-color: {accent};
    selection-color: {accent_text};
    outline: none;
}}
QPushButton#dashedButton {{
    border: 2px dashed {border};
    border-radius: 4px;
    color: {text_secondary};
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: {text_secondary};
    color: {text_primary};
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: {text_secondary};
    background: transparent;
    font-size: 18px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: {danger};
}}
QDialog {{
    background-color: {bg};
    color: {text_primary};
}}
/* QMessageBox / QInputDialog / QFileDialog 是 QDialog 子類，但部分 native style
   不繼承 QDialog 規則（Windows / Linux 預設 palette 介入）。明確指定確保
   淺色主題下 bg / text 可讀。 */
QMessageBox, QInputDialog, QFileDialog {{
    background-color: {bg};
    color: {text_primary};
}}
QMessageBox QLabel, QInputDialog QLabel, QFileDialog QLabel {{
    color: {text_primary};
}}
QInputDialog QLineEdit, QFileDialog QLineEdit {{
    background-color: {input_bg};
    color: {text_primary};
    border: 1px solid {border};
}}
QLabel#spritePreview {{
    border: 1px solid {border};
    background-color: {input_bg};
    color: {text_secondary};
}}
"""

# qfluentwidgets 只支援 DARK / LIGHT；其他主題一律用 DARK / LIGHT 作底
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
    if theme_name not in _FLUENT_THEME_MAP:
        theme_name = "dark"
    setTheme(_FLUENT_THEME_MAP[theme_name])
    font = QFont()
    font.setFamilies(["Microsoft JhengHei", "Noto Sans TC", "sans-serif"])
    font.setPixelSize(font_size)
    app.setFont(font)
    # palette 先切，apply_custom_overrides + register_themed 才會拿到正確顏色
    _palette.set_theme(theme_name)
    apply_custom_overrides(app, theme_name, font_size)


def apply_custom_overrides(app: QApplication, theme_name: str, font_size: int) -> None:
    """為原生 Qt 元件（非 qfluentwidgets）補充樣式；顏色由 palette 注入。"""
    subs = _palette.qss_substitutions(_palette.current())
    subs["font_size"] = font_size
    app.setStyleSheet(_QSS_TEMPLATE.format(**subs))


def save_preference(theme_name: str, font_size: int) -> None:
    """將主題偏好儲存到 QSettings。"""
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    settings.setValue("theme", theme_name)
    settings.setValue("font_size", font_size)


def load_preference() -> tuple[str, int]:
    """從 QSettings 讀取主題偏好，預設 Ivory Titanium 18px；夾至 [18, 28]。"""
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    theme = settings.value("theme", "ivory")
    try:
        font_size = int(settings.value("font_size", 18))
    except (TypeError, ValueError):
        font_size = 18
    # 全專案字體 ≥ 18px（任務 #2）；上限 28 避免元件裁切
    font_size = max(18, min(28, font_size))
    return theme, font_size
