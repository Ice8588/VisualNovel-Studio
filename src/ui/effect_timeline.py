"""Domain 3：特效 Timeline。多條命名軌道。

設計決策（POC 2026-04-19 改）：lane 內 segment **互斥不重疊**（同 stage_panel）。
若使用者要疊加多個特效，請新增多條軌道。

Phase 2 移植自 experimental/timeline_poc/effect_timeline.py，import 改為正式資料模型。
"""

from __future__ import annotations
from dataclasses import dataclass

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QColorDialog, QHBoxLayout, QInputDialog, QLabel, QMenu, QMessageBox,
    QPushButton, QWidget,
)

from src.core.models import EffectSegment, EffectTrack, Scene
from src.ui import _timeline_shared as shared
from src.ui.icons import design_icon


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
        self._mouse_inside: bool = False  # task.md #6 hover + icon
        self.setMouseTracking(True)
        self.setMinimumWidth(shared.LANE_WIDTH)
        self.setFixedWidth(shared.LANE_WIDTH)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # 才能收 keyPress (Delete)
        self._update_height()

    def _update_height(self):
        self.setMinimumHeight(shared.idx_to_y(len(self.scene.dialogues)))

    def _font_size_px(self) -> int:
        sz = self.font().pixelSize()
        if sz <= 0:
            pt = self.font().pointSize()
            sz = int(pt * 1.33) if pt > 0 else 20
        return max(18, min(28, sz))

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

        # task.md #6 cell hover：滑鼠在 lane 內 + 該列無 segment 時，先畫高亮方塊
        if (
            self._mouse_inside
            and self._cursor_idx is not None
            and self._drag is None
            and not self._row_has_segment(self._cursor_idx)
        ):
            self._paint_hover_cell(p, self._cursor_idx)

        p.setPen(QPen(shared.GRID_LINE, 1))
        for idx in range(len(self.scene.dialogues) + 1):
            y = shared.idx_to_y(idx)
            p.drawLine(0, y, self.width(), y)

        for seg in self.track.segments:
            self._paint_segment(p, seg)

        # task.md #6 hover「+」icon
        if (
            self._mouse_inside
            and self._cursor_idx is not None
            and self._drag is None
            and not self._row_has_segment(self._cursor_idx)
        ):
            self._paint_hover_plus(p, self._cursor_idx)

        if self._cursor_idx is not None:
            y = shared.idx_to_y(self._cursor_idx) + shared.ROW_HEIGHT // 2
            p.setPen(QPen(shared.CURSOR_LINE, 1, Qt.PenStyle.DashLine))
            p.drawLine(0, y, self.width(), y)

        p.end()

    def _row_has_segment(self, idx: int) -> bool:
        for s in self.track.segments:
            if s.start <= idx <= s.end:
                return True
        return False

    def _paint_hover_cell(self, p: QPainter, idx: int) -> None:
        from src.ui import palette as _pal
        bg = shared.BG_DARK
        fg = _pal.contrast_text(bg)
        cell = QColor(fg)
        cell.setAlpha(28)
        top = shared.idx_to_y(idx)
        rect = QRect(4, top + 2, self.width() - 8, shared.ROW_HEIGHT - 4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(cell)
        p.drawRoundedRect(rect, 5, 5)

    def _plus_hit_rect(self, idx: int) -> QRect:
        cx = self.width() // 2
        cy = shared.idx_to_y(idx) + shared.ROW_HEIGHT // 2
        radius = 13
        return QRect(cx - radius, cy - radius, radius * 2, radius * 2)

    def _paint_hover_plus(self, p: QPainter, idx: int) -> None:
        from src.ui import palette as _pal
        cx = self.width() // 2
        cy = shared.idx_to_y(idx) + shared.ROW_HEIGHT // 2
        radius = 11
        bg = shared.BG_DARK
        fg = _pal.contrast_text(bg)
        p.setPen(Qt.PenStyle.NoPen)
        bg_disk = QColor(fg)
        bg_disk.setAlpha(46)
        p.setBrush(bg_disk)
        p.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
        pen = QPen(fg, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        arm = 5
        p.drawLine(cx - arm, cy, cx + arm, cy)
        p.drawLine(cx, cy - arm, cx, cy + arm)

    def _seg_rect(self, seg: EffectSegment) -> QRect:
        top, bottom = shared.idx_range_to_rect_y(seg.start, seg.end)
        return QRect(6, top + 3, self.width() - 12, bottom - top - 6)

    def _paint_segment(self, p: QPainter, seg: EffectSegment):
        rect = self._seg_rect(seg)
        # Phase 4.2：track.color 優先，否則 fallback 到 effect_type 預設色
        base = QColor(self.track.color) if self.track.color else _effect_color(seg.effect_type)
        if not base.isValid():
            base = _effect_color(seg.effect_type)
        p.setBrush(base)
        if seg is self._selected:
            p.setPen(QPen(shared.CURSOR_LINE, 2))
        else:
            p.setPen(QPen(base.darker(140), 1))
        p.drawRoundedRect(rect, 6, 6)

        # 文字色依 base（effect_type 色）算對比；字體 ≥ 18px（task #2）
        from src.ui import palette as _pal
        fg = _pal.contrast_text(base)
        p.setPen(fg)
        f = shared.ui_sans_font(self._font_size_px(), bold=True, base=self.font())
        p.setFont(f)
        metrics = QFontMetrics(p.font())
        label = metrics.elidedText(seg.effect_type, Qt.TextElideMode.ElideRight, rect.width() - 12)
        p.drawText(rect.adjusted(6, 4, -6, -4), Qt.AlignmentFlag.AlignCenter, label)

        grip_color = QColor(fg)
        grip_color.setAlpha(130)
        p.setPen(QPen(grip_color, 2))
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

    def enterEvent(self, ev) -> None:
        self._mouse_inside = True
        self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev) -> None:
        self._mouse_inside = False
        self.update()
        super().leaveEvent(ev)

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()  # 收到 keyPress (Delete)
        # task.md #6：點擊「+」icon → 新增 segment
        if (
            self._mouse_inside
            and self._cursor_idx is not None
            and not self._row_has_segment(self._cursor_idx)
            and self._plus_hit_rect(self._cursor_idx).contains(ev.pos())
        ):
            self._create_effect_at_y(ev.pos().y())
            return
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
        self._create_effect_at_y(ev.pos().y())

    def _create_effect_at_y(self, y: int) -> None:
        """task.md #6：單擊「+」、雙擊空白共用的新增邏輯。"""
        if not self.scene.dialogues:
            return
        max_idx = len(self.scene.dialogues) - 1
        cur = shared.y_to_idx(y, max_idx)
        end = min(cur + 1, max_idx)
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
            else:
                self.update()  # 重畫 hover + icon
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

    def set_track_color(self, name: str, color: str | None) -> bool:
        """Phase 4.2：覆寫軌道顏色（hex 字串如 `"#RRGGBB"`；傳 None / 空字串 = 清除 override）。

        成功 True 時 emit segment_committed（讓 CenterPanel 重載預覽 / 標 dirty）。
        軌道不存在 → False。
        """
        track = next((t for t in self.scene.effect_tracks if t.name == name), None)
        if track is None:
            return False
        normalized = color if color else None
        if track.color == normalized:
            return False  # no-op
        track.color = normalized
        lane = self.lanes.get(name)
        if lane is not None:
            lane.update()
        self.segment_committed.emit()
        return True

    def rename_track(self, old_name: str, new_name: str) -> bool:
        """Phase 4：改 EffectTrack.name；目前 lane 字典 key 同步。

        回 False：old_name 不存在 / new_name 已被佔用 / 名稱無變更（no-op）。
        成功 True 時 emit segment_committed（讓 CenterPanel 重載預覽 / 標 dirty）。
        """
        if not new_name or new_name == old_name:
            return False
        if new_name in self.lanes:
            return False
        track = next((t for t in self.scene.effect_tracks if t.name == old_name), None)
        if track is None:
            return False
        track.name = new_name
        # rebuild lanes dict keep order
        new_lanes: dict[str, EffectLaneWidget] = {}
        for k, v in self.lanes.items():
            new_lanes[new_name if k == old_name else k] = v
        self.lanes = new_lanes
        self.segment_committed.emit()
        return True

    def remove_track(self, name: str) -> bool:
        """Phase 4：刪除整條 EffectTrack（含 segments）+ 拆 lane widget。"""
        track = next((t for t in self.scene.effect_tracks if t.name == name), None)
        if track is None:
            return False
        self.scene.effect_tracks.remove(track)
        lane = self.lanes.pop(name)
        # 銷毀排程到 event loop，先斷開轉發訊號，避免等待期間殘留事件打回本 widget
        lane.cursor_changed.disconnect()
        lane.segment_changed.disconnect()
        lane.segment_committed.disconnect()
        lane.segment_selected.disconnect()
        self._layout.removeWidget(lane)
        lane.setParent(None)
        lane.deleteLater()
        self.segment_committed.emit()
        return True

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

    def refresh_theme(self) -> None:
        for lane in self.lanes.values():
            lane.update()

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


class _TrackLabel(QLabel):
    """Phase 4：軌道名稱 label，右鍵彈出 rename / delete / 設定顏色選單。

    Phase 4.2：左側 4px 豎條反映 `track.color`（None 時不畫）。
    """
    rename_requested = pyqtSignal(str)  # current name
    delete_requested = pyqtSignal(str)  # current name
    color_requested = pyqtSignal(str)   # current name（Phase 4.2）

    def __init__(self, name: str, parent=None):
        super().__init__(name, parent)
        self.track_name = name
        self._accent: str | None = None
        self.setFixedWidth(shared.LANE_WIDTH)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_stylesheet()
        self.setToolTip("右鍵：重新命名 / 刪除 / 設定顏色")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_track_name(self, new_name: str) -> None:
        self.track_name = new_name
        self.setText(new_name)

    def set_accent_color(self, color: str | None) -> None:
        """Phase 4.2：同步 track.color → label 左側 4px 豎條。None → 清除。"""
        self._accent = color
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        accent = self._accent
        if accent:
            border = f"border-left: 4px solid {accent};"
            padding = "padding: 6px 0 6px 0;"  # 4px border 已吃左側
        else:
            border = ""
            padding = "padding: 6px 0;"
        bg = shared.BG_PANEL.name()
        fg = shared.TEXT_MUTED.name()
        self.setStyleSheet(
            f"color:{fg}; background:{bg}; {padding} {border} font-weight:bold;"
        )

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.RightButton:
            menu = QMenu(self)
            menu.addAction(design_icon("edit"), "重新命名…",
                           lambda: self.rename_requested.emit(self.track_name))
            menu.addAction(design_icon("brush"), "設定顏色…",
                           lambda: self.color_requested.emit(self.track_name))
            menu.addAction(design_icon("delete"), "刪除軌道…",
                           lambda: self.delete_requested.emit(self.track_name))
            menu.exec(ev.globalPosition().toPoint())
            return
        super().mousePressEvent(ev)


class EffectTimelineHeader(QWidget):
    """軌道名稱列。Phase 4 新增：右鍵 rename / delete / 設定顏色。"""

    track_rename_requested = pyqtSignal(str, str)  # (old_name, new_name)
    track_delete_requested = pyqtSignal(str)       # name
    track_color_changed = pyqtSignal(str, str)     # (name, hex) — 空 hex 代表清除（Phase 4.2）

    def __init__(self, scene: Scene, on_add_track, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._on_add_track = on_add_track
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._labels: dict[str, _TrackLabel] = {}
        for track in scene.effect_tracks:
            self._layout.addWidget(self._make_label(track.name, track.color))
        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(32, 28)
        self._add_btn.clicked.connect(self._handle_add)
        self._layout.addWidget(self._add_btn)
        self._layout.addStretch(1)
        self._apply_add_btn_style()

    def _apply_add_btn_style(self) -> None:
        if shared.is_light():
            bg, fg = "#E8E8EA", "#1E1E1E"
        else:
            bg, fg = "#3D3D40", "#E8E8E8"
        self._add_btn.setStyleSheet(f"background:{bg}; color:{fg}; border:none; border-radius:4px;")

    def refresh_theme(self) -> None:
        for lbl in self._labels.values():
            lbl._apply_stylesheet()
        self._apply_add_btn_style()

    def _make_label(self, name: str, color: str | None = None) -> _TrackLabel:
        lbl = _TrackLabel(name, self)
        lbl.set_accent_color(color)
        lbl.rename_requested.connect(self._on_rename_requested)
        lbl.delete_requested.connect(self._on_delete_requested)
        lbl.color_requested.connect(self._on_color_requested)
        self._labels[name] = lbl
        return lbl

    def append_track(self, name: str):
        idx = self._layout.indexOf(self._add_btn)
        track = next((t for t in self.scene.effect_tracks if t.name == name), None)
        self._layout.insertWidget(idx, self._make_label(name, track.color if track else None))

    def update_track_name(self, old_name: str, new_name: str) -> None:
        """軌道改名後同步 label."""
        if old_name not in self._labels:
            return
        lbl = self._labels.pop(old_name)
        lbl.set_track_name(new_name)
        self._labels[new_name] = lbl

    def update_track_color(self, name: str, color: str | None) -> None:
        """Phase 4.2：軌道 color 變更後同步 label 左側豎條。"""
        lbl = self._labels.get(name)
        if lbl is not None:
            lbl.set_accent_color(color)

    def remove_track_label(self, name: str) -> None:
        """軌道刪除後拆 label."""
        lbl = self._labels.pop(name, None)
        if lbl is not None:
            self._layout.removeWidget(lbl)
            lbl.setParent(None)
            lbl.deleteLater()

    def _handle_add(self):
        n = len(self.scene.effect_tracks) + 1
        self._on_add_track(f"軌道{n}")

    def _on_rename_requested(self, name: str) -> None:
        new_name, ok = QInputDialog.getText(
            self, "重新命名特效軌道", f"舊名稱：「{name}」\n\n新名稱：", text=name,
        )
        new_name = (new_name or "").strip()
        if not ok or not new_name or new_name == name:
            return
        self.track_rename_requested.emit(name, new_name)

    def _on_color_requested(self, name: str) -> None:
        """Phase 4.2：右鍵「設定顏色…」→ QColorDialog。選好 emit track_color_changed。"""
        track = next((t for t in self.scene.effect_tracks if t.name == name), None)
        if track is None:
            return
        initial = QColor(track.color) if track.color else QColor("#5F6368")
        chosen = QColorDialog.getColor(initial, self, "選擇軌道顏色")
        if chosen.isValid():
            self.track_color_changed.emit(name, chosen.name())  # "#RRGGBB"

    def _on_delete_requested(self, name: str) -> None:
        # 計算要連帶刪掉幾個 segment 顯示在訊息上
        track = next((t for t in self.scene.effect_tracks if t.name == name), None)
        n_seg = len(track.segments) if track else 0
        msg = f"確定刪除特效軌道「{name}」？"
        if n_seg:
            msg += f"\n\n軌道內 {n_seg} 個 segment 會一併刪除。"
        result = QMessageBox.question(
            self, "刪除特效軌道", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self.track_delete_requested.emit(name)
