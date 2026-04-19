"""Domain 2：舞台面板。三條獨立 lane（左/中/右），不允許 overlap。

Segment 互動：
- 拖頂緣  → 改 start
- 拖底緣  → 改 end
- 拖中段  → 整段平移
- 雙擊空白 → 新增 segment（預設長度 2 列）
- 點選 segment → 高亮，emit segment_selected

Phase 2 移植自 experimental/timeline_poc/stage_panel.py，import 改為正式資料模型。
"""

from __future__ import annotations
from dataclasses import dataclass

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from src.core.models import Scene, StageSegment
from src.ui import _timeline_shared as shared


@dataclass
class _DragState:
    seg: StageSegment
    mode: str  # "top" | "bottom" | "move"
    press_y: int
    orig_start: int
    orig_end: int


class StageLaneWidget(QWidget):
    cursor_changed = pyqtSignal(int)
    segment_changed = pyqtSignal()              # 每次 mouseMove 拖端點都觸發（live；僅供 widget 自我重繪）
    segment_committed = pyqtSignal()            # commit 邊界：拖完 / 雙擊新增 / Delete（caller 用來重載預覽）
    segment_selected = pyqtSignal(object)       # StageSegment | None
    # Phase 4：跨 lane 拖拉。release 時若 mouse 在別條 lane 上，由 StagePanel 接手 transfer
    request_lane_transfer = pyqtSignal(object, object)  # (segment, release_global_pos: QPoint)

    def __init__(self, scene: Scene, position: str, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.position = position  # "left" | "center" | "right"
        self._cursor_idx: int | None = None
        self._selected: StageSegment | None = None
        self._drag: _DragState | None = None
        self._drag_dirty: bool = False  # mouseMove 期間有實際變動才在 release 時 emit committed
        self._character_colors: dict[str, str] = {}
        self.setMouseTracking(True)
        self.setMinimumWidth(shared.LANE_WIDTH)
        self.setFixedWidth(shared.LANE_WIDTH)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # 才能收 keyPress (Delete)
        self._update_height()

    def _segments(self) -> list[StageSegment]:
        return self.scene.all_stage_lanes()[self.position]

    def _update_height(self):
        self.setMinimumHeight(shared.idx_to_y(len(self.scene.dialogues)))

    def set_cursor(self, idx: int | None):
        if idx == self._cursor_idx:
            return
        self._cursor_idx = idx
        self.update()

    def set_character_colors(self, mapping: dict[str, str]) -> None:
        self._character_colors = dict(mapping or {})
        self.update()

    def refresh(self):
        self._update_height()
        self.update()

    def select_segment(self, seg: StageSegment | None):
        self._selected = seg
        self.update()

    # --- 繪製 ---

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), shared.BG_DARK)

        # 列分隔線
        p.setPen(QPen(shared.GRID_LINE, 1))
        for idx in range(len(self.scene.dialogues) + 1):
            y = shared.idx_to_y(idx)
            p.drawLine(0, y, self.width(), y)

        # Segments
        for seg in self._segments():
            self._paint_segment(p, seg)

        # 游標線
        if self._cursor_idx is not None:
            y = shared.idx_to_y(self._cursor_idx) + shared.ROW_HEIGHT // 2
            p.setPen(QPen(shared.CURSOR_LINE, 1, Qt.PenStyle.DashLine))
            p.drawLine(0, y, self.width(), y)

        p.end()

    def _paint_segment(self, p: QPainter, seg: StageSegment):
        top, bottom = shared.idx_range_to_rect_y(seg.start, seg.end)
        rect = QRect(6, top + 3, self.width() - 12, bottom - top - 6)

        base = shared.character_color(
            seg.character, self._character_colors.get(seg.character)
        )
        p.setBrush(base)
        if seg is self._selected:
            p.setPen(QPen(shared.CURSOR_LINE, 2))
        else:
            p.setPen(QPen(base.darker(140), 1))
        p.drawRoundedRect(rect, 6, 6)

        # Label：character / costume / sprite
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("sans", 9, QFont.Weight.Bold))
        label_rect = QRect(rect.x() + 6, rect.y() + 4, rect.width() - 12, 16)
        metrics = QFontMetrics(p.font())
        name = metrics.elidedText(seg.character, Qt.TextElideMode.ElideRight, label_rect.width())
        p.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        if rect.height() > 30:
            p.setFont(QFont("sans", 8))
            p.setPen(QColor(255, 255, 255, 200))
            details = []
            if seg.costume:
                details.append(seg.costume)
            if seg.sprite:
                details.append(seg.sprite)
            if details:
                detail_rect = QRect(rect.x() + 6, rect.y() + 20, rect.width() - 12, rect.height() - 22)
                txt = "\n".join(details)
                p.drawText(
                    detail_rect,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                    txt,
                )

        # 端緣 grip
        p.setPen(QPen(QColor(255, 255, 255, 130), 2))
        p.drawLine(rect.x() + 12, rect.y() + 1, rect.right() - 12, rect.y() + 1)
        p.drawLine(rect.x() + 12, rect.bottom() - 1, rect.right() - 12, rect.bottom() - 1)

    # --- 互動 ---

    def _hit_segment(self, y: int) -> tuple[StageSegment | None, str]:
        for seg in self._segments():
            top, bottom = shared.idx_range_to_rect_y(seg.start, seg.end)
            if abs(y - top) <= shared.EDGE_HIT:
                return seg, "top"
            if abs(y - bottom) <= shared.EDGE_HIT:
                return seg, "bottom"
            if top < y < bottom:
                return seg, "move"
        return None, ""

    def _y_to_row_snap(self, y: int) -> int:
        """以列高 snap，回傳「最接近的列邊界」對應的 idx（0..N）。"""
        max_idx = len(self.scene.dialogues)
        idx = round(y / shared.ROW_HEIGHT)
        return max(0, min(idx, max_idx))

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()  # 收到 keyPress (Delete)
        seg, mode = self._hit_segment(ev.pos().y())
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
        seg, _ = self._hit_segment(ev.pos().y())
        if seg is not None:
            return  # 已經在 segment 上
        if not self.scene.dialogues:
            return
        # Bug B fix：沒有任何角色時不新增 ghost segment（character 必填、不能是不存在的名字）
        if not self._character_colors:
            return
        max_idx = len(self.scene.dialogues) - 1
        cur = shared.y_to_idx(ev.pos().y(), max_idx)
        end = min(cur + 1, max_idx)
        # 避免與既有 segment 重疊（lane 內 mutual exclusive）
        for s in self._segments():
            if not (end < s.start or cur > s.end):
                return  # 與既有重疊就不新增
        default_char = next(iter(self._character_colors.keys()))
        new_seg = StageSegment(start=cur, end=end, character=default_char, costume=None, sprite=None)
        self._segments().append(new_seg)
        self._segments().sort(key=lambda s: s.start)
        self._selected = new_seg
        self.segment_changed.emit()
        self.segment_committed.emit()
        self.segment_selected.emit(new_seg)
        self.update()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._drag is None:
            seg, mode = self._hit_segment(ev.pos().y())
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
        else:  # move
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
            dragged_seg = self._drag.seg
            drag_mode = self._drag.mode
            self._drag = None
            self._drag_dirty = False
            self._segments().sort(key=lambda s: s.start)
            self.unsetCursor()
            self.update()
            # Phase 4：若拖中段（move 模式）且 release 點在 lane 外，請求 StagePanel 跨 lane 轉移
            if drag_mode == "move":
                local_pos = ev.pos()
                if local_pos.x() < 0 or local_pos.x() > self.width():
                    self.request_lane_transfer.emit(
                        dragged_seg, ev.globalPosition().toPoint()
                    )
                    return  # transfer 內含 commit；不重複 emit
            if was_dirty:
                self.segment_committed.emit()

    def _clamp_against_neighbors(self, seg: StageSegment, new_start: int, new_end: int, edge: str = "start") -> int:
        """調整端點時不允許跨越鄰居 segment。"""
        others = [s for s in self._segments() if s is not seg]
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

    def _clamp_move(self, seg: StageSegment, new_start: int, new_end: int) -> tuple[int, int]:
        others = [s for s in self._segments() if s is not seg]
        for o in others:
            # 若移動會與 o 重疊，貼到 o 的上緣或下緣
            if not (new_end < o.start or new_start > o.end):
                length = new_end - new_start
                if seg.start < o.start:  # 從上方來
                    new_end = o.start - 1
                    new_start = new_end - length
                else:
                    new_start = o.end + 1
                    new_end = new_start + length
        return new_start, new_end

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self._selected is not None:
            self._segments().remove(self._selected)
            self._selected = None
            self.segment_changed.emit()
            self.segment_committed.emit()
            self.segment_selected.emit(None)
            self.update()


class StagePanel(QWidget):
    """三條 lane 水平排列。"""

    cursor_changed = pyqtSignal(int)
    segment_changed = pyqtSignal()       # live drag（每 mouseMove）
    segment_committed = pyqtSignal()     # commit 邊界
    segment_selected = pyqtSignal(object)

    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.lanes: dict[str, StageLaneWidget] = {}
        for pos in ("left", "center", "right"):
            lane = StageLaneWidget(scene, pos)
            self.lanes[pos] = lane
            lane.cursor_changed.connect(self.cursor_changed.emit)
            lane.segment_changed.connect(self.segment_changed.emit)
            lane.segment_committed.connect(self.segment_committed.emit)
            lane.segment_selected.connect(self._on_segment_selected)
            # Phase 4：跨 lane 拖拉
            lane.request_lane_transfer.connect(self._on_request_lane_transfer)
            layout.addWidget(lane)

        layout.addStretch(1)
        self.setMinimumWidth(shared.LANE_WIDTH * 3 + 4)

    def _on_segment_selected(self, seg):
        sender = self.sender()
        for lane in self.lanes.values():
            if lane is not sender:
                lane.select_segment(None)
        self.segment_selected.emit(seg)

    def _on_request_lane_transfer(self, seg: StageSegment, release_global_pos):
        """Phase 4：使用者把 segment 拖到別條 lane 上 release，這裡執行轉移。

        若 release 點不在任何 lane 上 → 不轉移、segment 留原處（emit committed）。
        若目標 lane 已被同範圍 segment 占用 → 不轉移（保守不破壞既有資料）。
        """
        source_lane = self.sender()
        if not isinstance(source_lane, StageLaneWidget):
            self.segment_committed.emit()
            return

        target_lane = None
        for lane in self.lanes.values():
            if lane is source_lane:
                continue
            local = lane.mapFromGlobal(release_global_pos)
            if 0 <= local.x() < lane.width() and 0 <= local.y() < lane.height():
                target_lane = lane
                break
        if target_lane is None:
            # release 點不在任何別 lane → 維持原 lane 但 emit committed（位置可能改了）
            self.segment_committed.emit()
            return

        # 檢查目標 lane 是否與 seg 範圍衝突
        for s in target_lane._segments():
            if not (seg.end < s.start or seg.start > s.end):
                # 與既有 segment 重疊 → 拒絕轉移、留在原 lane
                self.segment_committed.emit()
                return

        # 執行轉移
        if seg in source_lane._segments():
            source_lane._segments().remove(seg)
        target_lane._segments().append(seg)
        target_lane._segments().sort(key=lambda s: s.start)
        # 重繪兩條 lane
        source_lane.update()
        target_lane.update()
        # 清掉 source 的選取、設定 target 的選取
        source_lane.select_segment(None)
        target_lane.select_segment(seg)
        # 對外觸發
        self.segment_committed.emit()
        self.segment_selected.emit(seg)

    def set_cursor(self, idx: int | None):
        for lane in self.lanes.values():
            lane.set_cursor(idx)

    def set_character_colors(self, mapping: dict[str, str]) -> None:
        for lane in self.lanes.values():
            lane.set_character_colors(mapping)

    def refresh(self):
        for lane in self.lanes.values():
            lane.refresh()

    def global_rect_of_segment(self, seg: StageSegment):
        """回傳 seg 在螢幕全域座標的 QRect；找不到回 None。Phase 4 給 SegmentEditor 浮動定位用。"""
        from PyQt6.QtCore import QRect, QPoint
        for lane in self.lanes.values():
            if seg in lane._segments():
                top, bottom = shared.idx_range_to_rect_y(seg.start, seg.end)
                top_left_global = lane.mapToGlobal(QPoint(0, top))
                return QRect(top_left_global, QPoint(top_left_global.x() + lane.width(),
                                                      top_left_global.y() + (bottom - top)))
        return None


class StageHeader(QWidget):
    """三 lane 上方的標籤列。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        for label in ("左", "中", "右"):
            l = QLabel(label)
            l.setFixedWidth(shared.LANE_WIDTH)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet("color:#9AA0A6; background:#252526; padding:6px 0; font-weight:bold;")
            layout.addWidget(l)
        layout.addStretch(1)
