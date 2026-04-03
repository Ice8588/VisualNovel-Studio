"""左側面板：場景列表 + 場景屬性 + 角色列表。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.models import Character, Project, Scene

NONE_LABEL = "(無)"
EFFECT_OPTIONS = [NONE_LABEL, "rain", "snow", "crt", "pixel_dark"]


class LeftPanel(QWidget):
    """左側面板：場景管理（列表 + 屬性）+ 角色管理。"""

    # 場景信號
    scene_selected = pyqtSignal(int)        # scene index
    scene_added = pyqtSignal()
    scene_removed = pyqtSignal(int)         # scene index
    scenes_reordered = pyqtSignal()
    scene_property_changed = pyqtSignal()   # 背景/BGM/特效 changed

    # 角色信號
    character_add_requested = pyqtSignal()
    character_edit_requested = pyqtSignal(int)  # character index
    character_remove_requested = pyqtSignal(int)

    # 素材匯入信號
    bg_import_requested = pyqtSignal()
    music_import_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._project: Project | None = None
        self._current_scene_index: int = -1
        self._updating = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── 場景列表 ──
        scene_section = QWidget()
        scene_layout = QVBoxLayout()
        scene_layout.setContentsMargins(0, 0, 0, 0)
        scene_group = QGroupBox("場景列表")
        scene_group_layout = QVBoxLayout()
        self.scene_list = QListWidget()
        self.scene_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        scene_group_layout.addWidget(self.scene_list)
        scene_btn_layout = QHBoxLayout()
        self.btn_add_scene = QPushButton("新增")
        self.btn_remove_scene = QPushButton("移除")
        self.btn_remove_scene.setEnabled(False)
        scene_btn_layout.addWidget(self.btn_add_scene)
        scene_btn_layout.addWidget(self.btn_remove_scene)
        scene_group_layout.addLayout(scene_btn_layout)
        scene_group.setLayout(scene_group_layout)
        scene_layout.addWidget(scene_group)
        scene_section.setLayout(scene_layout)

        # ── 角色列表 ──
        char_section = QWidget()
        char_layout = QVBoxLayout()
        char_layout.setContentsMargins(0, 0, 0, 0)
        char_group = QGroupBox("角色列表")
        char_group_layout = QVBoxLayout()
        self.character_list = QListWidget()
        self.character_list.setIconSize(QSize(32, 32))
        char_group_layout.addWidget(self.character_list)
        char_btn_layout = QHBoxLayout()
        self.btn_add_char = QPushButton("新增")
        self.btn_edit_char = QPushButton("編輯")
        self.btn_remove_char = QPushButton("移除")
        self.btn_edit_char.setEnabled(False)
        self.btn_remove_char.setEnabled(False)
        char_btn_layout.addWidget(self.btn_add_char)
        char_btn_layout.addWidget(self.btn_edit_char)
        char_btn_layout.addWidget(self.btn_remove_char)
        char_group_layout.addLayout(char_btn_layout)
        char_group.setLayout(char_group_layout)
        char_layout.addWidget(char_group)
        char_section.setLayout(char_layout)

        # ── Inspector 屬性面板 ──
        inspector_group = QGroupBox("屬性")
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
        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("背景:"))
        self.combo_background = QComboBox()
        self.combo_background.addItem(NONE_LABEL)
        bg_row.addWidget(self.combo_background, 1)
        self.btn_import_bg = QPushButton("匯入")
        self.btn_import_bg.setFixedWidth(50)
        bg_row.addWidget(self.btn_import_bg)
        props_layout.addLayout(bg_row)
        bgm_row = QHBoxLayout()
        bgm_row.addWidget(QLabel("BGM:"))
        self.combo_bgm = QComboBox()
        self.combo_bgm.addItem(NONE_LABEL)
        bgm_row.addWidget(self.combo_bgm, 1)
        self.btn_import_music = QPushButton("匯入")
        self.btn_import_music.setFixedWidth(50)
        bgm_row.addWidget(self.btn_import_music)
        props_layout.addLayout(bgm_row)
        effect_row = QHBoxLayout()
        effect_row.addWidget(QLabel("特效:"))
        self.combo_effect = QComboBox()
        self.combo_effect.addItems(EFFECT_OPTIONS)
        effect_row.addWidget(self.combo_effect, 1)
        props_layout.addLayout(effect_row)
        props_layout.addStretch()
        scene_props.setLayout(props_layout)
        self._inspector.addWidget(scene_props)

        # Page 2：角色屬性（唯讀顯示）
        char_props = QWidget()
        char_props_layout = QVBoxLayout()
        char_props_layout.setContentsMargins(0, 0, 0, 0)
        self._lbl_char_name = QLabel("—")
        self._lbl_char_color = QLabel()
        self._lbl_char_color.setFixedSize(20, 20)
        self._lbl_char_position = QLabel("—")
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("名稱:"))
        name_row.addWidget(self._lbl_char_name, 1)
        color_row_layout = QHBoxLayout()
        color_row_layout.addWidget(QLabel("顏色:"))
        color_row_layout.addWidget(self._lbl_char_color)
        color_row_layout.addStretch()
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("位置:"))
        pos_row.addWidget(self._lbl_char_position, 1)
        char_props_layout.addLayout(name_row)
        char_props_layout.addLayout(color_row_layout)
        char_props_layout.addLayout(pos_row)
        char_props_layout.addStretch()
        char_props.setLayout(char_props_layout)
        self._inspector.addWidget(char_props)

        inspector_layout.addWidget(self._inspector)
        inspector_group.setLayout(inspector_layout)

        splitter.addWidget(scene_section)
        splitter.addWidget(char_section)
        splitter.addWidget(inspector_group)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 1)

        layout.addWidget(splitter)
        self.setLayout(layout)

        # 信號連接
        self.scene_list.currentRowChanged.connect(self._on_scene_selected)
        self.btn_add_scene.clicked.connect(self._on_add_scene)
        self.btn_remove_scene.clicked.connect(self._on_remove_scene)
        self.scene_list.model().rowsMoved.connect(self._on_scenes_reordered)
        self.combo_background.currentIndexChanged.connect(self._on_background_changed)
        self.combo_bgm.currentIndexChanged.connect(self._on_bgm_changed)
        self.combo_effect.currentIndexChanged.connect(self._on_effect_changed)
        self.btn_import_bg.clicked.connect(self.bg_import_requested.emit)
        self.btn_import_music.clicked.connect(self.music_import_requested.emit)

        self.character_list.currentRowChanged.connect(self._on_char_selection_changed)
        self.character_list.doubleClicked.connect(
            lambda: self.character_edit_requested.emit(self.character_list.currentRow())
        )
        self.btn_add_char.clicked.connect(self.character_add_requested.emit)
        self.btn_edit_char.clicked.connect(
            lambda: self.character_edit_requested.emit(self.character_list.currentRow())
        )
        self.btn_remove_char.clicked.connect(
            lambda: self.character_remove_requested.emit(self.character_list.currentRow())
        )

    # ── 公開方法 ──

    def set_project(self, project: Project) -> None:
        """綁定 Project，重建 UI。"""
        self._project = project
        self._refresh_scene_list()
        self._refresh_character_list()

    def set_asset_lists(self, backgrounds: list[str], music: list[str]) -> None:
        """更新背景和 BGM 的 ComboBox 選項。"""
        self._updating = True

        cur_bg = self.combo_background.currentText()
        cur_bgm = self.combo_bgm.currentText()

        self.combo_background.clear()
        self.combo_background.addItem(NONE_LABEL)
        self.combo_background.addItems(backgrounds)

        self.combo_bgm.clear()
        self.combo_bgm.addItem(NONE_LABEL)
        self.combo_bgm.addItems(music)

        idx_bg = self.combo_background.findText(cur_bg)
        self.combo_background.setCurrentIndex(max(0, idx_bg))
        idx_bgm = self.combo_bgm.findText(cur_bgm)
        self.combo_bgm.setCurrentIndex(max(0, idx_bgm))

        self._updating = False

    def get_current_scene_index(self) -> int:
        """取得目前選取的場景索引。"""
        return self._current_scene_index

    # ── 場景列表 ──

    def _refresh_scene_list(self) -> None:
        """重建場景列表。"""
        self._updating = True
        self.scene_list.clear()
        if self._project:
            for scene in self._project.scenes:
                label = scene.id
                if scene.background:
                    label += f"  [{scene.background}]"
                self.scene_list.addItem(label)
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
        self.btn_remove_scene.setEnabled(index >= 0)
        self._sync_props_to_scene()
        if index >= 0:
            self._inspector.setCurrentIndex(1)  # 顯示場景屬性
        else:
            self._inspector.setCurrentIndex(0)  # 空白
        self.scene_selected.emit(index)

    def _sync_props_to_scene(self) -> None:
        """同步場景屬性 ComboBox 到當前場景。"""
        self._updating = True
        scene = self._get_current_scene()
        if scene:
            self._set_combo_value(self.combo_background, scene.background)
            self._set_combo_value(self.combo_bgm, scene.bgm)
            effect_val = scene.effect or NONE_LABEL
            idx = self.combo_effect.findText(effect_val)
            self.combo_effect.setCurrentIndex(max(0, idx))
        else:
            self.combo_background.setCurrentIndex(0)
            self.combo_bgm.setCurrentIndex(0)
            self.combo_effect.setCurrentIndex(0)
        self._updating = False

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str | None) -> None:
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

    def _on_effect_changed(self, index: int) -> None:
        if self._updating:
            return
        scene = self._get_current_scene()
        if not scene:
            return
        scene.effect = None if index == 0 else self.combo_effect.currentText()
        self.scene_property_changed.emit()

    def _refresh_scene_list_label(self) -> None:
        """更新當前場景在列表中的顯示文字。"""
        scene = self._get_current_scene()
        if not scene or self._current_scene_index < 0:
            return
        item = self.scene_list.item(self._current_scene_index)
        if item:
            label = scene.id
            if scene.background:
                label += f"  [{scene.background}]"
            item.setText(label)

    def _on_add_scene(self) -> None:
        if not self._project:
            return
        scene_id = self._project.next_scene_id()
        self._project.scenes.append(Scene(id=scene_id))
        self._refresh_scene_list()
        self.scene_list.setCurrentRow(len(self._project.scenes) - 1)
        self.scene_added.emit()

    def _on_remove_scene(self) -> None:
        if not self._project or self._current_scene_index < 0:
            return
        idx = self._current_scene_index
        self._project.scenes.pop(idx)
        self._refresh_scene_list()
        self.scene_removed.emit(idx)

    def _on_scenes_reordered(self) -> None:
        if self._updating or not self._project:
            return
        new_order = []
        for i in range(self.scene_list.count()):
            text = self.scene_list.item(i).text()
            scene_id = text.split()[0]
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
        """重建角色列表，有 Sprite 時顯示縮圖，否則顯示色塊。"""
        self.character_list.clear()
        if not self._project:
            return
        assets_dir: Path | None = None
        if self._project.project_path:
            assets_dir = self._project.project_path.parent / "assets"
        for char in self._project.characters:
            item = QListWidgetItem(f"  {char.name}")
            pixmap = self._get_char_icon(char, assets_dir)
            item.setIcon(QIcon(pixmap))
            self.character_list.addItem(item)

    def _get_char_icon(self, char, assets_dir) -> QPixmap:
        """取得角色 Icon：優先 Sprite 縮圖，fallback 顏色方塊。"""
        if assets_dir and char.sprites:
            sprite_path = assets_dir / char.sprites[0].filename
            if sprite_path.exists():
                pm = QPixmap(str(sprite_path))
                if not pm.isNull():
                    return pm.scaled(
                        32, 32,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(char.name_color))
        return pixmap

    def _on_char_selection_changed(self, row: int) -> None:
        has_selection = row >= 0
        self.btn_edit_char.setEnabled(has_selection)
        self.btn_remove_char.setEnabled(has_selection)
        if has_selection and self._project and row < len(self._project.characters):
            char = self._project.characters[row]
            self._lbl_char_name.setText(char.name)
            self._lbl_char_color.setStyleSheet(
                f"background-color: {char.name_color}; border: 1px solid #888; border-radius: 3px;"
            )
            pos_map = {"left": "左", "center": "中", "right": "右"}
            self._lbl_char_position.setText(pos_map.get(char.position, char.position))
            self._inspector.setCurrentIndex(2)  # 顯示角色屬性
        else:
            # 角色取消選取時，若場景已選則回到場景屬性
            if self._current_scene_index >= 0:
                self._inspector.setCurrentIndex(1)
            else:
                self._inspector.setCurrentIndex(0)

    def refresh_characters(self) -> None:
        """外部呼叫：重新整理角色列表。"""
        self._refresh_character_list()

    def refresh_scenes(self) -> None:
        """外部呼叫：重新整理場景列表。"""
        self._refresh_scene_list()
