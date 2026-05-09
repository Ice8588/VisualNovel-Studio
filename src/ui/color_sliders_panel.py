"""ColorSlidersPanel：HSL 三滑桿 + 即時 hex 顯示，內嵌（非 popup）色板。

使用情境：preview toolbar 的「對話框顏色」色塊按鈕點擊後展開此面板，
比 QColorDialog 簡潔許多。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.ui import palette


class ColorSlidersPanel(QWidget):
    """HSL 三滑桿色板。emit `color_changed(hex)` 當任一滑桿移動。

    set_color(hex) 同步外部值（不觸發 signal）。
    """

    color_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("colorSlidersPanel")
        self._suppress = False
        self._hex = "#141428"
        self._setup_ui()
        # 註冊主題感知背景
        palette.register_themed(
            self,
            lambda p: (
                f"#colorSlidersPanel {{ background:{p.surface.name()};"
                f" border:1px solid {p.border.name()}; border-radius:6px; padding:6px; }}"
            ),
        )

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # 上排：色塊預覽 + hex 顯示
        head = QHBoxLayout()
        head.setSpacing(8)
        self._swatch = QLabel()
        self._swatch.setFixedSize(36, 24)
        self._swatch.setStyleSheet(
            f"background-color:{self._hex}; border:1px solid #888; border-radius:3px;"
        )
        head.addWidget(self._swatch)
        self._lbl_hex = QLabel(self._hex.upper())
        self._lbl_hex.setStyleSheet("font-family: monospace; font-size: 12px;")
        head.addWidget(self._lbl_hex, 1)
        root.addLayout(head)

        # 三滑桿：H / S / L
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)

        self._sl_h = self._make_slider(0, 360)
        self._sl_s = self._make_slider(0, 100)
        self._sl_l = self._make_slider(0, 100)

        self._lbl_h_val = QLabel("0")
        self._lbl_s_val = QLabel("0")
        self._lbl_l_val = QLabel("0")
        for lbl in (self._lbl_h_val, self._lbl_s_val, self._lbl_l_val):
            lbl.setFixedWidth(30)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("font-family: monospace;")

        grid.addWidget(QLabel("色相"), 0, 0)
        grid.addWidget(self._sl_h, 0, 1)
        grid.addWidget(self._lbl_h_val, 0, 2)
        grid.addWidget(QLabel("飽和"), 1, 0)
        grid.addWidget(self._sl_s, 1, 1)
        grid.addWidget(self._lbl_s_val, 1, 2)
        grid.addWidget(QLabel("亮度"), 2, 0)
        grid.addWidget(self._sl_l, 2, 1)
        grid.addWidget(self._lbl_l_val, 2, 2)
        root.addLayout(grid)

        for sl in (self._sl_h, self._sl_s, self._sl_l):
            sl.valueChanged.connect(self._on_slider_changed)

        # 套用 _hex 初始值到三滑桿
        self.set_color(self._hex)

    @staticmethod
    def _make_slider(lo: int, hi: int) -> QSlider:
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(lo, hi)
        sl.setSingleStep(1)
        sl.setMinimumWidth(160)
        return sl

    # ── 對外 API ──

    def set_color(self, hex_color: str) -> None:
        """同步外部值，不 emit signal。"""
        c = QColor(hex_color)
        if not c.isValid():
            return
        self._hex = c.name()  # 標準化
        h = c.hslHue() if c.hslHue() >= 0 else 0       # 灰階時 hue=-1
        s = c.hslSaturation() * 100 // 255
        l = c.lightness() * 100 // 255
        self._suppress = True
        try:
            self._sl_h.setValue(h)
            self._sl_s.setValue(s)
            self._sl_l.setValue(l)
        finally:
            self._suppress = False
        self._refresh_display()

    def color(self) -> str:
        return self._hex

    # ── Internal ──

    def _on_slider_changed(self, _v: int) -> None:
        if self._suppress:
            return
        h = self._sl_h.value()
        s = self._sl_s.value() * 255 // 100
        l = self._sl_l.value() * 255 // 100
        c = QColor.fromHsl(h, s, l)
        self._hex = c.name()
        self._refresh_display()
        self.color_changed.emit(self._hex)

    def _refresh_display(self) -> None:
        self._swatch.setStyleSheet(
            f"background-color:{self._hex}; border:1px solid #888; border-radius:3px;"
        )
        self._lbl_hex.setText(self._hex.upper())
        self._lbl_h_val.setText(str(self._sl_h.value()))
        self._lbl_s_val.setText(str(self._sl_s.value()))
        self._lbl_l_val.setText(str(self._sl_l.value()))
