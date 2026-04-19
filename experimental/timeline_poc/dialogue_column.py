"""Domain 1：對話卡片列。自繪 QWidget + 手動處理拖拉重排。

固定列高 (ROW_HEIGHT)，與右側 stage/effect 共用 Y 軸。
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from . import shared
from .models import Scene


class DialogueColumn(QWidget):
    cursor_changed = pyqtSignal(int)       # 使用者點/hover 某列
    dialogue_moved = pyqtSignal(int, int)  # src_idx, dst_idx
    selection_changed = pyqtSignal(int)    # 單選簡化版

    WIDTH_HINT = 360

    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._cursor_idx: int | None = None
        self._selected_idx: int | None = None
        self._drag_src: int | None = None
        self._drag_press_y: int = 0
        self._drag_current_y: int = 0
        self._is_dragging: bool = False
        self.setMouseTracking(True)
        self.setMinimumWidth(self.WIDTH_HINT)
        self._update_height()

    def _update_height(self):
        self.setMinimumHeight(shared.idx_to_y(len(self.scene.dialogues)))

    def set_cursor(self, idx: int | None):
        if idx == self._cursor_idx:
            return
        self._cursor_idx = idx
        self.update()

    def refresh(self):
        self._update_height()
        self.update()

    # --- 繪製 ---

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), shared.BG_PANEL)

        for idx, dlg in enumerate(self.scene.dialogues):
            top = shared.idx_to_y(idx)
            rect = QRect(0, top, self.width(), shared.ROW_HEIGHT)
            self._paint_card(p, rect, idx, dlg)

        # 游標線
        if self._cursor_idx is not None:
            y = shared.idx_to_y(self._cursor_idx) + shared.ROW_HEIGHT // 2
            p.setPen(QPen(shared.CURSOR_LINE, 1, Qt.PenStyle.DashLine))
            p.drawLine(0, y, self.width(), y)

        # 拖拉中 ghost + drop indicator
        if self._is_dragging and self._drag_src is not None:
            dst = self._drop_target_idx(self._drag_current_y)
            self._paint_drop_indicator(p, dst)
            self._paint_drag_ghost(p, self._drag_current_y, self.scene.dialogues[self._drag_src])

        p.end()

    def _paint_card(self, p: QPainter, rect: QRect, idx: int, dlg):
        inner = rect.adjusted(6, 4, -6, -4)

        # 卡片底色
        is_narration = dlg.type == "narration"
        is_selected = idx == self._selected_idx
        bg = QColor("#2D2D30") if is_narration else QColor("#2E3440")
        if is_selected:
            bg = bg.lighter(130)
        p.setBrush(bg)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawRoundedRect(inner, 6, 6)

        # 選中邊框
        if is_selected:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(shared.CURSOR_LINE, 2))
            p.drawRoundedRect(inner.adjusted(1, 1, -1, -1), 6, 6)

        # Gutter 索引
        p.setPen(shared.TEXT_MUTED)
        p.setFont(QFont("sans", 9))
        p.drawText(
            QRect(inner.x() + 2, inner.y(), 24, inner.height()),
            Qt.AlignmentFlag.AlignCenter,
            str(idx + 1),
        )

        # 類型 icon（▶ 對話 / ▒ 旁白）
        icon = "▶" if not is_narration else "▒"
        p.setPen(shared.TEXT_MUTED if is_narration else shared.TEXT_PRIMARY)
        p.drawText(
            QRect(inner.x() + 24, inner.y(), 16, inner.height()),
            Qt.AlignmentFlag.AlignCenter,
            icon,
        )

        text_x = inner.x() + 46
        text_right = inner.right() - 4

        # 角色 chip
        if dlg.character:
            chip_color = shared.character_color(dlg.character)
            metrics = QFontMetrics(QFont("sans", 9, QFont.Weight.Bold))
            label = dlg.character
            chip_w = metrics.horizontalAdvance(label) + 14
            chip_rect = QRect(text_x, inner.y() + 6, chip_w, 18)
            p.setBrush(chip_color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(chip_rect, 9, 9)
            p.setFont(QFont("sans", 9, QFont.Weight.Bold))
            p.setPen(QColor("#FFFFFF"))
            p.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, label)
            text_x += chip_w + 6

        # 文字效果 chip（右側貼邊）
        if dlg.text_effects:
            label = " ".join(f"·{e}" for e in dlg.text_effects)
            metrics = QFontMetrics(QFont("sans", 8))
            chip_w = metrics.horizontalAdvance(label) + 10
            chip_rect = QRect(text_right - chip_w, inner.y() + 6, chip_w, 16)
            p.setBrush(QColor(255, 255, 255, 30))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(chip_rect, 8, 8)
            p.setFont(QFont("sans", 8))
            p.setPen(shared.TEXT_MUTED)
            p.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, label)
            text_right -= chip_w + 6

        # 文字內容
        text_rect = QRect(text_x, inner.y() + 22, text_right - text_x, inner.height() - 24)
        p.setFont(QFont("sans", 10))
        p.setPen(shared.TEXT_PRIMARY if not is_narration else shared.TEXT_MUTED)
        metrics = QFontMetrics(p.font())
        elided = metrics.elidedText(dlg.text, Qt.TextElideMode.ElideRight, text_rect.width())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

    def _paint_drop_indicator(self, p: QPainter, dst: int):
        y = shared.idx_to_y(dst)
        p.setPen(QPen(shared.DROP_INDICATOR, 3))
        p.drawLine(6, y, self.width() - 6, y)

    def _paint_drag_ghost(self, p: QPainter, y: int, dlg):
        ghost_top = y - shared.ROW_HEIGHT // 2
        rect = QRect(8, ghost_top, self.width() - 16, shared.ROW_HEIGHT - 4)
        p.setOpacity(0.75)
        p.setBrush(QColor("#3D4455"))
        p.setPen(QPen(shared.DROP_INDICATOR, 1))
        p.drawRoundedRect(rect, 6, 6)
        p.setPen(shared.TEXT_PRIMARY)
        p.setFont(QFont("sans", 10))
        metrics = QFontMetrics(p.font())
        label = metrics.elidedText(dlg.text, Qt.TextElideMode.ElideRight, rect.width() - 20)
        p.drawText(rect.adjusted(12, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter, label)
        p.setOpacity(1.0)

    # --- 互動 ---

    def _idx_at(self, y: int) -> int | None:
        idx = y // shared.ROW_HEIGHT
        if 0 <= idx < len(self.scene.dialogues):
            return idx
        return None

    def _drop_target_idx(self, y: int) -> int:
        """拖拉放開時的目標位置（插入點）。"""
        raw = y // shared.ROW_HEIGHT
        if (y % shared.ROW_HEIGHT) > shared.ROW_HEIGHT // 2:
            raw += 1
        return max(0, min(raw, len(self.scene.dialogues)))

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._idx_at(ev.pos().y())
        if idx is None:
            return
        self._selected_idx = idx
        self.selection_changed.emit(idx)
        self.cursor_changed.emit(idx)
        self._drag_src = idx
        self._drag_press_y = ev.pos().y()
        self._drag_current_y = ev.pos().y()
        self._is_dragging = False
        self.update()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._drag_src is not None:
            if abs(ev.pos().y() - self._drag_press_y) > shared.DRAG_THRESHOLD:
                self._is_dragging = True
            self._drag_current_y = ev.pos().y()
            self.update()
        else:
            idx = self._idx_at(ev.pos().y())
            if idx is not None and idx != self._cursor_idx:
                self._cursor_idx = idx
                self.cursor_changed.emit(idx)
                self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if self._drag_src is None:
            return
        if self._is_dragging:
            dst = self._drop_target_idx(ev.pos().y())
            # 正規化：dst 是插入點，如果 src < dst，實際移動到 dst-1
            if dst > self._drag_src:
                dst -= 1
            if dst != self._drag_src:
                self.dialogue_moved.emit(self._drag_src, dst)
                self._selected_idx = dst
        self._drag_src = None
        self._is_dragging = False
        self.update()
