"""Domain 3：特效 Timeline。多條命名軌道。

設計決策（POC 2026-04-19 改）：lane 內 segment **互斥不重疊**（同 stage_panel）。
若使用者要疊加多個特效，請新增多條軌道。

Phase 2 移植自 experimental/timeline_poc/effect_timeline.py，import 改為正式資料模型。
"""

from __future__ import annotations
from dataclasses import dataclass

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.core.models import EffectSegment, EffectTrack, Scene
from src.ui import _timeline_shared as shared


@dataclass
class _DragState:
    seg: EffectSegment
    mode: str
    press_y: int
    orig_start: int
    orig_end: int


def _effect_color(effect_type: str) -> QColor:
    return QColor(shared.EFFECT_COLORS.get(effect_type, "#5F6368"))


class EffectLaneWidget(QWidget):
    cursor_changed = pyqtSignal(int)
    segment_changed = pyqtSignal()       # live drag
    segment_committed = pyqtSignal()     # commit 邊界
    segment_selected = pyqtSignal(object)

    def __init__(self, scene: Scene, track: EffectTrack, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.track = track
        self._cursor_idx: int | None = None
        self._selected: EffectSegment | None = None
        self._drag: _DragState | None = None
        self._drag_dirty: bool = False
        self.setMouseTracking(True)
        self.setMinimumWidth(shared.LANE_WIDTH)
        self.setFixedWidth(shared.LANE_WIDTH)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # 才能收 keyPress (Delete)
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

    def select_segment(self, seg: EffectSegment | None):
        self._selected = seg
        self.update()

    # --- 繪製 ---

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), shared.BG_DARK)

        p.setPen(QPen(shared.GRID_LINE, 1))
        for idx in range(len(self.scene.dialogues) + 1):
            y = shared.idx_to_y(idx)
            p.drawLine(0, y, self.width(), y)

        for seg in self.track.segments:
            self._paint_segment(p, seg)

        if self._cursor_idx is not None:
            y = shared.idx_to_y(self._cursor_idx) + shared.ROW_HEIGHT // 2
            p.setPen(QPen(shared.CURSOR_LINE, 1, Qt.PenStyle.DashLine))
            p.drawLine(0, y, self.width(), y)

        p.end()

    def _seg_rect(self, seg: EffectSegment) -> QRect:
        top, bottom = shared.idx_range_to_rect_y(seg.start, seg.end)
        return QRect(6, top + 3, self.width() - 12, bottom - top - 6)

    def _paint_segment(self, p: QPainter, seg: EffectSegment):
        rect = self._seg_rect(seg)
        base = _effect_color(seg.effect_type)
        p.setBrush(base)
        if seg is self._selected:
            p.setPen(QPen(shared.CURSOR_LINE, 2))
        else:
            p.setPen(QPen(base.darker(140), 1))
        p.drawRoundedRect(rect, 6, 6)

        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("sans", 9, QFont.Weight.Bold))
        metrics = QFontMetrics(p.font())
        label = metrics.elidedText(seg.effect_type, Qt.TextElideMode.ElideRight, rect.width() - 12)
        p.drawText(rect.adjusted(6, 4, -6, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)

        p.setPen(QPen(QColor(255, 255, 255, 130), 2))
        p.drawLine(rect.x() + 12, rect.y() + 1, rect.right() - 12, rect.y() + 1)
        p.drawLine(rect.x() + 12, rect.bottom() - 1, rect.right() - 12, rect.bottom() - 1)

    # --- 互斥 clamp ---

    def _clamp_against_neighbors(self, seg: EffectSegment, new_start: int, new_end: int, edge: str = "start") -> int:
        others = [s for s in self.track.segments if s is not seg]
        if edge == "start":
            for o in others:
                if o.end < seg.start and o.end >= new_start:
                    new_start = o.end + 1
            return new_start
        else:
            for o in others:
                if o.start > seg.end and o.start <= new_end:
                    new_end = o.start - 1
            return new_end

    def _clamp_move(self, seg: EffectSegment, new_start: int, new_end: int) -> tuple[int, int]:
        others = [s for s in self.track.segments if s is not seg]
        for o in others:
            if not (new_end < o.start or new_start > o.end):
                length = new_end - new_start
                if seg.start < o.start:
                    new_end = o.start - 1
                    new_start = new_end - length
                else:
                    new_start = o.end + 1
                    new_end = new_start + length
        return new_start, new_end

    # --- 互動 ---

    def _hit_segment(self, pos) -> tuple[EffectSegment | None, str]:
        for seg in self.track.segments:
            rect = self._seg_rect(seg)
            if not rect.contains(pos):
                continue
            if abs(pos.y() - rect.y()) <= shared.EDGE_HIT:
                return seg, "top"
            if abs(pos.y() - rect.bottom()) <= shared.EDGE_HIT:
                return seg, "bottom"
            return seg, "move"
        return None, ""

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()  # 收到 keyPress (Delete)
        seg, mode = self._hit_segment(ev.pos())
        if seg is None:
            self._selected = None
            self.segment_selected.emit(None)
            cur_idx = shared.y_to_idx(ev.pos().y(), max(0, len(self.scene.dialogues) - 1))
            self.cursor_changed.emit(cur_idx)
            self.update()
            return
        self._selected = seg
        self.segment_selected.emit(seg)
        self._drag = _DragState(seg=seg, mode=mode, press_y=ev.pos().y(), orig_start=seg.start, orig_end=seg.end)
        self.update()

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        seg, _ = self._hit_segment(ev.pos())
        if seg is not None:
            return
        if not self.scene.dialogues:
            return
        max_idx = len(self.scene.dialogues) - 1
        cur = shared.y_to_idx(ev.pos().y(), max_idx)
        end = min(cur + 1, max_idx)
        # 互斥檢查：與既有任何 segment 重疊就不新增
        for s in self.track.segments:
            if not (end < s.start or cur > s.end):
                return
        new_seg = EffectSegment(start=cur, end=end, effect_type="rain", params={})
        self.track.segments.append(new_seg)
        self.track.segments.sort(key=lambda s: s.start)
        self._selected = new_seg
        self.segment_changed.emit()
        self.segment_committed.emit()
        self.segment_selected.emit(new_seg)
        self.update()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._drag is None:
            seg, mode = self._hit_segment(ev.pos())
            if mode in ("top", "bottom"):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif mode == "move":
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()
            cur_idx = shared.y_to_idx(ev.pos().y(), max(0, len(self.scene.dialogues) - 1))
            if cur_idx != self._cursor_idx:
                self._cursor_idx = cur_idx
                self.cursor_changed.emit(cur_idx)
                self.update()
            return

        max_idx = len(self.scene.dialogues) - 1
        d = self._drag
        delta = ev.pos().y() - d.press_y
        delta_rows = round(delta / shared.ROW_HEIGHT)

        before = (d.seg.start, d.seg.end)
        if d.mode == "top":
            new_start = max(0, min(d.orig_start + delta_rows, d.orig_end))
            d.seg.start = self._clamp_against_neighbors(d.seg, new_start, d.seg.end)
        elif d.mode == "bottom":
            new_end = max(d.orig_start, min(d.orig_end + delta_rows, max_idx))
            d.seg.end = self._clamp_against_neighbors(d.seg, d.seg.start, new_end, edge="end")
        else:
            length = d.orig_end - d.orig_start
            new_start = max(0, min(d.orig_start + delta_rows, max_idx - length))
            new_end = new_start + length
            new_start, new_end = self._clamp_move(d.seg, new_start, new_end)
            d.seg.start = new_start
            d.seg.end = new_end

        if (d.seg.start, d.seg.end) != before:
            self._drag_dirty = True
            self.segment_changed.emit()
        self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if self._drag is not None:
            was_dirty = self._drag_dirty
            self._drag = None
            self._drag_dirty = False
            self.track.segments.sort(key=lambda s: s.start)
            self.unsetCursor()
            self.update()
            if was_dirty:
                self.segment_committed.emit()

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self._selected is not None:
            self.track.segments.remove(self._selected)
            self._selected = None
            self.segment_changed.emit()
            self.segment_committed.emit()
            self.segment_selected.emit(None)
            self.update()


class EffectTimelineWidget(QWidget):
    cursor_changed = pyqtSignal(int)
    segment_changed = pyqtSignal()       # live drag
    segment_committed = pyqtSignal()     # commit 邊界
    segment_selected = pyqtSignal(object)
    track_added = pyqtSignal(str)

    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self.lanes: dict[str, EffectLaneWidget] = {}
        for track in scene.effect_tracks:
            self._build_lane(track, append=True)
        self._layout.addStretch(1)

    def _build_lane(self, track: EffectTrack, append: bool):
        lane = EffectLaneWidget(self.scene, track)
        self.lanes[track.name] = lane
        lane.cursor_changed.connect(self.cursor_changed.emit)
        lane.segment_changed.connect(self.segment_changed.emit)
        lane.segment_committed.connect(self.segment_committed.emit)
        lane.segment_selected.connect(self._on_seg_selected)
        if append:
            self._layout.addWidget(lane)
        else:
            self._layout.insertWidget(self._layout.count() - 1, lane)

    def add_track(self, name: str):
        track = EffectTrack(name=name, segments=[])
        self.scene.effect_tracks.append(track)
        self._build_lane(track, append=False)
        self.track_added.emit(name)
        # 新增軌道是 commit 動作（不是 live drag），讓 caller 重載預覽 / 標 dirty
        self.segment_committed.emit()

    def _on_seg_selected(self, seg):
        sender = self.sender()
        for lane in self.lanes.values():
            if lane is not sender:
                lane.select_segment(None)
        self.segment_selected.emit(seg)

    def set_cursor(self, idx: int | None):
        for lane in self.lanes.values():
            lane.set_cursor(idx)

    def refresh(self):
        for lane in self.lanes.values():
            lane.refresh()

    def global_rect_of_segment(self, seg: EffectSegment):
        """回傳 seg 在螢幕全域座標的 QRect；找不到回 None。Phase 4 給 SegmentEditor 浮動定位用。"""
        from PyQt6.QtCore import QRect, QPoint
        for lane in self.lanes.values():
            if seg in lane.track.segments:
                top, bottom = shared.idx_range_to_rect_y(seg.start, seg.end)
                top_left_global = lane.mapToGlobal(QPoint(0, top))
                return QRect(top_left_global, QPoint(top_left_global.x() + lane.width(),
                                                      top_left_global.y() + (bottom - top)))
        return None


class EffectTimelineHeader(QWidget):
    def __init__(self, scene: Scene, on_add_track, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._on_add_track = on_add_track
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        for track in scene.effect_tracks:
            self._layout.addWidget(self._make_label(track.name))
        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(32, 28)
        self._add_btn.clicked.connect(self._handle_add)
        self._add_btn.setStyleSheet("background:#3D3D40; color:#E8E8E8; border:none; border-radius:4px;")
        self._layout.addWidget(self._add_btn)
        self._layout.addStretch(1)

    def _make_label(self, name: str) -> QLabel:
        l = QLabel(name)
        l.setFixedWidth(shared.LANE_WIDTH)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setStyleSheet("color:#9AA0A6; background:#252526; padding:6px 0; font-weight:bold;")
        return l

    def append_track(self, name: str):
        idx = self._layout.indexOf(self._add_btn)
        self._layout.insertWidget(idx, self._make_label(name))

    def _handle_add(self):
        n = len(self.scene.effect_tracks) + 1
        self._on_add_track(f"軌道{n}")
