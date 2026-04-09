"""左側面板：場景列表 + 場景屬性 + 角色列表。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ComboBox, LineEdit, ListWidget, PushButton, SegmentedWidget

from src.core.models import Character, Project, Scene

_POS_OPTIONS = ["左", "中", "右"]
_POS_TO_KEY = {"左": "left", "中": "center", "右": "right"}
_KEY_TO_POS = {"left": "左", "center": "中", "right": "右"}

NONE_LABEL = "(無)"
EFFECT_OPTIONS = [NONE_LABEL, "rain", "snow", "crt", "pixel_dark"]


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

        self._btn_del = QPushButton("×")
        self._btn_del.setFixedSize(18, 18)
        self._btn_del.setStyleSheet(
            "QPushButton{border:none;color:#888;background:transparent;"
            "font-size:13px;font-weight:bold;padding:0;}"
            "QPushButton:hover{color:#e05555;}"
        )
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


_DASHED_BTN_STYLE = (
    "QPushButton{border:2px dashed #555;border-radius:4px;color:#888;"
    "background:transparent;padding:4px;}"
    "QPushButton:hover{border-color:#888;color:#bbb;}"
)


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
    character_edit_requested = pyqtSignal(int)   # character index
    character_remove_requested = pyqtSignal(int)
    character_property_changed = pyqtSignal()    # name/color/position edited
    costume_edit_requested = pyqtSignal(int)     # character index

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
        self.scene_list = ListWidget()
        self.scene_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        scene_layout.addWidget(self.scene_list)
        self.btn_add_scene = QPushButton("+ 新增場景")
        self.btn_add_scene.setStyleSheet(_DASHED_BTN_STYLE)
        scene_layout.addWidget(self.btn_add_scene)
        scene_section.setLayout(scene_layout)
        self._list_stack.addWidget(scene_section)

        # Page 1：角色列表
        char_section = QWidget()
        char_layout = QVBoxLayout()
        char_layout.setContentsMargins(0, 0, 0, 0)
        char_layout.setSpacing(4)
        self.character_list = ListWidget()
        self.character_list.setIconSize(QSize(32, 32))
        char_layout.addWidget(self.character_list)
        self.btn_add_char = QPushButton("+ 新增角色")
        self.btn_add_char.setStyleSheet(_DASHED_BTN_STYLE)
        char_layout.addWidget(self.btn_add_char)
        char_section.setLayout(char_layout)
        self._list_stack.addWidget(char_section)

        top_layout.addWidget(self._list_stack)
        top_widget.setLayout(top_layout)

        splitter.addWidget(top_widget)

        # ── 下方：Inspector 屬性面板 ──
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
        self.combo_background = ComboBox()
        self.combo_background.addItem(NONE_LABEL)
        bg_row.addWidget(self.combo_background, 1)
        self.btn_import_bg = PushButton("匯入")
        self.btn_import_bg.setFixedWidth(50)
        bg_row.addWidget(self.btn_import_bg)
        props_layout.addLayout(bg_row)
        bgm_row = QHBoxLayout()
        bgm_row.addWidget(QLabel("BGM:"))
        self.combo_bgm = ComboBox()
        self.combo_bgm.addItem(NONE_LABEL)
        bgm_row.addWidget(self.combo_bgm, 1)
        self.btn_import_music = PushButton("匯入")
        self.btn_import_music.setFixedWidth(50)
        bgm_row.addWidget(self.btn_import_music)
        props_layout.addLayout(bgm_row)
        effect_row = QHBoxLayout()
        effect_row.addWidget(QLabel("特效:"))
        self.combo_effect = ComboBox()
        self.combo_effect.addItems(EFFECT_OPTIONS)
        effect_row.addWidget(self.combo_effect, 1)
        props_layout.addLayout(effect_row)
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
        name_row.addWidget(QLabel("名稱:"))
        self._edit_char_name = LineEdit()
        self._edit_char_name.setPlaceholderText("角色名稱")
        name_row.addWidget(self._edit_char_name, 1)
        char_props_layout.addLayout(name_row)
        # 顏色
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("顏色:"))
        self._lbl_char_color = QLabel()
        self._lbl_char_color.setFixedSize(20, 20)
        self._btn_char_color = PushButton("選色")
        self._btn_char_color.setFixedWidth(50)
        color_row.addWidget(self._lbl_char_color)
        color_row.addWidget(self._btn_char_color)
        color_row.addStretch()
        char_props_layout.addLayout(color_row)
        # 位置
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("位置:"))
        self._combo_char_pos = ComboBox()
        self._combo_char_pos.addItems(_POS_OPTIONS)
        pos_row.addWidget(self._combo_char_pos, 1)
        char_props_layout.addLayout(pos_row)
        # 服裝列表
        char_props_layout.addWidget(QLabel("服裝:"))
        self._char_costume_list = QListWidget()
        self._char_costume_list.setFixedHeight(70)
        char_props_layout.addWidget(self._char_costume_list)
        btn_edit_costume = QPushButton("編輯服裝…")
        btn_edit_costume.setStyleSheet(_DASHED_BTN_STYLE)
        btn_edit_costume.clicked.connect(
            lambda: self.costume_edit_requested.emit(self._current_char_index)
        )
        char_props_layout.addWidget(btn_edit_costume)
        char_props_layout.addStretch()
        char_props.setLayout(char_props_layout)
        self._inspector.addWidget(char_props)
        # 角色屬性連接
        self._edit_char_name.editingFinished.connect(self._on_char_name_changed)
        self._btn_char_color.clicked.connect(self._on_char_color_btn)
        self._combo_char_pos.currentIndexChanged.connect(self._on_char_position_changed)

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
        self.combo_effect.currentIndexChanged.connect(self._on_effect_changed)
        self.btn_import_bg.clicked.connect(self.bg_import_requested.emit)
        self.btn_import_music.clicked.connect(self.music_import_requested.emit)

        self.character_list.currentRowChanged.connect(self._on_char_selection_changed)
        self.btn_add_char.clicked.connect(self.character_add_requested.emit)

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
            effect_val = scene.effect or NONE_LABEL
            idx = self.combo_effect.findText(effect_val)
            self.combo_effect.setCurrentIndex(max(0, idx))
        else:
            self.combo_background.setCurrentIndex(0)
            self.combo_bgm.setCurrentIndex(0)
            self.combo_effect.setCurrentIndex(0)
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

    def _on_effect_changed(self, index: int) -> None:
        if self._updating:
            return
        scene = self._get_current_scene()
        if not scene:
            return
        scene.effect = None if index == 0 else self.combo_effect.currentText()
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
        """由 item widget 的刪除按鈕觸發；場景有對話時先詢問確認。"""
        row = self.scene_list.row(item)
        if row < 0 or not self._project or row >= len(self._project.scenes):
            return
        scene = self._project.scenes[row]
        dlg_count = len(scene.dialogues)
        if dlg_count > 0:
            result = QMessageBox.question(
                self,
                "確認移除場景",
                f"場景「{scene.id}」包含 {dlg_count} 條對話。\n確定要移除？",
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
        self._lbl_char_color.setStyleSheet(
            f"background-color: {char.name_color}; border: 1px solid #888; border-radius: 3px;"
        )
        pos_label = _KEY_TO_POS.get(char.position, "中")
        idx = _POS_OPTIONS.index(pos_label) if pos_label in _POS_OPTIONS else 1
        self._combo_char_pos.setCurrentIndex(idx)
        self._char_costume_list.clear()
        for cos in char.costumes:
            self._char_costume_list.addItem(cos.name)
        self._updating = False

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

    def _on_char_color_btn(self) -> None:
        char = self._get_current_char()
        if not char:
            return
        initial = QColor(char.name_color)
        color = QColorDialog.getColor(initial, self, "選擇名稱顏色")
        if not color.isValid():
            return
        char.name_color = color.name()
        self._lbl_char_color.setStyleSheet(
            f"background-color: {char.name_color}; border: 1px solid #888; border-radius: 3px;"
        )
        # Update icon (color block) in character list
        item = self.character_list.item(self._current_char_index)
        if item:
            widget = self.character_list.itemWidget(item)
            if widget:
                pm = QPixmap(32, 32)
                pm.fill(QColor(char.name_color))
                widget.update_icon(pm)
        self.character_property_changed.emit()

    def _on_char_position_changed(self, _idx: int) -> None:
        if self._updating:
            return
        char = self._get_current_char()
        if not char:
            return
        pos_label = self._combo_char_pos.currentText()
        char.position = _POS_TO_KEY.get(pos_label, "center")
        self.character_property_changed.emit()

    def refresh_costume_list(self) -> None:
        """外部呼叫：重新整理角色屬性面板的服裝列表（服裝編輯後）。"""
        self._refresh_char_props()

    def refresh_characters(self) -> None:
        """外部呼叫：重新整理角色列表。"""
        self._refresh_character_list()

    def refresh_scenes(self) -> None:
        """外部呼叫：重新整理場景列表。"""
        self._refresh_scene_list()
