"""Domain 3：特效 Timeline。多條命名軌道，每條 lane 內 segment 允許 overlap。

POC 重疊繪製策略：先以 Y 區間找出彼此重疊的 segments 群組，群組內按 start 排序後分配 column index，
寬度均分。簡單但能驗證疊加可行。
"""

from __future__ import annotations
from dataclasses import dataclass

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import shared
from .models import EffectSegment, EffectTrack, Scene


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
    segment_changed = pyqtSignal()
    segment_selected = pyqtSignal(object)

    def __init__(self, scene: Scene, track: EffectTrack, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.track = track
        self._cursor_idx: int | None = None
        self._selected: EffectSegment | None = None
        self._drag: _DragState | None = None
        self._segment_columns: dict[int, tuple[int, int]] = {}  # id(seg) -> (col, n_cols)
        self.setMouseTracking(True)
        self.setMinimumWidth(shared.LANE_WIDTH)
        self.setFixedWidth(shared.LANE_WIDTH)
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

    # --- 繪製：先計算重疊群組的分側 ---

    def _compute_columns(self):
        self._segment_columns.clear()
        # Greedy interval graph coloring：對每個 segment 指派最小 column 號
        sorted_segs = sorted(self.track.segments, key=lambda s: (s.start, s.end))
        active: list[tuple[int, EffectSegment]] = []  # (col, seg)
        for seg in sorted_segs:
            # 釋放已結束的 col
            active = [(c, s) for c, s in active if s.end >= seg.start]
            used_cols = {c for c, _ in active}
            col = 0
            while col in used_cols:
                col += 1
            active.append((col, seg))
            self._segment_columns[id(seg)] = (col, 0)
        # 補回每個群組的 max cols（同個重疊群組共享 n_cols）
        # 簡化：對每列 idx 算當下 active 數，segment 的 n_cols 取它生命週期中最大值
        for seg in sorted_segs:
            max_n = 1
            for idx in range(seg.start, seg.end + 1):
                count = sum(
                    1 for s in self.track.segments if s.start <= idx <= s.end
                )
                max_n = max(max_n, count)
            col, _ = self._segment_columns[id(seg)]
            self._segment_columns[id(seg)] = (col, max_n)

    def paintEvent(self, _event):
        self._compute_columns()
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
        col, n_cols = self._segment_columns.get(id(seg), (0, 1))
        n_cols = max(n_cols, 1)
        top, bottom = shared.idx_range_to_rect_y(seg.start, seg.end)
        usable_w = self.width() - 12  # 6px padding 兩側
        col_w = usable_w / n_cols
        x = 6 + int(col * col_w)
        w = max(int(col_w) - 2, 16)
        return QRect(x, top + 3, w, bottom - top - 6)

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
        p.setFont(QFont("sans", 8, QFont.Weight.Bold))
        metrics = QFontMetrics(p.font())
        label = metrics.elidedText(seg.effect_type, Qt.TextElideMode.ElideRight, rect.width() - 6)
        p.drawText(rect.adjusted(4, 2, -4, -2), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)

        p.setPen(QPen(QColor(255, 255, 255, 130), 2))
        p.drawLine(rect.x() + 6, rect.y() + 1, rect.right() - 6, rect.y() + 1)
        p.drawLine(rect.x() + 6, rect.bottom() - 1, rect.right() - 6, rect.bottom() - 1)

    # --- 互動 ---

    def _hit_segment(self, pos) -> tuple[EffectSegment | None, str]:
        for seg in self.track.segments:
            rect = self._seg_rect(seg)
            if not rect.contains(pos):
                # 也允許僅 y 在範圍內、x 落在 segment 視覺欄內
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
        seg, mode = self._hit_segment(ev.pos())
        if seg is None:
            self._selected = None
            self.segment_selected.emit(None)
            cur_idx = shared.y_to_idx(ev.pos().y(), len(self.scene.dialogues) - 1)
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
        max_idx = len(self.scene.dialogues) - 1
        cur = shared.y_to_idx(ev.pos().y(), max_idx)
        end = min(cur + 1, max_idx)
        new_seg = EffectSegment(start=cur, end=end, effect_type="rain", params={})
        self.track.segments.append(new_seg)
        self.track.segments.sort(key=lambda s: s.start)
        self._selected = new_seg
        self.segment_changed.emit()
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
            cur_idx = shared.y_to_idx(ev.pos().y(), len(self.scene.dialogues) - 1)
            if cur_idx != self._cursor_idx:
                self._cursor_idx = cur_idx
                self.cursor_changed.emit(cur_idx)
                self.update()
            return

        max_idx = len(self.scene.dialogues) - 1
        d = self._drag
        delta = ev.pos().y() - d.press_y
        delta_rows = round(delta / shared.ROW_HEIGHT)

        if d.mode == "top":
            d.seg.start = max(0, min(d.orig_start + delta_rows, d.orig_end))
        elif d.mode == "bottom":
            d.seg.end = max(d.orig_start, min(d.orig_end + delta_rows, max_idx))
        else:
            length = d.orig_end - d.orig_start
            new_start = max(0, min(d.orig_start + delta_rows, max_idx - length))
            d.seg.start = new_start
            d.seg.end = new_start + length

        self.segment_changed.emit()
        self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if self._drag is not None:
            self._drag = None
            self.track.segments.sort(key=lambda s: s.start)
            self.unsetCursor()
            self.update()

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self._selected is not None:
            self.track.segments.remove(self._selected)
            self._selected = None
            self.segment_changed.emit()
            self.segment_selected.emit(None)
            self.update()


class EffectTimelineWidget(QWidget):
    cursor_changed = pyqtSignal(int)
    segment_changed = pyqtSignal()
    segment_selected = pyqtSignal(object)

    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self.lanes: dict[str, EffectLaneWidget] = {}
        # 先用 addWidget 依序加入既有 tracks
        for track in scene.effect_tracks:
            self._build_lane(track, append=True)
        self._layout.addStretch(1)

    def _build_lane(self, track: EffectTrack, append: bool):
        lane = EffectLaneWidget(self.scene, track)
        self.lanes[track.name] = lane
        lane.cursor_changed.connect(self.cursor_changed.emit)
        lane.segment_changed.connect(self.segment_changed.emit)
        lane.segment_selected.connect(self._on_seg_selected)
        if append:
            self._layout.addWidget(lane)
        else:
            # 已有 stretch，插在 stretch 之前
            self._layout.insertWidget(self._layout.count() - 1, lane)

    def add_track(self, name: str):
        track = EffectTrack(name=name, segments=[])
        self.scene.effect_tracks.append(track)
        self._build_lane(track, append=False)

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


class EffectTimelineHeader(QWidget):
    def __init__(self, scene: Scene, on_add_track, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._on_add_track = on_add_track
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        # 先 addWidget 依序加標籤
        for track in scene.effect_tracks:
            self._layout.addWidget(self._make_label(track.name))
        # 然後加 + 按鈕，最後 stretch
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
        # 插入點：+ 按鈕之前
        idx = self._layout.indexOf(self._add_btn)
        self._layout.insertWidget(idx, self._make_label(name))

    def _handle_add(self):
        n = len(self.scene.effect_tracks) + 1
        self._on_add_track(f"軌道{n}")
