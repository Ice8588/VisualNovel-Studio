"""ColorSlidersPanel：HSL 三條漸層滑桿（色相 / 飽和 / 亮度），浮動小面板。

標準 HSL color picker 模式：
- H（色相 0-360）：彩虹漸層 紅→黃→綠→青→藍→紫→紅
- S（飽和 0-100）：灰 → 當前色相滿飽和
- L（亮度 0-100）：黑 → 當前色相滿色 → 白

任一軸動 → 其他兩軸的 groove 即時重算（呈現「拉這軸會跑到什麼顏色」）。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGridLayout, QLabel, QSlider, QWidget

from src.ui import palette


class ColorSlidersPanel(QWidget):
    """HSL 三滑桿色板。emit `color_changed(hex)` 任一滑桿移動時。"""

    color_changed = pyqtSignal(str)

    # H 軸彩虹固定 7 stop（由 R 360° 回到 R）
    _HUE_GRADIENT = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0,"
        " stop:0 #FF0000, stop:0.167 #FFFF00, stop:0.333 #00FF00,"
        " stop:0.500 #00FFFF, stop:0.667 #0000FF, stop:0.833 #FF00FF,"
        " stop:1 #FF0000)"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("colorSlidersPanel")
        self.setFixedSize(300, 200)
        self._suppress = False
        self._color = QColor(20, 20, 40)
        self._setup_ui()
        palette.register_themed(
            self,
            lambda p: (
                f"#colorSlidersPanel {{ background:{p.surface.name()};"
                f" border:1px solid {p.border.name()}; border-radius:6px; }}"
            ),
        )

    def _setup_ui(self) -> None:
        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(16)  # 上方 hex 區與下方滑桿區的距離

        # 上方：色塊預覽 + hex
        head = QHBoxLayout()
        head.setSpacing(10)
        self._swatch = QLabel()
        self._swatch.setFixedSize(60, 32)
        self._swatch.setStyleSheet("background:#141428; border:1px solid #888; border-radius:4px;")
        head.addWidget(self._swatch)
        self._lbl_hex = QLabel("#141428")
        # task.md #12：font-size 交給 QSS 模板（QApplication.font）統一管理；
        # 此處只指定 monospace family。
        self._lbl_hex.setStyleSheet("font-family:monospace;")
        head.addWidget(self._lbl_hex, 1)
        outer.addLayout(head)

        # 三軸滑桿 grid — 垂直間距拉開填滿剩餘高度（移除底部 stretch）
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(20)  # 三條滑桿之間的距離拉開

        self._sliders: dict[str, QSlider] = {}
        self._labels: dict[str, QLabel] = {}
        rows = [("H", 360, 0, "色相"), ("S", 100, 1, "飽和"), ("L", 100, 2, "亮度")]
        for key, hi, row, name in rows:
            tag = QLabel(name)
            tag.setFixedWidth(36)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(0, hi)
            sl.setSingleStep(1)
            sl.setMinimumWidth(170)
            sl.setFixedHeight(24)
            lbl = QLabel("0")
            lbl.setFixedWidth(36)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("font-family:monospace;")
            grid.addWidget(tag, row, 0)
            grid.addWidget(sl, row, 1)
            grid.addWidget(lbl, row, 2)
            self._sliders[key] = sl
            self._labels[key] = lbl
            sl.valueChanged.connect(lambda _v, k=key: self._on_slider_changed(k))
        outer.addLayout(grid, 1)  # grid 佔剩餘垂直空間

        self._sync_sliders_from_color()
        self._refresh_display()

    # ── 對外 API ──

    def set_color(self, hex_color: str) -> None:
        c = QColor(hex_color)
        if not c.isValid():
            return
        self._color = c
        self._suppress = True
        try:
            self._sync_sliders_from_color()
        finally:
            self._suppress = False
        self._refresh_display()

    def color(self) -> str:
        return self._color.name()

    # ── Internal ──

    def _sync_sliders_from_color(self) -> None:
        c = self._color
        h = c.hslHue() if c.hslHue() >= 0 else 0  # 灰階時 hue=-1 → 0
        self._sliders["H"].setValue(h)
        self._sliders["S"].setValue(int(c.hslSaturation() * 100 / 255))
        self._sliders["L"].setValue(int(c.lightness() * 100 / 255))

    def _on_slider_changed(self, _key: str) -> None:
        if self._suppress:
            return
        h = self._sliders["H"].value()
        s = int(self._sliders["S"].value() * 255 / 100)
        l = int(self._sliders["L"].value() * 255 / 100)
        self._color = QColor.fromHsl(h, s, l)
        self._refresh_display()
        self.color_changed.emit(self._color.name())

    def _refresh_display(self) -> None:
        h = self._sliders["H"].value()
        s_pct = self._sliders["S"].value()
        l_pct = self._sliders["L"].value()
        self._labels["H"].setText(str(h))
        self._labels["S"].setText(str(s_pct))
        self._labels["L"].setText(str(l_pct))
        # 上方色塊 + hex 文字
        cur_hex = self._color.name()
        self._swatch.setStyleSheet(
            f"background:{cur_hex}; border:1px solid #888; border-radius:4px;"
        )
        self._lbl_hex.setText(cur_hex.upper())
        s_255 = int(s_pct * 255 / 100)
        l_255 = int(l_pct * 255 / 100)

        # H 彩虹漸層恆定
        self._sliders["H"].setStyleSheet(self._slider_qss_raw(self._HUE_GRADIENT))
        # S：同 H 同 L 下，灰 → 滿飽和
        gray = QColor.fromHsl(h, 0,    l_255).name()
        full = QColor.fromHsl(h, 255,  l_255).name()
        self._sliders["S"].setStyleSheet(self._slider_qss(gray, full))
        # L：黑 → 當前 H/S 滿色 → 白
        mid  = QColor.fromHsl(h, s_255, 128).name()
        self._sliders["L"].setStyleSheet(self._slider_qss(
            "#000000", "#FFFFFF", mid_stop=mid))

    @staticmethod
    def _slider_qss(start: str, end: str, mid_stop: str | None = None) -> str:
        if mid_stop:
            grad = (
                f"qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                f" stop:0 {start}, stop:0.5 {mid_stop}, stop:1 {end})"
            )
        else:
            grad = (
                f"qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                f" stop:0 {start}, stop:1 {end})"
            )
        return ColorSlidersPanel._slider_qss_raw(grad)

    @staticmethod
    def _slider_qss_raw(grad: str) -> str:
        return (
            "QSlider::groove:horizontal {"
            "  height: 8px; border-radius: 4px;"
            f"  background: {grad};"
            "}"
            "QSlider::handle:horizontal {"
            "  background: #FFFFFF; border: 1px solid #444;"
            "  width: 12px; height: 12px; margin: -3px 0; border-radius: 6px;"
            "}"
        )
