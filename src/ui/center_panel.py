"""Phase 2：中央面板重構。

結構（垂直 QSplitter）：
  ├─ PreviewWidget（上，既有元件）
  └─ Bottom（垂直 QSplitter）
      ├─ Workspace（水平 QSplitter 包在 QScrollArea）
      │    ├─ DialogueColumn   左，拉伸
      │    ├─ StagePanel       中，固定 3*LANE_WIDTH
      │    └─ EffectTimelineWidget 右，固定 N*LANE_WIDTH
      └─ SegmentEditor（底，固定 ~160px）

MainWindow 依賴的公開介面（保持不變）：
- 屬性 preview / spin_dlg_font / spin_name_font / spin_opacity / btn_refresh_preview
- signal project_changed / empty_state_import_text / empty_state_add_scene
- method set_project / set_current_scene / add_dialogues_to_current_scene /
  reload_preview / get_selected_dialogue_index / cleanup / refresh
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PushButton

from src.core.models import Dialogue, Project, Scene
from src.ui import _timeline_shared as shared
from src.ui.dialogue_list import DialogueColumn
from src.ui.effect_timeline import EffectTimelineHeader, EffectTimelineWidget
from src.ui.empty_state import EmptyStateWidget
from src.ui.preview_widget import PreviewWidget
from src.ui.segment_editor import SegmentEditor
from src.ui.stage_panel import StageHeader, StagePanel

if TYPE_CHECKING:
    pass


class _Column(QWidget):
    """header + content 縱向組合，用於三域的每一欄。header 隨欄寬移動。"""

    def __init__(self, header: QWidget, content: QWidget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(content, 1)


class CenterPanel(QWidget):
    """三域分離的中央面板。"""

    project_changed = pyqtSignal()
    empty_state_import_text = pyqtSignal()
    empty_state_add_scene = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._project: Project | None = None
        self._current_scene_index: int = -1
        self._building: bool = False
        self._setup_ui()

    # ── UI 組裝 ─────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        self._main_splitter = QSplitter(Qt.Orientation.Vertical)
        self._main_splitter.setHandleWidth(6)

        # 上：PreviewWidget + toolbar
        self._main_splitter.addWidget(self._build_preview_container())

        # 下：Workspace（三域）+ SegmentEditor
        self._main_splitter.addWidget(self._build_editing_container())

        self._main_splitter.setStretchFactor(0, 1)
        self._main_splitter.setStretchFactor(1, 1)
        self._main_splitter.setSizes([400, 400])

        root.addWidget(self._main_splitter)

        # preview bridge：dialogue_advanced 同步游標
        self.preview.bridge.dialogue_advanced.connect(self._on_preview_dialogue_advanced)

    def _build_preview_container(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(2, 2, 2, 2)
        toolbar.setSpacing(10)
        self.btn_refresh_preview = PushButton("重新整理")
        toolbar.addWidget(self.btn_refresh_preview)
        toolbar.addSpacing(14)
        toolbar.addWidget(QLabel("對話字體:"))
        self.spin_dlg_font = QSpinBox()
        self.spin_dlg_font.setRange(14, 28)
        self.spin_dlg_font.setValue(18)
        self.spin_dlg_font.setSuffix(" px")
        self.spin_dlg_font.setMinimumWidth(110)
        toolbar.addWidget(self.spin_dlg_font)
        toolbar.addSpacing(10)
        toolbar.addWidget(QLabel("名稱字體:"))
        self.spin_name_font = QSpinBox()
        self.spin_name_font.setRange(14, 28)
        self.spin_name_font.setValue(16)
        self.spin_name_font.setSuffix(" px")
        self.spin_name_font.setMinimumWidth(110)
        toolbar.addWidget(self.spin_name_font)
        toolbar.addSpacing(10)
        toolbar.addWidget(QLabel("透明度:"))
        self.spin_opacity = QDoubleSpinBox()
        self.spin_opacity.setRange(0.5, 1.0)
        self.spin_opacity.setSingleStep(0.05)
        self.spin_opacity.setDecimals(2)
        self.spin_opacity.setValue(0.85)
        self.spin_opacity.setMinimumWidth(100)
        toolbar.addWidget(self.spin_opacity)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # EmptyState / Preview stacked
        self._preview_stack = QStackedWidget()
        self._empty_state = EmptyStateWidget()
        self._empty_state.import_text_clicked.connect(self.empty_state_import_text)
        self._empty_state.add_scene_clicked.connect(self.empty_state_add_scene)

        self.preview = PreviewWidget()

        self._preview_stack.addWidget(self._empty_state)  # index 0
        self._preview_stack.addWidget(self.preview)        # index 1
        layout.addWidget(self._preview_stack, 1)
        return container

    def _build_editing_container(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Phase 4：SegmentEditor 改為浮動視窗（不再吃掉工作區的垂直空間）
        self._workspace_scroll = QScrollArea()
        self._workspace_scroll.setWidgetResizable(True)
        self._workspace_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._workspace_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._workspace_placeholder_html = QLabel("載入中…")
        self._workspace_placeholder_html.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._workspace_scroll.setWidget(self._workspace_placeholder_html)

        layout.addWidget(self._workspace_scroll)

        # SegmentEditor 改為 self 的子 widget，預設 hidden；選 segment 時 show + raise + move
        self.segment_editor = SegmentEditor(parent=self)
        self.segment_editor.hide()
        self.segment_editor.setFixedWidth(280)
        self.segment_editor.setMinimumHeight(180)
        self.segment_editor.segment_changed.connect(self._on_segment_edited)
        self.segment_editor.closed.connect(self._on_segment_editor_closed)

        # 三域 widget 屬性：用 empty scene 預先建立，set_project 再綁真資料
        self._empty_scene = Scene(id="__empty__", dialogues=[])
        self.dialogue_list = DialogueColumn(self._empty_scene)
        self.stage_panel = StagePanel(self._empty_scene)
        self.effect_timeline = EffectTimelineWidget(self._empty_scene)

        self._rebuild_workspace()
        return container

    def _rebuild_workspace(self) -> None:
        """(重新)建立工作區三域 widget layout。Scene 切換時呼叫。"""
        self._building = True
        try:
            scene = self._get_current_scene() or self._empty_scene

            # 重建三域 widget（新 Scene 綁定）
            # 斷開舊 signal 以防 duplicate
            self._disconnect_workspace_signals()

            self.dialogue_list = DialogueColumn(scene)
            self.stage_panel = StagePanel(scene)
            self.effect_timeline = EffectTimelineWidget(scene)

            # 套用角色顏色
            color_map = self._character_color_map()
            self.dialogue_list.set_character_colors(color_map)
            self.stage_panel.set_character_colors(color_map)

            # header 們
            dialogue_header = QLabel("對話")
            dialogue_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dialogue_header.setStyleSheet(
                "color:#E8E8E8; background:#252526; padding:6px 0; font-weight:bold;"
            )
            stage_header = StageHeader()
            effect_header = EffectTimelineHeader(scene, on_add_track=self._on_add_effect_track)
            self._effect_header = effect_header
            # Phase 4 lane mgmt：rename / delete 軌道
            effect_header.track_rename_requested.connect(self._on_rename_effect_track)
            effect_header.track_delete_requested.connect(self._on_delete_effect_track)
            # Phase 4.2：軌道顏色覆寫
            effect_header.track_color_changed.connect(self._on_effect_track_color_changed)

            col_dialogue = _Column(dialogue_header, self.dialogue_list)
            col_stage = _Column(stage_header, self.stage_panel)
            col_effect = _Column(effect_header, self.effect_timeline)

            col_stage.setFixedWidth(shared.LANE_WIDTH * 3 + 6)
            effect_lanes = max(1, len(scene.effect_tracks))
            col_effect.setMinimumWidth(shared.LANE_WIDTH * effect_lanes + 48)

            workspace = QWidget()
            workspace_layout = QHBoxLayout(workspace)
            workspace_layout.setContentsMargins(0, 0, 0, 0)
            workspace_layout.setSpacing(2)
            workspace_layout.addWidget(col_dialogue, 1)
            workspace_layout.addWidget(col_stage, 0)
            workspace_layout.addWidget(col_effect, 0)

            self._workspace_scroll.setWidget(workspace)
            self._workspace_root = workspace

            self._connect_workspace_signals()

            # 如果 segment editor 有帶 project，更新它的候選清單
            if self._project:
                self.segment_editor.set_project(self._project)
            # 切 scene 清掉 editor 並隱藏浮動視窗
            self.segment_editor.set_segment(None)
            self.segment_editor.hide()
        finally:
            self._building = False

    def _connect_workspace_signals(self) -> None:
        self.dialogue_list.dialogue_moved.connect(self._on_dialogue_moved)
        self.dialogue_list.cursor_changed.connect(self._on_cursor_from_widget)
        self.dialogue_list.selection_changed.connect(self._on_cursor_from_widget)

        # 拖端點 mouseMove 期間 segment_changed 連續觸發；不在此重載預覽，
        # 等到 segment_committed (mouseRelease / Delete / 雙擊新增) 才 reload。
        self.stage_panel.cursor_changed.connect(self._on_cursor_from_widget)
        self.stage_panel.segment_committed.connect(self._on_segment_committed)
        self.stage_panel.segment_selected.connect(self._on_stage_segment_selected)

        self.effect_timeline.cursor_changed.connect(self._on_cursor_from_widget)
        self.effect_timeline.segment_committed.connect(self._on_segment_committed)
        self.effect_timeline.segment_selected.connect(self._on_effect_segment_selected)
        self._signals_connected = True

    def _disconnect_workspace_signals(self) -> None:
        if not getattr(self, "_signals_connected", False):
            return
        for obj in (getattr(self, "dialogue_list", None),
                    getattr(self, "stage_panel", None),
                    getattr(self, "effect_timeline", None)):
            if obj is None:
                continue
            try:
                obj.disconnect()
            except (TypeError, RuntimeError):
                pass
        self._signals_connected = False

    # ── Project / Scene 綁定 ───────────────────────────────

    def _get_current_scene(self) -> Scene | None:
        if not self._project or not self._project.scenes:
            return None
        if not (0 <= self._current_scene_index < len(self._project.scenes)):
            return None
        return self._project.scenes[self._current_scene_index]

    def _character_color_map(self) -> dict[str, str]:
        if not self._project:
            return {}
        return {c.name: c.name_color for c in self._project.characters}

    def _update_empty_state(self) -> None:
        has_scenes = bool(self._project and self._project.scenes)
        self._preview_stack.setCurrentIndex(1 if has_scenes else 0)

    def set_project(self, project: Project) -> None:
        self._project = project
        self._current_scene_index = 0 if project.scenes else -1
        self.segment_editor.set_project(project)
        self._rebuild_workspace()
        self._update_empty_state()

    def set_current_scene(self, index: int) -> None:
        self._current_scene_index = index
        self._rebuild_workspace()
        self._update_empty_state()

    def reload_preview(self, project: Project) -> None:
        self.preview.reload_preview(project)

    def cleanup(self) -> None:
        self.preview.cleanup()

    def add_dialogues_to_current_scene(
        self, dialogues: list[Dialogue], insert_after: int | None = None
    ) -> None:
        if not self._project or not self._project.scenes:
            return
        scene = self._get_current_scene()
        if scene is None:
            return
        if insert_after is None or not (0 <= insert_after < len(scene.dialogues)):
            # append
            for d in dialogues:
                scene.insert_dialogue(len(scene.dialogues), d)
        else:
            for i, d in enumerate(dialogues):
                scene.insert_dialogue(insert_after + 1 + i, d)
        self.refresh()
        self._update_empty_state()
        self.project_changed.emit()

    def get_selected_dialogue_index(self) -> int | None:
        # 對話卡片列目前無「選取」概念 → 回傳 None。
        # Phase 3/5 加 inline 編輯時再把 _selected_idx 暴露出來。
        return None

    def refresh(self) -> None:
        """外部觸發重新繪製三域 widget（資料未變結構、只需重繪）。"""
        # 更新角色顏色映射（角色可能被重命名 / 重新著色）
        color_map = self._character_color_map()
        self.dialogue_list.set_character_colors(color_map)
        self.stage_panel.set_character_colors(color_map)
        self.dialogue_list.refresh()
        self.stage_panel.refresh()
        self.effect_timeline.refresh()
        # segment editor 的候選也可能變（角色 / 服裝被編輯）
        if self._project:
            self.segment_editor.set_project(self._project)

    # ── Signal handlers ────────────────────────────────────

    def _on_dialogue_moved(self, src: int, dst: int) -> None:
        scene = self._get_current_scene()
        if scene is None:
            return
        scene.move_dialogue(src, dst)
        self.refresh()
        self.project_changed.emit()

    def _on_cursor_from_widget(self, idx: int) -> None:
        # 三 widget 共享游標：轉發到另外兩個
        if self._building:
            return
        sender = self.sender()
        for w in (self.dialogue_list, self.stage_panel, self.effect_timeline):
            if w is not sender:
                w.set_cursor(idx)
        # 預覽同步（Preview 已載入時）
        if self._preview_stack.currentIndex() == 1 and self._current_scene_index >= 0:
            self.preview.jump_to_dialogue(self._current_scene_index, idx)

    def _on_stage_segment_selected(self, seg) -> None:
        # stage 選中 → 清掉 effect 的選取
        for lane in self.effect_timeline.lanes.values():
            lane.select_segment(None)
        self._show_segment_editor_for(seg, self.stage_panel)

    def _on_effect_segment_selected(self, seg) -> None:
        for lane in self.stage_panel.lanes.values():
            lane.select_segment(None)
        self._show_segment_editor_for(seg, self.effect_timeline)

    def _show_segment_editor_for(self, seg, source_widget) -> None:
        """Phase 4：浮動 SegmentEditor 定位在 segment 旁；seg=None 則隱藏。"""
        if seg is None:
            self.segment_editor.hide()
            self.segment_editor.set_segment(None)
            return

        self.segment_editor.set_segment(seg)
        # 取 segment 全域座標 → 轉成 self 的 local 座標
        seg_global_rect = source_widget.global_rect_of_segment(seg)
        if seg_global_rect is None:
            return
        editor_w = self.segment_editor.width() or 280
        editor_h = max(self.segment_editor.sizeHint().height(), 180)
        # 預設放右側
        target_global_x = seg_global_rect.right() + 8
        # 若超出 self 右緣 → 改放左側
        self_global_right = self.mapToGlobal(self.rect().topRight()).x()
        if target_global_x + editor_w > self_global_right:
            target_global_x = max(0, seg_global_rect.left() - editor_w - 8)
        target_global_y = max(0, seg_global_rect.top())
        # 若超出 self 下緣 → 上移
        self_global_bottom = self.mapToGlobal(self.rect().bottomLeft()).y()
        if target_global_y + editor_h > self_global_bottom:
            target_global_y = max(0, self_global_bottom - editor_h - 8)
        local = self.mapFromGlobal(QPoint(target_global_x, target_global_y))
        self.segment_editor.move(local)
        self.segment_editor.raise_()
        self.segment_editor.show()
        self.segment_editor.setFocus()  # 收 ESC

    def _on_segment_editor_closed(self) -> None:
        """X 鈕或 ESC 觸發；關閉浮動視窗並清除 segment 選取。"""
        self.segment_editor.hide()
        self.segment_editor.set_segment(None)
        for lane in self.stage_panel.lanes.values():
            lane.select_segment(None)
        for lane in self.effect_timeline.lanes.values():
            lane.select_segment(None)

    def _on_segment_committed(self) -> None:
        """commit 邊界（拖完 / 雙擊新增 / Delete / 加軌道）：reload 預覽 + 標 dirty。

        live drag 中的 segment_changed 不走這條，避免每 mouseMove 重載 webengine。
        widget 自己已在 mouseMove 內 self.update() 完成重繪。
        """
        if self._building:
            return
        if self._project and self._current_scene_index >= 0:
            self.preview.reload_preview(self._project)
        self.project_changed.emit()

    def _on_segment_edited(self) -> None:
        """來自 SegmentEditor payload 變更：是單次動作（非 drag loop）。

        StageSegment 的 character/costume/sprite 變了 → 對應 lane 需要重畫 chip；
        EffectSegment 的 type/params 變了 → effect lane 重畫。
        然後 reload 預覽 + 標 dirty。
        """
        if self._building:
            return
        self.stage_panel.refresh()
        self.effect_timeline.refresh()
        if self._project and self._current_scene_index >= 0:
            self.preview.reload_preview(self._project)
        self.project_changed.emit()

    def _on_add_effect_track(self, name: str) -> None:
        scene = self._get_current_scene()
        if scene is None:
            return
        # 若同名已存在，加流水號
        existing = {t.name for t in scene.effect_tracks}
        final_name = name
        n = 2
        while final_name in existing:
            final_name = f"{name}_{n}"
            n += 1
        self.effect_timeline.add_track(final_name)
        # header 同步新標籤
        if hasattr(self, "_effect_header"):
            self._effect_header.append_track(final_name)
        # 寬度重算
        effect_lanes = max(1, len(scene.effect_tracks))
        # col_effect 物件沒存 ref，但可從 _workspace_root 抓。為簡單起見，
        # 讓 rebuild_workspace 完全重建。
        self._rebuild_workspace()
        self.project_changed.emit()

    def _on_rename_effect_track(self, old_name: str, new_name: str) -> None:
        """Phase 4 lane mgmt：rename 軌道。EffectTimelineHeader 已先彈過 input dialog。"""
        scene = self._get_current_scene()
        if scene is None:
            return
        if any(t.name == new_name for t in scene.effect_tracks):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "重新命名失敗",
                                f"已有同名軌道「{new_name}」，請換一個名稱。")
            return
        if not self.effect_timeline.rename_track(old_name, new_name):
            return
        if hasattr(self, "_effect_header"):
            self._effect_header.update_track_name(old_name, new_name)
        self.project_changed.emit()

    def _on_delete_effect_track(self, name: str) -> None:
        """Phase 4 lane mgmt：刪除整條 EffectTrack。confirm 已由 header 彈過。"""
        scene = self._get_current_scene()
        if scene is None:
            return
        if not self.effect_timeline.remove_track(name):
            return
        if hasattr(self, "_effect_header"):
            self._effect_header.remove_track_label(name)
        # 寬度可能縮，rebuild 簡單一致
        self._rebuild_workspace()
        self.project_changed.emit()

    def _on_effect_track_color_changed(self, name: str, hex_color: str) -> None:
        """Phase 4.2：Header 用 QColorDialog 選好 color → 寫入 track 並同步 label 左豎條。

        空字串 hex 代表清除 override。segment_committed 由 set_track_color 內部 emit。
        """
        scene = self._get_current_scene()
        if scene is None:
            return
        normalized = hex_color or None
        if not self.effect_timeline.set_track_color(name, normalized):
            return
        if hasattr(self, "_effect_header"):
            self._effect_header.update_track_color(name, normalized)
        self.project_changed.emit()

    def _on_preview_dialogue_advanced(self, scene_idx: int, dlg_idx: int) -> None:
        # Preview 自動播放 → 同步游標到對話 / 舞台 / 特效
        if scene_idx != self._current_scene_index:
            return
        self.dialogue_list.set_cursor(dlg_idx)
        self.stage_panel.set_cursor(dlg_idx)
        self.effect_timeline.set_cursor(dlg_idx)
