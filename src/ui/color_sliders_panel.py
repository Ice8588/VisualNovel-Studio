"""ColorSlidersPanel：RGB 三軸色板 + 即時漸層滑桿，浮動 200×100 小面板。

設計：
- 三條 RGB 滑桿水平排列（R / G / B 各一橫排）
- 每條 slider 的 groove 用 qlineargradient 顯示「該軸 0→255 變化時的顏色」
  例：R 滑桿在當前 G、B 不變下，由 (0,G,B) 漸變到 (255,G,B)
  使用者拖任一軸時，其他兩軸的漸層即時更新
- 浮動：caller 把它當子 widget show()，不進 layout，靠 move() 定位
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGridLayout, QLabel, QSlider, QWidget

from src.ui import palette


class ColorSlidersPanel(QWidget):
    """RGB 三滑桿色板（200×100）。emit `color_changed(hex)` 滑桿移動時。"""

    color_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("colorSlidersPanel")
        self.setFixedSize(220, 110)
        self._suppress = False
        self._r, self._g, self._b = 20, 20, 40  # 預設 #141428
        self._setup_ui()
        # 主題感知：外框 / 內距 / 陰影感
        palette.register_themed(
            self,
            lambda p: (
                f"#colorSlidersPanel {{ background:{p.surface.name()};"
                f" border:1px solid {p.border.name()}; border-radius:6px; }}"
            ),
        )

    def _setup_ui(self) -> None:
        grid = QGridLayout(self)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)

        self._sl_r = self._make_slider()
        self._sl_g = self._make_slider()
        self._sl_b = self._make_slider()
        self._lbl_r = QLabel("0"); self._lbl_g = QLabel("0"); self._lbl_b = QLabel("0")

        for c, lbl, sl, name in (
            (0, self._lbl_r, self._sl_r, "R"),
            (1, self._lbl_g, self._sl_g, "G"),
            (2, self._lbl_b, self._sl_b, "B"),
        ):
            tag = QLabel(name)
            tag.setFixedWidth(12)
            tag.setStyleSheet("font-family:monospace; font-weight:bold;")
            lbl.setFixedWidth(28)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("font-family:monospace;")
            grid.addWidget(tag, c, 0)
            grid.addWidget(sl, c, 1)
            grid.addWidget(lbl, c, 2)

        for sl in (self._sl_r, self._sl_g, self._sl_b):
            sl.valueChanged.connect(self._on_slider_changed)

        # 一次刷新 stylesheet + label
        self._suppress = True
        self._sl_r.setValue(self._r)
        self._sl_g.setValue(self._g)
        self._sl_b.setValue(self._b)
        self._suppress = False
        self._refresh()

    @staticmethod
    def _make_slider() -> QSlider:
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(0, 255)
        sl.setSingleStep(1)
        sl.setMinimumWidth(120)
        sl.setFixedHeight(20)
        return sl

    # ── 對外 API ──

    def set_color(self, hex_color: str) -> None:
        c = QColor(hex_color)
        if not c.isValid():
            return
        self._suppress = True
        try:
            self._r, self._g, self._b = c.red(), c.green(), c.blue()
            self._sl_r.setValue(self._r)
            self._sl_g.setValue(self._g)
            self._sl_b.setValue(self._b)
        finally:
            self._suppress = False
        self._refresh()

    def color(self) -> str:
        return QColor(self._r, self._g, self._b).name()

    # ── Internal ──

    def _on_slider_changed(self, _v: int) -> None:
        if self._suppress:
            return
        self._r = self._sl_r.value()
        self._g = self._sl_g.value()
        self._b = self._sl_b.value()
        self._refresh()
        self.color_changed.emit(self.color())

    def _refresh(self) -> None:
        self._lbl_r.setText(str(self._r))
        self._lbl_g.setText(str(self._g))
        self._lbl_b.setText(str(self._b))
        # 三條 slider groove 用 qlineargradient 顯示「該軸 0→255 對顏色的影響」
        self._sl_r.setStyleSheet(self._slider_qss(
            f"rgb(0,{self._g},{self._b})", f"rgb(255,{self._g},{self._b})"))
        self._sl_g.setStyleSheet(self._slider_qss(
            f"rgb({self._r},0,{self._b})", f"rgb({self._r},255,{self._b})"))
        self._sl_b.setStyleSheet(self._slider_qss(
            f"rgb({self._r},{self._g},0)", f"rgb({self._r},{self._g},255)"))

    @staticmethod
    def _slider_qss(start: str, end: str) -> str:
        # groove 用線性漸層（左→右）；handle 簡化成白色細邊圓角
        return (
            "QSlider::groove:horizontal {"
            "  height: 8px; border-radius: 4px;"
            f"  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"    stop:0 {start}, stop:1 {end});"
            "}"
            "QSlider::handle:horizontal {"
            "  background: #FFFFFF; border: 1px solid #444;"
            "  width: 12px; height: 12px; margin: -3px 0; border-radius: 6px;"
            "}"
        )
