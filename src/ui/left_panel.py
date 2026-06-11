"""左側面板：場景列表 + 場景屬性 + 角色列表。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ComboBox, LineEdit, ListWidget, PushButton, SegmentedWidget, StrongBodyLabel

from src.core.models import Character, Episode, Project, Scene
from src.ui import palette
from src.ui.icons import design_icon, themed_icon
from src.ui.palette import PRESET_NAME_COLORS as PRESET_COLORS

NONE_LABEL = "(無)"


class _HoverDeleteItemWidget(QWidget):
    """清單項目 widget：文字標籤（可加圖示）+ hover 時顯示的 × 刪除按鈕。"""

    delete_clicked = pyqtSignal()
    item_double_clicked = pyqtSignal()

    def __init__(
        self,
        text: str,
        icon_pixmap: QPixmap | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(6)

        self._icon_label: QLabel | None = None
        if icon_pixmap is not None:
            self._icon_label = QLabel()
            self._icon_label.setPixmap(icon_pixmap)
            self._icon_label.setFixedSize(32, 32)
            self._icon_label.setScaledContents(True)
            layout.addWidget(self._icon_label)

        self._text_label = QLabel(text)
        self._text_label.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text_label, 1)

        self._btn_del = QPushButton()
        self._btn_del.setObjectName("hoverDeleteButton")
        self._btn_del.setIcon(design_icon("close"))
        self._btn_del.setIconSize(QSize(14, 14))
        self._btn_del.setFixedSize(20, 20)
        self._btn_del.setToolTip("移除")
        self._btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_del.hide()
        self._btn_del.clicked.connect(self.delete_clicked)
        layout.addWidget(self._btn_del)

        self.setLayout(layout)

    def set_text(self, text: str) -> None:
        self._text_label.setText(text)

    def update_icon(self, pixmap: QPixmap) -> None:
        if self._icon_label is not None:
            self._icon_label.setPixmap(pixmap)

    def enterEvent(self, event) -> None:
        self._btn_del.show()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._btn_del.hide()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.item_double_clicked.emit()
        super().mouseDoubleClickEvent(event)



class LeftPanel(QWidget):
    """左側面板：場景管理（列表 + 屬性）+ 角色管理。"""

    # 場景信號
    scene_selected = pyqtSignal(int)        # scene index
    scene_added = pyqtSignal()
    scene_removed = pyqtSignal(int)         # scene index
    scenes_reordered = pyqtSignal()
    scene_property_changed = pyqtSignal()   # 背景/BGM changed

    # 角色信號
    character_add_requested = pyqtSignal()
    character_edit_requested = pyqtSignal(int)   # character index
    character_remove_requested = pyqtSignal(int)
    character_property_changed = pyqtSignal()    # name/color/position edited
    costume_edit_requested = pyqtSignal(int)     # character index

    # 影片（Episode）信號
    episode_switched = pyqtSignal(int)   # 新 active episode index
    episodes_changed = pyqtSignal()      # 新增/改名/刪除影片

    # 角色匯入信號
    character_import_requested = pyqtSignal()

    # 素材匯入信號
    bg_import_requested = pyqtSignal()
    music_import_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._project: Project | None = None
        self._current_scene_index: int = -1
        self._current_char_index: int = -1
        self._updating = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)

        # ── 上方：SegmentedWidget 切換（場景 / 角色） ──
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        self._seg_widget = SegmentedWidget()
        self._seg_widget.addItem(routeKey="scenes", text="場景")
        self._seg_widget.addItem(routeKey="characters", text="角色")
        self._seg_widget.setCurrentItem("scenes")
        self._seg_widget.currentItemChanged.connect(self._on_tab_changed)
        top_layout.addWidget(self._seg_widget)

        self._list_stack = QStackedWidget()

        # Page 0：場景列表
        scene_section = QWidget()
        scene_layout = QVBoxLayout()
        scene_layout.setContentsMargins(0, 0, 0, 0)
        scene_layout.setSpacing(4)

        # 影片切換列（漸進揭露：單支影片時整列隱藏，入口在檔案選單「新增影片」）
        self._episode_bar = QWidget()
        ep_row = QHBoxLayout()
        ep_row.setContentsMargins(0, 0, 0, 0)
        ep_row.setSpacing(4)
        _ep_lbl = QLabel("影片:")
        _ep_lbl.setFixedWidth(56)
        ep_row.addWidget(_ep_lbl)
        self.combo_episode = ComboBox()
        ep_row.addWidget(self.combo_episode, 1)
        self.btn_add_episode = PushButton("＋")
        self.btn_add_episode.setFixedWidth(32)
        self.btn_add_episode.setToolTip("新增影片（共用本作品的角色與素材）")
        ep_row.addWidget(self.btn_add_episode)
        self.btn_episode_menu = PushButton("⋯")
        self.btn_episode_menu.setFixedWidth(32)
        self.btn_episode_menu.setToolTip("重新命名／刪除這支影片")
        ep_row.addWidget(self.btn_episode_menu)
        self._episode_bar.setLayout(ep_row)
        scene_layout.addWidget(self._episode_bar)

        self.scene_list = ListWidget()
        _f = self.scene_list.font(); _f.setPixelSize(18); self.scene_list.setFont(_f)
        self.scene_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        scene_layout.addWidget(self.scene_list)
        self.btn_add_scene = QPushButton(" 新增場景")
        self.btn_add_scene.setObjectName("dashedButton")
        self.btn_add_scene.setIcon(themed_icon("add"))
        self.btn_add_scene.setIconSize(QSize(16, 16))
        scene_layout.addWidget(self.btn_add_scene)
        scene_section.setLayout(scene_layout)
        self._list_stack.addWidget(scene_section)

        # Page 1：角色列表
        char_section = QWidget()
        char_layout = QVBoxLayout()
        char_layout.setContentsMargins(0, 0, 0, 0)
        char_layout.setSpacing(4)
        self.character_list = ListWidget()
        _f = self.character_list.font(); _f.setPixelSize(18); self.character_list.setFont(_f)
        self.character_list.setIconSize(QSize(32, 32))
        char_layout.addWidget(self.character_list)
        self.btn_add_char = QPushButton(" 新增角色")
        self.btn_add_char.setObjectName("dashedButton")
        self.btn_add_char.setIcon(themed_icon("add"))
        self.btn_add_char.setIconSize(QSize(16, 16))
        char_layout.addWidget(self.btn_add_char)
        self.btn_import_char = QPushButton(" 從其他作品匯入…")
        self.btn_import_char.setObjectName("dashedButton")
        self.btn_import_char.setIcon(themed_icon("open"))
        self.btn_import_char.setIconSize(QSize(16, 16))
        self.btn_import_char.setToolTip("把另一個作品做好的角色（含立繪）複製進來")
        char_layout.addWidget(self.btn_import_char)
        char_section.setLayout(char_layout)
        self._list_stack.addWidget(char_section)

        top_layout.addWidget(self._list_stack)
        top_widget.setLayout(top_layout)

        splitter.addWidget(top_widget)

        # ── 下方：Inspector 屬性面板 ──
        inspector_group = QGroupBox("屬性")
        inspector_group.setStyleSheet("QGroupBox::title { font-weight: bold; }")
        inspector_layout = QVBoxLayout()
        self._inspector = QStackedWidget()

        # Page 0：空白提示
        placeholder = QLabel("選擇場景或角色\n以查看屬性")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inspector.addWidget(placeholder)

        # Page 1：場景屬性
        scene_props = QWidget()
        props_layout = QVBoxLayout()
        props_layout.setContentsMargins(0, 0, 0, 0)
        # 兩列共用 label 寬度，確保 ComboBox 左緣對齊
        _LABEL_W = 56
        bg_row = QHBoxLayout()
        _bg_lbl = QLabel("背景:")
        _bg_lbl.setFixedWidth(_LABEL_W)
        bg_row.addWidget(_bg_lbl)
        self.combo_background = ComboBox()
        self.combo_background.addItem(NONE_LABEL)
        bg_row.addWidget(self.combo_background, 1)
        # 上傳按鈕：不設 fixed 寬，讓字體放大時不裁切
        self.btn_import_bg = PushButton("上傳")
        bg_row.addWidget(self.btn_import_bg)
        props_layout.addLayout(bg_row)
        bgm_row = QHBoxLayout()
        _bgm_lbl = QLabel("BGM:")
        _bgm_lbl.setFixedWidth(_LABEL_W)
        bgm_row.addWidget(_bgm_lbl)
        self.combo_bgm = ComboBox()
        self.combo_bgm.addItem(NONE_LABEL)
        bgm_row.addWidget(self.combo_bgm, 1)
        self.btn_import_music = PushButton("上傳")
        bgm_row.addWidget(self.btn_import_music)
        props_layout.addLayout(bgm_row)
        # Phase 2：場景層級的特效 ComboBox 移除，改由特效 timeline 拖 segment 管理。
        props_layout.addStretch()
        scene_props.setLayout(props_layout)
        self._inspector.addWidget(scene_props)

        # Page 2：角色屬性（可編輯）
        char_props = QWidget()
        char_props_layout = QVBoxLayout()
        char_props_layout.setContentsMargins(0, 0, 0, 0)
        char_props_layout.setSpacing(4)
        # 名稱
        name_row = QHBoxLayout()
        name_row.addWidget(StrongBodyLabel("名稱："))
        self._edit_char_name = LineEdit()
        self._edit_char_name.setPlaceholderText("角色名稱")
        name_row.addWidget(self._edit_char_name, 1)
        char_props_layout.addLayout(name_row)
        # 顏色：預設色塊按鈕列
        char_props_layout.addWidget(StrongBodyLabel("名牌顏色："))
        color_grid = QHBoxLayout()
        color_grid.setSpacing(4)
        self._color_btns: list[QPushButton] = []
        for hex_color, label in PRESET_COLORS:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setToolTip(label)
            btn.clicked.connect(lambda _, c=hex_color: self._on_preset_color_clicked(c))
            color_grid.addWidget(btn)
            self._color_btns.append(btn)
        color_grid.addStretch()
        char_props_layout.addLayout(color_grid)
        # 服裝列表
        char_props_layout.addWidget(StrongBodyLabel("服裝："))
        self._char_costume_list = ListWidget()
        # task.md #12：跟 QApplication.font，不硬編碼 18px
        self._char_costume_list.setFixedHeight(70)
        char_props_layout.addWidget(self._char_costume_list)
        btn_edit_costume = QPushButton("編輯服裝…")
        btn_edit_costume.setObjectName("dashedButton")
        btn_edit_costume.clicked.connect(
            lambda: self.costume_edit_requested.emit(self._current_char_index)
        )
        char_props_layout.addWidget(btn_edit_costume)
        char_props_layout.addStretch()
        char_props.setLayout(char_props_layout)
        self._inspector.addWidget(char_props)
        # 角色屬性連接
        self._edit_char_name.editingFinished.connect(self._on_char_name_changed)

        inspector_layout.addWidget(self._inspector)
        inspector_group.setLayout(inspector_layout)

        splitter.addWidget(inspector_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)
        self.setLayout(layout)

        # 信號連接
        self.scene_list.currentRowChanged.connect(self._on_scene_selected)
        self.btn_add_scene.clicked.connect(self._on_add_scene)
        self.scene_list.model().rowsMoved.connect(self._on_scenes_reordered)
        self.combo_background.currentIndexChanged.connect(self._on_background_changed)
        self.combo_bgm.currentIndexChanged.connect(self._on_bgm_changed)
        self.btn_import_bg.clicked.connect(self.bg_import_requested.emit)
        self.btn_import_music.clicked.connect(self.music_import_requested.emit)

        self.character_list.currentRowChanged.connect(self._on_char_selection_changed)
        self.btn_add_char.clicked.connect(self.character_add_requested.emit)
        self.btn_import_char.clicked.connect(self.character_import_requested.emit)

        self.combo_episode.currentIndexChanged.connect(self._on_episode_combo_changed)
        self.btn_add_episode.clicked.connect(self.add_episode)
        self.btn_episode_menu.clicked.connect(self._on_episode_menu)

    def _on_tab_changed(self, route_key: str) -> None:
        """SegmentedWidget 切換：同步 stacked widget 和屬性面板。"""
        index = 0 if route_key == "scenes" else 1
        self._list_stack.setCurrentIndex(index)
        if index == 0:
            if self._current_scene_index >= 0:
                self._inspector.setCurrentIndex(1)
            else:
                self._inspector.setCurrentIndex(0)
        else:
            row = self.character_list.currentRow()
            if row >= 0:
                self._on_char_selection_changed(row)
            else:
                self._inspector.setCurrentIndex(0)

    # ── 公開方法 ──

    def set_project(self, project: Project) -> None:
        """綁定 Project，重建 UI。"""
        self._project = project
        self._refresh_episode_bar()
        self._refresh_scene_list()
        self._refresh_character_list()

    def refresh_theme(self) -> None:
        """主題切換後重新染色 icon + 重套預設色按鈕邊框。"""
        if hasattr(self, "btn_add_scene"):
            self.btn_add_scene.setIcon(themed_icon("add"))
        if hasattr(self, "btn_add_char"):
            self.btn_add_char.setIcon(themed_icon("add"))
        # 重套色塊按鈕邊框（依當前選取色）
        if hasattr(self, "_color_btns") and self._color_btns:
            current = getattr(self, "_current_color_hex", PRESET_COLORS[0][0])
            self._update_color_display(current)

    def set_asset_lists(self, backgrounds: list[str], music: list[str]) -> None:
        """更新背景和 BGM 的 ComboBox 選項，重建後以當前場景 model 值回填。"""
        self._updating = True

        self.combo_background.clear()
        self.combo_background.addItem(NONE_LABEL)
        self.combo_background.addItems(backgrounds)

        self.combo_bgm.clear()
        self.combo_bgm.addItem(NONE_LABEL)
        self.combo_bgm.addItems(music)

        self._updating = False

        # 選項重建後以當前場景 model 值回填（而非舊的 currentText），防呆
        self._sync_props_to_scene()

    def get_current_scene_index(self) -> int:
        """取得目前選取的場景索引。"""
        return self._current_scene_index

    # ── 影片（Episode）切換 ──

    def _refresh_episode_bar(self) -> None:
        """重建影片下拉選單；單支影片時整列隱藏（漸進揭露）。"""
        self._updating = True
        self.combo_episode.clear()
        if self._project:
            for ep in self._project.episodes:
                self.combo_episode.addItem(ep.name)
            self.combo_episode.setCurrentIndex(self._project.active_episode_index)
        multi = bool(self._project) and len(self._project.episodes) > 1
        self._episode_bar.setVisible(multi)
        self._updating = False

    def _on_episode_combo_changed(self, index: int) -> None:
        if self._updating or not self._project or index < 0:
            return
        self._project.active_episode_index = index
        self._refresh_scene_list()
        self.episode_switched.emit(index)

    def add_episode(self) -> None:
        """新增一支影片並切換過去；公開給檔案選單呼叫。"""
        if not self._project:
            return
        default = self._project.next_episode_name()
        name, ok = QInputDialog.getText(self, "新增影片", "影片名稱：", text=default)
        if not ok:
            return
        self._project.episodes.append(Episode(name=name.strip() or default))
        self._project.active_episode_index = len(self._project.episodes) - 1
        self._refresh_episode_bar()
        self._refresh_scene_list()
        self.episodes_changed.emit()

    def _on_episode_menu(self) -> None:
        menu = QMenu(self)
        act_rename = menu.addAction("重新命名")
        act_delete = menu.addAction("刪除這支影片")
        chosen = menu.exec(
            self.btn_episode_menu.mapToGlobal(self.btn_episode_menu.rect().bottomLeft())
        )
        if chosen == act_rename:
            self._on_rename_episode()
        elif chosen == act_delete:
            self._on_remove_episode()

    def _on_rename_episode(self) -> None:
        if not self._project:
            return
        ep = self._project.active_episode
        name, ok = QInputDialog.getText(self, "重新命名影片", "影片名稱：", text=ep.name)
        if ok and name.strip():
            ep.name = name.strip()
            self._refresh_episode_bar()
            self.episodes_changed.emit()

    def _on_remove_episode(self) -> None:
        if not self._project or len(self._project.episodes) <= 1:
            return  # 最後一支不可刪（按鈕列在單影片時本來就隱藏；此為保險）
        ep = self._project.active_episode
        n_dlg = sum(len(s.dialogues) for s in ep.scenes)
        result = QMessageBox.question(
            self, "刪除影片",
            f"「{ep.name}」含 {len(ep.scenes)} 個場景、{n_dlg} 則對話，將一併刪除。\n"
            "（角色與素材屬於整個作品，不受影響）\n確定刪除？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        idx = self._project.active_episode_index
        self._project.episodes.pop(idx)
        self._project.active_episode_index = max(0, idx - 1)
        self._refresh_episode_bar()
        self._refresh_scene_list()
        self.episodes_changed.emit()

    # ── 場景列表 ──

    def _refresh_scene_list(self) -> None:
        """重建場景列表，每項用帶 hover 刪除按鈕的 widget。"""
        self._updating = True
        self.scene_list.clear()
        if self._project:
            for scene in self._project.scenes:
                label = scene.id
                if scene.background:
                    label += f"  [{scene.background}]"
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, scene.id)
                item.setSizeHint(QSize(0, 36))
                self.scene_list.addItem(item)
                widget = _HoverDeleteItemWidget(label)
                widget.delete_clicked.connect(
                    lambda checked=False, it=item: self._on_remove_scene_by_item(it)
                )
                widget.item_double_clicked.connect(
                    lambda it=item: self._on_scene_rename_item(it)
                )
                self.scene_list.setItemWidget(item, widget)
        self._updating = False

        if self._project and self._project.scenes:
            self.scene_list.setCurrentRow(0)
        else:
            self._current_scene_index = -1
            self._sync_props_to_scene()

    def _on_scene_selected(self, index: int) -> None:
        if self._updating:
            return
        self._current_scene_index = index
        self._sync_props_to_scene()
        if index >= 0:
            self._inspector.setCurrentIndex(1)
        else:
            self._inspector.setCurrentIndex(0)
        self.scene_selected.emit(index)

    def _sync_props_to_scene(self) -> None:
        """同步場景屬性 ComboBox 到當前場景。"""
        self._updating = True
        scene = self._get_current_scene()
        if scene:
            self._set_combo_value(self.combo_background, scene.background)
            self._set_combo_value(self.combo_bgm, scene.bgm)
        else:
            self.combo_background.setCurrentIndex(0)
            self.combo_bgm.setCurrentIndex(0)
        self._updating = False

    @staticmethod
    def _set_combo_value(combo, value: str | None) -> None:
        if not value:
            combo.setCurrentIndex(0)
            return
        idx = combo.findText(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _on_background_changed(self, index: int) -> None:
        if self._updating:
            return
        scene = self._get_current_scene()
        if not scene:
            return
        scene.background = None if index == 0 else self.combo_background.currentText()
        self._refresh_scene_list_label()
        self.scene_property_changed.emit()

    def _on_bgm_changed(self, index: int) -> None:
        if self._updating:
            return
        scene = self._get_current_scene()
        if not scene:
            return
        scene.bgm = None if index == 0 else self.combo_bgm.currentText()
        self.scene_property_changed.emit()

    def _refresh_scene_list_label(self) -> None:
        """更新當前場景在列表 widget 中的顯示文字。"""
        scene = self._get_current_scene()
        if not scene or self._current_scene_index < 0:
            return
        item = self.scene_list.item(self._current_scene_index)
        if item:
            label = scene.id
            if scene.background:
                label += f"  [{scene.background}]"
            widget = self.scene_list.itemWidget(item)
            if widget:
                widget.set_text(label)

    def _on_add_scene(self) -> None:
        if not self._project:
            return
        scene_id = self._project.next_scene_id()
        self._project.scenes.append(Scene(id=scene_id))
        self._refresh_scene_list()
        self.scene_list.setCurrentRow(len(self._project.scenes) - 1)
        self.scene_added.emit()

    def _on_remove_scene_by_item(self, item: QListWidgetItem) -> None:
        """由 item widget 的刪除按鈕觸發；場景有對話 / segment 時先詢問確認。"""
        row = self.scene_list.row(item)
        if row < 0 or not self._project or row >= len(self._project.scenes):
            return
        scene = self._project.scenes[row]
        n_dialogues = len(scene.dialogues)
        n_stage = sum(len(lane) for lane in scene.all_stage_lanes().values())
        n_effect = sum(len(t.segments) for t in scene.effect_tracks)
        if n_dialogues + n_stage + n_effect > 0:
            detail = (
                f"場景「{scene.id}」將連帶刪除 {n_dialogues} 則對話、"
                f"{n_stage} 條立繪 segment、{n_effect} 條特效 segment。\n確定要移除？"
            )
            result = QMessageBox.question(
                self,
                "確認移除場景",
                detail,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return
        self._project.scenes.pop(row)
        self._refresh_scene_list()
        self.scene_removed.emit(row)

    def _on_scene_rename_item(self, item: QListWidgetItem) -> None:
        """雙擊場景 → QInputDialog 重命名。"""
        row = self.scene_list.row(item)
        if row < 0 or not self._project or row >= len(self._project.scenes):
            return
        scene = self._project.scenes[row]
        new_name, ok = QInputDialog.getText(
            self, "重命名場景", "場景 ID:", text=scene.id
        )
        if ok and new_name.strip():
            scene.id = new_name.strip()
            item.setData(Qt.ItemDataRole.UserRole, scene.id)
            label = scene.id
            if scene.background:
                label += f"  [{scene.background}]"
            widget = self.scene_list.itemWidget(item)
            if widget:
                widget.set_text(label)

    def _on_scenes_reordered(self) -> None:
        if self._updating or not self._project:
            return
        new_order = []
        for i in range(self.scene_list.count()):
            scene_id = self.scene_list.item(i).data(Qt.ItemDataRole.UserRole)
            for scene in self._project.scenes:
                if scene.id == scene_id:
                    new_order.append(scene)
                    break
        self._project.scenes = new_order
        self.scenes_reordered.emit()

    def _get_current_scene(self) -> Scene | None:
        if (
            not self._project
            or self._current_scene_index < 0
            or self._current_scene_index >= len(self._project.scenes)
        ):
            return None
        return self._project.scenes[self._current_scene_index]

    # ── 角色列表 ──

    def _refresh_character_list(self) -> None:
        """重建角色列表，每項帶頭像 + hover 刪除按鈕。"""
        self.character_list.clear()
        if not self._project:
            return
        assets_dir: Path | None = None
        if self._project.project_path:
            assets_dir = self._project.project_path.parent / "assets"
        for char in self._project.characters:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 40))
            self.character_list.addItem(item)
            icon_pixmap = self._get_char_icon(char, assets_dir)
            widget = _HoverDeleteItemWidget(char.name, icon_pixmap=icon_pixmap)
            widget.delete_clicked.connect(
                lambda checked=False, it=item: self._on_remove_char_by_item(it)
            )
            widget.item_double_clicked.connect(
                lambda it=item: self._on_char_double_clicked_item(it)
            )
            self.character_list.setItemWidget(item, widget)

    def _get_char_icon(self, char: Character, assets_dir: Path | None) -> QPixmap:
        """取得角色 Icon：裁切上方 40% 高 × 水平中央 40% 寬後縮放至 32×32。"""
        if assets_dir and char.sprites:
            sprite_path = assets_dir / char.sprites[0].filename
            if sprite_path.exists():
                pm = QPixmap(str(sprite_path))
                if not pm.isNull():
                    w, h = pm.width(), pm.height()
                    crop_w = max(1, int(w * 0.4))
                    crop_h = max(1, int(h * 0.4))
                    x = (w - crop_w) // 2
                    cropped = pm.copy(x, 0, crop_w, crop_h)
                    return cropped.scaled(
                        32, 32,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(char.name_color))
        return pixmap

    def _on_remove_char_by_item(self, item: QListWidgetItem) -> None:
        """由 item widget 的刪除按鈕觸發。"""
        row = self.character_list.row(item)
        if row >= 0:
            self.character_remove_requested.emit(row)

    def _on_char_double_clicked_item(self, item: QListWidgetItem) -> None:
        """雙擊角色 → 開啟編輯對話框。"""
        row = self.character_list.row(item)
        if row >= 0:
            self.character_edit_requested.emit(row)

    def _on_char_selection_changed(self, row: int) -> None:
        self._current_char_index = row
        if row >= 0 and self._project and row < len(self._project.characters):
            self._refresh_char_props()
            self._inspector.setCurrentIndex(2)
        else:
            if self._current_scene_index >= 0:
                self._inspector.setCurrentIndex(1)
            else:
                self._inspector.setCurrentIndex(0)

    def _refresh_char_props(self) -> None:
        """將角色屬性填入可編輯控件。"""
        char = self._get_current_char()
        if not char:
            return
        self._updating = True
        self._edit_char_name.setText(char.name)
        self._update_color_display(char.name_color)
        self._char_costume_list.clear()
        for cos in char.costumes:
            self._char_costume_list.addItem(cos.name)
        self._updating = False

    def _update_color_display(self, hex_color: str) -> None:
        """標示目前選取的預設色（無獨立預覽方塊；以選取邊框呈現）。"""
        pal = palette.current()
        sel_border = pal.border_focus.name()
        unsel_border = pal.border.name()
        self._current_color_hex = hex_color
        for btn, (c, _) in zip(self._color_btns, PRESET_COLORS):
            selected = c.upper() == hex_color.upper()
            border = f"3px solid {sel_border}" if selected else f"2px solid {unsel_border}"
            btn.setStyleSheet(
                f"background-color:{c}; border:{border}; border-radius:3px;"
            )

    def _get_current_char(self) -> Character | None:
        if (
            not self._project
            or self._current_char_index < 0
            or self._current_char_index >= len(self._project.characters)
        ):
            return None
        return self._project.characters[self._current_char_index]

    def _on_char_name_changed(self) -> None:
        if self._updating:
            return
        char = self._get_current_char()
        if not char:
            return
        new_name = self._edit_char_name.text().strip()
        if not new_name or new_name == char.name:
            return
        char.name = new_name
        # Update the item widget text
        item = self.character_list.item(self._current_char_index)
        if item:
            widget = self.character_list.itemWidget(item)
            if widget:
                widget.set_text(new_name)
        self.character_property_changed.emit()

    def _on_preset_color_clicked(self, hex_color: str) -> None:
        char = self._get_current_char()
        if not char:
            return
        char.name_color = hex_color
        self._update_color_display(hex_color)
        item = self.character_list.item(self._current_char_index)
        if item:
            widget = self.character_list.itemWidget(item)
            if widget:
                pm = QPixmap(32, 32)
                pm.fill(QColor(hex_color))
                widget.update_icon(pm)
        self.character_property_changed.emit()

    def refresh_costume_list(self) -> None:
        """外部呼叫：重新整理角色屬性面板的服裝列表（服裝編輯後）。"""
        self._refresh_char_props()

    def refresh_characters(self, keep_tab: bool = False) -> None:
        """外部呼叫：重新整理角色列表。keep_tab=True 時保持在角色頁。"""
        saved_index = self._current_char_index
        self._refresh_character_list()
        if keep_tab and saved_index >= 0:
            self._seg_widget.setCurrentItem("characters")
            self._list_stack.setCurrentIndex(1)
            self.character_list.setCurrentRow(saved_index)
            self._inspector.setCurrentIndex(2)

    def refresh_scenes(self) -> None:
        """外部呼叫：重新整理場景列表。"""
        self._refresh_scene_list()
