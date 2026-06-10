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

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.color_sliders_panel import ColorSlidersPanel
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
    # 對話框背景 / 文字色變更（live；main_window 寫進 game_settings 並 markDirty 但不 reload）
    dialogue_box_color_changed = pyqtSignal(str)
    dialogue_text_color_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._project: Project | None = None
        self._current_scene_index: int = -1
        self._building: bool = False
        # Phase 5.1 焦點保護：追蹤 preview 上次停留位置，segment commit 後 reload 完跳回
        self._last_preview_pos: tuple[int, int] = (0, 0)
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
        toolbar.setContentsMargins(14, 4, 4, 4)
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
        self.spin_opacity.setRange(0.0, 1.0)  # 0% ~ 100%
        self.spin_opacity.setSingleStep(0.05)
        self.spin_opacity.setDecimals(2)
        self.spin_opacity.setValue(0.85)
        self.spin_opacity.setMinimumWidth(100)
        toolbar.addWidget(self.spin_opacity)
        toolbar.addSpacing(10)
        # 對話框背景色：標題 + 色塊按鈕 → 浮動色板（panel 左緣對齊「背景顏色」標題左緣）
        self._lbl_bg_color = QLabel("背景顏色:")
        toolbar.addWidget(self._lbl_bg_color)
        self.btn_dlg_color = QPushButton()
        self.btn_dlg_color.setFixedSize(28, 24)
        self.btn_dlg_color.setToolTip("點擊展開色板（HSL 滑桿）— 對話框背景")
        self._dlg_color_hex = "#141428"
        self._apply_dlg_color_swatch()
        self.btn_dlg_color.clicked.connect(
            lambda: self._toggle_color_panel(self.color_panel, self._lbl_bg_color)
        )
        toolbar.addWidget(self.btn_dlg_color)

        # 兩個色色組緊鄰：標題視覺靠近，避免大塊空白。
        # 同時開兩塊面板會重疊 → _toggle_color_panel 改為「打開一塊就關掉另一塊」（互斥）
        toolbar.addSpacing(16)

        # 對話框文字色：標題 + 色塊按鈕 → 另一塊浮動色板
        self._lbl_text_color = QLabel("文字顏色:")
        toolbar.addWidget(self._lbl_text_color)
        self.btn_text_color = QPushButton()
        self.btn_text_color.setFixedSize(28, 24)
        self.btn_text_color.setToolTip("點擊展開色板（HSL 滑桿）— 對話文字色")
        self._text_color_hex = "#EEEEEE"
        self._apply_text_color_swatch()
        self.btn_text_color.clicked.connect(
            lambda: self._toggle_color_panel(self.text_panel, self._lbl_text_color)
        )
        toolbar.addWidget(self.btn_text_color)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 兩塊浮動色板：parent = container，不入 layout 不擠預覽
        self.color_panel = ColorSlidersPanel(container)
        self.color_panel.set_color(self._dlg_color_hex)
        self.color_panel.color_changed.connect(self._on_color_panel_changed)
        self.color_panel.hide()

        self.text_panel = ColorSlidersPanel(container)
        self.text_panel.set_color(self._text_color_hex)
        self.text_panel.color_changed.connect(self._on_text_panel_changed)
        self.text_panel.hide()

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

    def _apply_dlg_color_swatch(self) -> None:
        self.btn_dlg_color.setStyleSheet(
            f"background-color:{self._dlg_color_hex}; border:1px solid #888; border-radius:3px;"
        )

    def _apply_text_color_swatch(self) -> None:
        self.btn_text_color.setStyleSheet(
            f"background-color:{self._text_color_hex}; border:1px solid #888; border-radius:3px;"
        )

    def set_dialogue_box_color(self, hex_color: str) -> None:
        """外部呼叫（main_window 從 game_settings 同步）。"""
        self._dlg_color_hex = hex_color
        self._apply_dlg_color_swatch()
        if hasattr(self, "color_panel"):
            self.color_panel.set_color(hex_color)

    def get_dialogue_box_color(self) -> str:
        return self._dlg_color_hex

    def set_dialogue_text_color(self, hex_color: str) -> None:
        self._text_color_hex = hex_color
        self._apply_text_color_swatch()
        if hasattr(self, "text_panel"):
            self.text_panel.set_color(hex_color)

    def get_dialogue_text_color(self) -> str:
        return self._text_color_hex

    def _toggle_color_panel(self, panel, anchor_label) -> None:
        """通用展開 / 收起浮動色板。panel 左緣對齊 anchor_label（標題）左緣，
        垂直放在 anchor 下方。toolbar 已預留標題間距 ≥ panel 寬度，
        兩塊面板同時展開仍不重疊；極端視窗才會被 clamp 邏輯避讓。
        """
        if panel.isVisible():
            panel.hide()
            return
        # 互斥：toolbar spacing 已縮短到 16px，兩塊面板不可能並排不重疊；
        # 統一邏輯為「永遠只開一塊」——打開一塊前先關掉另一塊。
        other = self.text_panel if panel is self.color_panel else self.color_panel
        if other.isVisible():
            other.hide()

        parent = panel.parent()
        anchor_bl = anchor_label.mapTo(parent, anchor_label.rect().bottomLeft())
        desired_x = anchor_bl.x()
        y = anchor_bl.y() + 8

        # clamp 到 parent 邊界
        desired_x = max(4, min(desired_x, parent.width() - panel.width() - 4))
        panel.move(desired_x, y)
        panel.show()
        panel.raise_()

    def _on_color_panel_changed(self, hex_color: str) -> None:
        """背景色板滑桿移動：更新色塊 + 廣播。main_window 接訊號做 live update（不 reload）。"""
        self._dlg_color_hex = hex_color
        self._apply_dlg_color_swatch()
        self.dialogue_box_color_changed.emit(hex_color)

    def _on_text_panel_changed(self, hex_color: str) -> None:
        """文字色板滑桿移動：更新色塊 + 廣播。"""
        self._text_color_hex = hex_color
        self._apply_text_color_swatch()
        self.dialogue_text_color_changed.emit(hex_color)

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
            if self._project:
                self.stage_panel.set_characters(self._project.characters)

            # header 們：對話列三欄（索引 / 角色 / 台詞），寬度跟 dialogue_list 一致
            dialogue_header = self._build_dialogue_header()
            self._dialogue_header = dialogue_header
            self._apply_dialogue_header_style()
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
            workspace.setObjectName("timelineWorkspace")
            workspace_layout = QHBoxLayout(workspace)
            workspace_layout.setContentsMargins(0, 0, 0, 0)
            workspace_layout.setSpacing(2)
            workspace_layout.addWidget(col_dialogue, 1)
            workspace_layout.addWidget(col_stage, 0)
            workspace_layout.addWidget(col_effect, 0)

            self._workspace_scroll.setWidget(workspace)
            self._workspace_root = workspace
            self._apply_workspace_bg()

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
        # task.md #8：點 chip 改說話者 → 通知外層重載預覽 + 標 dirty
        self.dialogue_list.speaker_changed.connect(self._on_dialogue_speaker_changed)
        # Task 6：刪除 / 編輯文字 / 插入 → refresh + 重載預覽 + 標 dirty
        self.dialogue_list.content_changed.connect(self._on_dialogue_content_changed)

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
        # 用 wildcard `obj.disconnect()` 在 Qt6 會吐 "destroyed signal of X::unnamed"
        # 警告，且在某些情境下會導致 segfault（theme 切換時 setStyleSheet 連鎖
        # restyle 觸發 UAF）。逐 signal-slot 明確 disconnect 才安全。
        if not getattr(self, "_signals_connected", False):
            return
        bindings = (
            (getattr(self, "dialogue_list", None), (
                ("dialogue_moved", self._on_dialogue_moved),
                ("cursor_changed", self._on_cursor_from_widget),
                ("selection_changed", self._on_cursor_from_widget),
                ("speaker_changed", self._on_dialogue_speaker_changed),
                ("content_changed", self._on_dialogue_content_changed),
            )),
            (getattr(self, "stage_panel", None), (
                ("cursor_changed", self._on_cursor_from_widget),
                ("segment_committed", self._on_segment_committed),
                ("segment_selected", self._on_stage_segment_selected),
            )),
            (getattr(self, "effect_timeline", None), (
                ("cursor_changed", self._on_cursor_from_widget),
                ("segment_committed", self._on_segment_committed),
                ("segment_selected", self._on_effect_segment_selected),
            )),
        )
        for obj, sigs in bindings:
            if obj is None:
                continue
            for sig_name, slot in sigs:
                try:
                    getattr(obj, sig_name).disconnect(slot)
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
        # Phase 5.1：切 scene → preview 位置重置到該 scene 開頭
        self._last_preview_pos = (max(0, index), 0)
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
        # Task 6：暴露 dialogue_list 的目前選取列，供「貼上文字」插入模式定位。
        if not hasattr(self, "dialogue_list"):
            return None
        return self.dialogue_list._selected_idx

    def refresh(self) -> None:
        """外部觸發重新繪製三域 widget（資料未變結構、只需重繪）。"""
        # 更新角色顏色映射（角色可能被重命名 / 重新著色）
        color_map = self._character_color_map()
        self.dialogue_list.set_character_colors(color_map)
        self.stage_panel.set_character_colors(color_map)
        if self._project:
            self.stage_panel.set_characters(self._project.characters)
        self.dialogue_list.refresh()
        self.stage_panel.refresh()
        self.effect_timeline.refresh()
        # segment editor 的候選也可能變（角色 / 服裝被編輯）
        if self._project:
            self.segment_editor.set_project(self._project)

    def _build_dialogue_header(self) -> QWidget:
        """三欄 header（索引 / 角色 / 台詞），寬度對齊 dialogue_list 的卡片內三欄。"""
        h = QWidget()
        h.setObjectName("dialogueHeader")
        lay = QHBoxLayout(h)
        # 卡片有 6px 外邊距 + 4px 內邊距，total left padding ~6px。對齊
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(0)
        self._dlg_header_labels: list[QLabel] = []
        # 索引欄
        l_idx = QLabel("索引")
        l_idx.setFixedWidth(shared.COL_INDEX_W)
        l_idx.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dlg_header_labels.append(l_idx)
        lay.addWidget(l_idx)
        # 角色欄
        l_char = QLabel("角色")
        l_char.setFixedWidth(shared.COL_CHARACTER_W)
        l_char.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dlg_header_labels.append(l_char)
        lay.addWidget(l_char)
        # 台詞欄（伸縮）
        l_text = QLabel("台詞")
        l_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dlg_header_labels.append(l_text)
        lay.addWidget(l_text, 1)
        return h

    def _apply_dialogue_header_style(self) -> None:
        if not getattr(self, "_dialogue_header", None):
            return
        bg = shared.BG_PANEL.name()
        fg = shared.TEXT_PRIMARY.name()
        # 父 widget bg；子 label 文字色 + 粗體
        self._dialogue_header.setStyleSheet(
            f"QWidget#dialogueHeader {{ background:{bg}; }} "
            f"QWidget#dialogueHeader QLabel {{ color:{fg}; padding:6px 0; "
            f"font-weight:bold; background:transparent; }}"
        )

    def _apply_workspace_bg(self) -> None:
        """workspace 容器 + ScrollArea viewport 背景跟主題；避免欄位間隙與右緣黑邊。"""
        bg = shared.BG_DARK.name()
        if getattr(self, "_workspace_root", None):
            self._workspace_root.setStyleSheet(
                f"QWidget#timelineWorkspace {{ background-color: {bg}; }}"
            )
        if getattr(self, "_workspace_scroll", None):
            vp = self._workspace_scroll.viewport()
            if vp:
                vp.setStyleSheet(f"background-color: {bg};")

    def refresh_theme(self) -> None:
        """主題切換後外部呼叫：重套 timeline header stylesheet 並重畫所有 paint widget。"""
        self._apply_dialogue_header_style()
        self._apply_workspace_bg()
        if hasattr(self, "stage_panel"):
            self.stage_panel.refresh_theme()
        if hasattr(self, "effect_timeline"):
            self.effect_timeline.refresh_theme()
        if hasattr(self, "_effect_header") and self._effect_header is not None:
            self._effect_header.refresh_theme()
        if hasattr(self, "dialogue_list"):
            self.dialogue_list.update()
        # StageHeader 在 _Column 內由 layout 持有；用 findChildren 抓出來重套
        from src.ui.stage_panel import StageHeader
        for sh in self.findChildren(StageHeader):
            sh.refresh_theme()

    # ── Signal handlers ────────────────────────────────────

    def _on_dialogue_moved(self, src: int, dst: int) -> None:
        scene = self._get_current_scene()
        if scene is None:
            return
        scene.move_dialogue(src, dst)
        self.refresh()
        self.project_changed.emit()

    def _on_cursor_from_widget(self, idx: int) -> None:
        # 三 widget 共享游標：一律廣播到所有 widget（包括 sender 自己）。
        # 因為 stage_panel / effect_timeline 內部各有多條 sub-lane，當其中一條 lane
        # 自己 hover 更新 _cursor_idx 後，必須讓「同 panel 內的其他 lane」也同步。
        # set_cursor 是 idempotent（值相同就 early return），重複呼叫無副作用。
        if self._building:
            return
        for w in (self.dialogue_list, self.stage_panel, self.effect_timeline):
            w.set_cursor(idx)
        # 預覽同步（Preview 已載入時）
        if self._preview_stack.currentIndex() == 1 and self._current_scene_index >= 0:
            self.preview.jump_to_dialogue(self._current_scene_index, idx)
            # Phase 5.1：記下目前停留位置，供後續 reload 恢復
            self._last_preview_pos = (self._current_scene_index, idx)

    def _on_stage_segment_selected(self, seg) -> None:
        # stage 選中 → 清掉 effect 的選取
        for lane in self.effect_timeline.lanes.values():
            lane.select_segment(None)
        # task.md #7：依 lane 動態替換編輯器標題
        if seg is not None:
            lane_pos = self._stage_lane_of_segment(seg)
            label = {
                "left": "舞台左側角色設定",
                "center": "舞台中間角色設定",
                "right": "舞台右側角色設定",
            }.get(lane_pos, "Segment 編輯器")
            self.segment_editor.set_lane_label(label)
        self._show_segment_editor_for(seg, self.stage_panel)

    def _on_effect_segment_selected(self, seg) -> None:
        for lane in self.stage_panel.lanes.values():
            lane.select_segment(None)
        if seg is not None:
            self.segment_editor.set_lane_label("特效軌道設定")
        self._show_segment_editor_for(seg, self.effect_timeline)

    def _stage_lane_of_segment(self, seg) -> str | None:
        """task.md #7：找出 stage segment 屬於哪條 lane（左/中/右）。"""
        if not self._project or self._current_scene_index < 0:
            return None
        scene = self._project.scenes[self._current_scene_index]
        for pos, segments in scene.all_stage_lanes().items():
            if seg in segments:
                return pos
        return None

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

    def _reload_preview_keep_position(self) -> None:
        """Phase 5.1：reload 預覽後跳回 `_last_preview_pos`，避免每次 commit 都回到第 0 句。

        QTimer 500ms 是保守值：等 QtWebEngine loadFinished + engine.js 初始化。
        若使用者環境慢仍會看到短暫跳首，屬已知限制（計畫書風險條 1）。
        """
        if not self._project or self._current_scene_index < 0:
            return
        scene_idx, dlg_idx = self._last_preview_pos
        self.preview.reload_preview(self._project)
        QTimer.singleShot(
            500, lambda s=scene_idx, d=dlg_idx: self.preview.jump_to_dialogue(s, d)
        )

    def _on_segment_committed(self) -> None:
        """commit 邊界（拖完 / 雙擊新增 / Delete / 加軌道 / 改軌道色）：reload 預覽 + 標 dirty。

        live drag 中的 segment_changed 不走這條，避免每 mouseMove 重載 webengine。
        widget 自己已在 mouseMove 內 self.update() 完成重繪。
        Phase 5.1：reload 後跳回原位置。
        """
        if self._building:
            return
        self._reload_preview_keep_position()
        self.project_changed.emit()

    def _on_dialogue_speaker_changed(self, _idx: int) -> None:
        """task.md #8：對話列說話者 chip 改變 → reload 預覽 + 標 dirty。"""
        if self._building:
            return
        self._reload_preview_keep_position()
        self.project_changed.emit()

    def _on_dialogue_content_changed(self) -> None:
        """Task 6：對話列內容變更（刪除 / 編輯文字 / 插入）→ refresh + reload 預覽 + 標 dirty。

        列數可能變化，需 refresh() 重算三域高度（共用 Y 軸）。
        """
        if self._building:
            return
        self.refresh()
        self._reload_preview_keep_position()
        self.project_changed.emit()

    def _on_segment_edited(self) -> None:
        """來自 SegmentEditor payload 變更：是單次動作（非 drag loop）。

        StageSegment 的 character/costume/sprite 變了 → 對應 lane 需要重畫 chip；
        EffectSegment 的 type/params 變了 → effect lane 重畫。
        然後 reload 預覽 + 標 dirty（Phase 5.1：跳回原位置）。
        """
        if self._building:
            return
        self.stage_panel.refresh()
        self.effect_timeline.refresh()
        self._reload_preview_keep_position()
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
        # Phase 5.1：不論是否為 current scene 都記位置，讓跨 scene AUTO 播放也能被恢復
        self._last_preview_pos = (scene_idx, dlg_idx)
        if scene_idx != self._current_scene_index:
            return
        self.dialogue_list.set_cursor(dlg_idx)
        self.stage_panel.set_cursor(dlg_idx)
        self.effect_timeline.set_cursor(dlg_idx)
