"""中央-右側面板：預覽（上）+ 對話表格（下）。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import LineEdit, PushButton

from src.core.models import Character, Dialogue, Project, Scene
from src.ui.preview_widget import PreviewWidget

NONE_LABEL = "(無)"
NARRATION_LABEL = "(旁白)"


class _DraggableTable(QTableWidget):
    """自訂拖曳排序的 QTableWidget，不依賴 Qt InternalMove 的 visual/logical 映射。"""

    row_moved = pyqtSignal(int, int)  # (from_row, to_row)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    def startDrag(self, supportedActions):
        """確保拖曳時選中整行。"""
        row = self.currentRow()
        if row >= 0:
            self.selectRow(row)
        super().startDrag(supportedActions)

    def dropEvent(self, event) -> None:
        from_row = self.currentRow()
        to_index = self.indexAt(event.position().toPoint())
        if to_index.isValid():
            to_row = to_index.row()
            rect = self.visualRect(to_index)
            if event.position().toPoint().y() > rect.center().y():
                to_row = min(to_row + 1, self.rowCount() - 1)
        else:
            to_row = self.rowCount() - 1

        if from_row >= 0 and to_row != from_row:
            self.row_moved.emit(from_row, to_row)
        event.accept()

    def mousePressEvent(self, event):
        """點擊空白區域取消選取。"""
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.clearSelection()
            self.setCurrentItem(None)
        super().mousePressEvent(event)


class CenterPanel(QWidget):
    """預覽 + 對話表格，支援行內編輯、搜尋、批次操作。"""

    project_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._project: Project | None = None
        self._current_scene_index: int = -1
        self._updating = False
        self._search_results: list[tuple[int, int]] = []
        self._search_current: int = -1
        self._clipboard_dialogues: list[Dialogue] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── 上半：預覽 ──
        self.preview = PreviewWidget()

        # ── 下半：對話表格 ──
        dialogue_widget = QWidget()
        dialogue_layout = QVBoxLayout()
        dialogue_layout.setContentsMargins(0, 0, 0, 0)

        # 按鈕列
        dlg_header = QHBoxLayout()
        dlg_header.addWidget(QLabel("對話列表"))
        dlg_header.addStretch()
        self.btn_add_dialogue = PushButton("新增")
        self.btn_remove_dialogue = PushButton("移除")
        self.btn_move_up = PushButton("上移")
        self.btn_move_down = PushButton("下移")
        self.btn_remove_dialogue.setEnabled(False)
        self.btn_move_up.setEnabled(False)
        self.btn_move_down.setEnabled(False)
        dlg_header.addWidget(self.btn_add_dialogue)
        dlg_header.addWidget(self.btn_remove_dialogue)
        dlg_header.addWidget(self.btn_move_up)
        dlg_header.addWidget(self.btn_move_down)
        dialogue_layout.addLayout(dlg_header)

        # 搜尋列
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜尋:"))
        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("輸入關鍵字搜尋對話…")
        self.btn_search_prev = PushButton("<")
        self.btn_search_next = PushButton(">")
        self.btn_search_prev.setFixedWidth(30)
        self.btn_search_next.setFixedWidth(30)
        self.lbl_search_count = QLabel("")
        self.btn_search_prev.setEnabled(False)
        self.btn_search_next.setEnabled(False)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.btn_search_prev)
        search_layout.addWidget(self.btn_search_next)
        search_layout.addWidget(self.lbl_search_count)
        dialogue_layout.addLayout(search_layout)

        # 對話表格：6 欄（#、圖示、對話文字、角色、表情、效果）
        self.dialogue_table = _DraggableTable()
        self.dialogue_table.setColumnCount(6)
        self.dialogue_table.setHorizontalHeaderLabels(["#", "", "對話文字", "角色", "表情", "效果"])
        header = self.dialogue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.dialogue_table.setColumnWidth(0, 40)
        self.dialogue_table.setColumnWidth(1, 40)
        self.dialogue_table.setColumnWidth(3, 100)
        self.dialogue_table.setColumnWidth(4, 80)
        self.dialogue_table.setColumnWidth(5, 100)
        self.dialogue_table.verticalHeader().setDefaultSectionSize(48)
        self.dialogue_table.verticalHeader().setVisible(False)
        self.dialogue_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        # 右鍵選單
        self.dialogue_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.dialogue_table.customContextMenuRequested.connect(self._on_context_menu)
        # 鍵盤快捷鍵
        from PyQt6.QtGui import QKeySequence
        act_del = QAction(self.dialogue_table)
        act_del.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        act_del.triggered.connect(self._on_remove_dialogue)
        self.dialogue_table.addAction(act_del)
        act_copy = QAction(self.dialogue_table)
        act_copy.setShortcut(QKeySequence("Ctrl+C"))
        act_copy.triggered.connect(self._on_copy_dialogues)
        self.dialogue_table.addAction(act_copy)
        act_paste = QAction(self.dialogue_table)
        act_paste.setShortcut(QKeySequence("Ctrl+V"))
        act_paste.triggered.connect(self._on_paste_dialogues)
        self.dialogue_table.addAction(act_paste)
        act_paste_text = QAction(self.dialogue_table)
        act_paste_text.setShortcut(QKeySequence("Ctrl+Shift+V"))
        act_paste_text.triggered.connect(self._on_paste_text_to_scene)
        self.dialogue_table.addAction(act_paste_text)

        dialogue_layout.addWidget(self.dialogue_table)
        dialogue_widget.setLayout(dialogue_layout)

        # 預覽容器：工具列 + 預覽元件
        preview_container = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(2)

        preview_toolbar = QHBoxLayout()
        preview_toolbar.addStretch()
        self.btn_refresh_preview = PushButton("重新整理")
        self.btn_game_settings = PushButton("遊戲設定")
        self.btn_refresh_preview.setFixedHeight(24)
        self.btn_game_settings.setFixedHeight(24)
        preview_toolbar.addWidget(self.btn_refresh_preview)
        preview_toolbar.addWidget(self.btn_game_settings)
        preview_layout.addLayout(preview_toolbar)
        preview_layout.addWidget(self.preview)
        preview_container.setLayout(preview_layout)

        splitter.addWidget(preview_container)
        splitter.addWidget(dialogue_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)
        self.setLayout(layout)

        # 信號連接
        self.dialogue_table.cellChanged.connect(self._on_dialogue_edited)
        self.dialogue_table.row_moved.connect(self._on_row_moved)
        self.btn_add_dialogue.clicked.connect(self._on_add_dialogue)
        self.btn_remove_dialogue.clicked.connect(self._on_remove_dialogue)
        self.btn_move_up.clicked.connect(self._on_move_dialogue_up)
        self.btn_move_down.clicked.connect(self._on_move_dialogue_down)
        self.dialogue_table.currentCellChanged.connect(self._on_dialogue_selection_changed)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.btn_search_prev.clicked.connect(self._on_search_prev)
        self.btn_search_next.clicked.connect(self._on_search_next)

    # ── 公開方法 ──

    def set_project(self, project: Project) -> None:
        """綁定 Project。"""
        self._project = project
        self._current_scene_index = 0 if project.scenes else -1
        self._refresh_dialogue_table()

    def set_current_scene(self, index: int) -> None:
        """外部切換場景時呼叫。"""
        self._current_scene_index = index
        self._refresh_dialogue_table()

    def reload_preview(self, project: Project) -> None:
        """重新載入預覽。"""
        self.preview.reload_preview(project)

    def cleanup(self) -> None:
        """清理預覽暫存資源。"""
        self.preview.cleanup()

    def add_dialogues_to_current_scene(
        self, dialogues: list[Dialogue], insert_after: int | None = None
    ) -> None:
        """將解析後的對話加入當前場景。"""
        if not self._project:
            return
        if not self._project.scenes:
            # 由 main_window 負責新增場景
            return
        scene = self._get_current_scene()
        if scene:
            if insert_after is not None and 0 <= insert_after < len(scene.dialogues):
                for i, d in enumerate(dialogues):
                    scene.dialogues.insert(insert_after + 1 + i, d)
            else:
                scene.dialogues.extend(dialogues)
            self._refresh_dialogue_table()
            self.project_changed.emit()

    def get_selected_dialogue_index(self) -> int | None:
        """回傳目前選取的對話索引。"""
        row = self.dialogue_table.currentRow()
        return row if row >= 0 else None

    # ── 對話表格 ──

    def _refresh_dialogue_table(self) -> None:
        """重建對話表格。6 欄：#、圖示、對話文字、角色、表情、效果。"""
        self._updating = True
        self.dialogue_table.setRowCount(0)

        scene = self._get_current_scene()
        if not scene:
            self._updating = False
            return

        self.dialogue_table.setRowCount(len(scene.dialogues))
        for row, dlg in enumerate(scene.dialogues):
            # 欄 0：索引（唯讀）
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setFlags(idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.dialogue_table.setItem(row, 0, idx_item)

            # 欄 1：角色縮圖（唯讀）
            icon_item = QTableWidgetItem()
            icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if dlg.character:
                char_obj = self._find_character(dlg.character)
                if char_obj:
                    pm = self._get_char_thumbnail(char_obj)
                    if pm:
                        icon_item.setIcon(QIcon(pm))
            self.dialogue_table.setItem(row, 1, icon_item)

            # 欄 2：對話文字（可編輯）
            self.dialogue_table.setItem(row, 2, QTableWidgetItem(dlg.text))

            # 欄 3：角色 ComboBox
            char_combo = QComboBox()
            char_combo.addItem(NARRATION_LABEL, None)
            if self._project:
                for c in self._project.characters:
                    char_combo.addItem(c.name, c.name)
            idx = char_combo.findData(dlg.character)
            char_combo.setCurrentIndex(max(0, idx))
            char_combo.currentIndexChanged.connect(
                lambda _, r=row: self._on_char_combo_changed(r)
            )
            self.dialogue_table.setCellWidget(row, 3, char_combo)

            # 欄 4：表情 ComboBox
            sprite_combo = QComboBox()
            sprite_combo.addItem(NONE_LABEL, None)
            if dlg.character:
                char_obj = self._find_character(dlg.character)
                if char_obj:
                    for sv in char_obj.sprites:
                        sprite_combo.addItem(sv.label, sv.label)
            idx = sprite_combo.findData(dlg.sprite)
            sprite_combo.setCurrentIndex(max(0, idx))
            sprite_combo.currentIndexChanged.connect(
                lambda _, r=row: self._on_sprite_combo_changed(r)
            )
            sprite_combo.setEnabled(bool(dlg.character))
            self.dialogue_table.setCellWidget(row, 4, sprite_combo)

            # 欄 5：效果（逗號分隔文字）
            effect_text = ", ".join(dlg.effects) if dlg.effects else ""
            self.dialogue_table.setItem(row, 5, QTableWidgetItem(effect_text))

        self._updating = False

    def _on_dialogue_edited(self, row: int, column: int) -> None:
        if self._updating:
            return
        scene = self._get_current_scene()
        if not scene or row >= len(scene.dialogues):
            return

        dlg = scene.dialogues[row]
        item = self.dialogue_table.item(row, column)
        value = item.text() if item else ""

        if column == 2:  # 對話文字欄
            dlg.text = value
            self.project_changed.emit()
        elif column == 5:  # 效果欄
            dlg.effects = [e.strip() for e in value.split(",") if e.strip()]
            self.project_changed.emit()

    def _on_char_combo_changed(self, row: int) -> None:
        if self._updating:
            return
        scene = self._get_current_scene()
        if not scene or row >= len(scene.dialogues):
            return
        combo = self.dialogue_table.cellWidget(row, 3)
        if not combo:
            return
        char_name = combo.currentData()
        dlg = scene.dialogues[row]
        dlg.character = char_name
        dlg.type = "dialogue" if char_name else "narration"
        if not char_name:
            dlg.sprite = None

        # 只更新該行的 sprite combo，不重建整個表格
        self._updating = True
        sprite_combo = self.dialogue_table.cellWidget(row, 4)
        if sprite_combo:
            sprite_combo.blockSignals(True)
            sprite_combo.clear()
            sprite_combo.addItem(NONE_LABEL, None)
            if char_name:
                char_obj = self._find_character(char_name)
                if char_obj:
                    for sv in char_obj.sprites:
                        sprite_combo.addItem(sv.label, sv.label)
            sprite_combo.setEnabled(bool(char_name))
            sprite_combo.blockSignals(False)

        # 更新圖示欄
        icon_item = self.dialogue_table.item(row, 1)
        if icon_item:
            if char_name:
                char_obj = self._find_character(char_name)
                pm = self._get_char_thumbnail(char_obj) if char_obj else None
                icon_item.setIcon(QIcon(pm) if pm else QIcon())
            else:
                icon_item.setIcon(QIcon())
        self._updating = False

        self.project_changed.emit()

    def _on_sprite_combo_changed(self, row: int) -> None:
        if self._updating:
            return
        scene = self._get_current_scene()
        if not scene or row >= len(scene.dialogues):
            return
        combo = self.dialogue_table.cellWidget(row, 4)
        if not combo:
            return
        scene.dialogues[row].sprite = combo.currentData()
        self.project_changed.emit()

    def _get_char_thumbnail(self, char: Character) -> QPixmap | None:
        """取得角色 32x32 縮圖。"""
        if not self._project or not self._project.project_path:
            return None
        assets_dir = self._project.project_path.parent / "assets"
        if char.sprites:
            path = assets_dir / char.sprites[0].filename
            if path.exists():
                pm = QPixmap(str(path))
                if not pm.isNull():
                    return pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        # fallback: 角色名稱顏色色塊
        pm = QPixmap(32, 32)
        pm.fill(QColor(char.name_color))
        return pm

    # ── 對話操作 ──

    def _on_dialogue_selection_changed(
        self, row: int, _col: int, _prev_row: int, _prev_col: int
    ) -> None:
        scene = self._get_current_scene()
        has_scene = scene is not None
        has_selection = row >= 0 and has_scene and row < len(scene.dialogues)
        self.btn_remove_dialogue.setEnabled(has_selection)
        self.btn_move_up.setEnabled(has_selection and row > 0)
        self.btn_move_down.setEnabled(
            has_selection and row < len(scene.dialogues) - 1
        )
        # 跳轉預覽到選取的台詞
        if has_selection:
            self.preview.jump_to_dialogue(self._current_scene_index, row)

    def _on_add_dialogue(self) -> None:
        if not self._project or not self._project.scenes:
            return
        scene = self._get_current_scene()
        if not scene:
            return
        scene.dialogues.append(Dialogue(type="narration", text=""))
        self._refresh_dialogue_table()
        last_row = len(scene.dialogues) - 1
        self.dialogue_table.setCurrentCell(last_row, 2)
        self.dialogue_table.editItem(self.dialogue_table.item(last_row, 2))
        self.project_changed.emit()

    def _on_remove_dialogue(self) -> None:
        scene = self._get_current_scene()
        row = self.dialogue_table.currentRow()
        if not scene or row < 0 or row >= len(scene.dialogues):
            return
        scene.dialogues.pop(row)
        self._refresh_dialogue_table()
        self.project_changed.emit()

    def _on_move_dialogue_up(self) -> None:
        scene = self._get_current_scene()
        row = self.dialogue_table.currentRow()
        if not scene or row <= 0:
            return
        scene.dialogues[row - 1], scene.dialogues[row] = (
            scene.dialogues[row],
            scene.dialogues[row - 1],
        )
        self._refresh_dialogue_table()
        self.dialogue_table.setCurrentCell(row - 1, 0)
        self.project_changed.emit()

    def _on_move_dialogue_down(self) -> None:
        scene = self._get_current_scene()
        row = self.dialogue_table.currentRow()
        if not scene or row < 0 or row >= len(scene.dialogues) - 1:
            return
        scene.dialogues[row], scene.dialogues[row + 1] = (
            scene.dialogues[row + 1],
            scene.dialogues[row],
        )
        self._refresh_dialogue_table()
        self.dialogue_table.setCurrentCell(row + 1, 0)
        self.project_changed.emit()

    # ── 拖曳排序 ──

    def _on_row_moved(self, from_row: int, to_row: int) -> None:
        """拖曳信號：直接操作 scene.dialogues 並重繪。"""
        scene = self._get_current_scene()
        if not scene or self._updating:
            return
        if from_row < 0 or from_row >= len(scene.dialogues):
            return
        to_row = max(0, min(to_row, len(scene.dialogues) - 1))
        dlg = scene.dialogues.pop(from_row)
        scene.dialogues.insert(to_row, dlg)
        self._refresh_dialogue_table()
        self.dialogue_table.setCurrentCell(to_row, 0)
        self.project_changed.emit()

    # ── 右鍵選單 ──

    def _on_context_menu(self, pos) -> None:
        """對話表格右鍵選單（完整操作集）。"""
        scene = self._get_current_scene()
        if not scene or not self._project:
            return
        row = self.dialogue_table.rowAt(pos.y())
        has_row = 0 <= row < len(scene.dialogues)

        menu = QMenu(self)

        act_del = menu.addAction("刪除", self._on_remove_dialogue)
        act_del.setEnabled(has_row)
        menu.addSeparator()
        act_copy = menu.addAction("複製", self._on_copy_dialogues)
        act_copy.setEnabled(has_row)
        act_paste = menu.addAction("貼上", self._on_paste_dialogues)
        act_paste.setEnabled(bool(self._clipboard_dialogues))
        menu.addAction("貼上文字", self._on_paste_text_to_scene)
        menu.addSeparator()
        act_up = menu.addAction("上移", self._on_move_dialogue_up)
        act_up.setEnabled(has_row and row > 0)
        act_down = menu.addAction("下移", self._on_move_dialogue_down)
        act_down.setEnabled(has_row and row < len(scene.dialogues) - 1)
        menu.addSeparator()
        menu.addAction("指定角色", self._on_batch_assign)
        # 移動到場景子選單
        if has_row and len(self._project.scenes) > 1:
            menu.addSeparator()
            move_menu = menu.addMenu("移動到場景…")
            for i, target_scene in enumerate(self._project.scenes):
                if i == self._current_scene_index:
                    continue
                action = move_menu.addAction(target_scene.id)
                action.setData(i)
                action.triggered.connect(
                    lambda checked, target_idx=i, src_row=row: self._move_dialogue_to_scene(
                        src_row, target_idx
                    )
                )

        menu.exec(self.dialogue_table.viewport().mapToGlobal(pos))

    def _move_dialogue_to_scene(self, row: int, target_scene_index: int) -> None:
        """將指定行的對話移動到目標場景末尾。"""
        scene = self._get_current_scene()
        if not scene or not self._project:
            return
        if row < 0 or row >= len(scene.dialogues):
            return
        if target_scene_index < 0 or target_scene_index >= len(self._project.scenes):
            return

        dialogue = scene.dialogues.pop(row)
        self._project.scenes[target_scene_index].dialogues.append(dialogue)
        self._refresh_dialogue_table()
        self.project_changed.emit()

    # ── 複製 / 貼上 ──

    def _on_copy_dialogues(self) -> None:
        """複製選中台詞到內部剪貼簿。"""
        import copy
        scene = self._get_current_scene()
        if not scene:
            return
        selected_rows = sorted(
            {idx.row() for idx in self.dialogue_table.selectionModel().selectedRows()}
        )
        self._clipboard_dialogues = [
            copy.deepcopy(scene.dialogues[r])
            for r in selected_rows
            if r < len(scene.dialogues)
        ]

    def _on_paste_dialogues(self) -> None:
        """將內部剪貼簿的台詞貼到當前選取行之後。"""
        import copy
        scene = self._get_current_scene()
        if not scene or not self._clipboard_dialogues:
            return
        insert_after = self.dialogue_table.currentRow()
        if insert_after < 0:
            insert_after = len(scene.dialogues) - 1
        for i, dlg in enumerate(self._clipboard_dialogues):
            scene.dialogues.insert(insert_after + 1 + i, copy.deepcopy(dlg))
        self._refresh_dialogue_table()
        self.dialogue_table.setCurrentCell(insert_after + len(self._clipboard_dialogues), 2)
        self.project_changed.emit()

    def _on_paste_text_to_scene(self) -> None:
        """開啟貼上文字對話框，將文字解析為台詞加入當前場景。"""
        from src.ui.dialogs import PasteTextDialog
        from src.core.text_parser import _classify_lines

        dlg = PasteTextDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        text = dlg.get_text()
        lines = text.splitlines()
        new_dialogues = _classify_lines(lines)
        if not new_dialogues:
            return
        insert_after = self.dialogue_table.currentRow() if dlg.is_insert_mode() else None
        self.add_dialogues_to_current_scene(new_dialogues, insert_after=insert_after)

    # ── 批次角色指定 ──

    def _on_batch_assign(self) -> None:
        scene = self._get_current_scene()
        if not scene:
            return
        selected_rows = sorted(
            {idx.row() for idx in self.dialogue_table.selectionModel().selectedRows()}
        )
        if not selected_rows:
            return

        from src.ui.dialogs import BatchAssignDialog

        sprites = self._project.assets.get("sprites", []) if self._project else []
        dlg = BatchAssignDialog(sprites, self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        character, sprite = dlg.get_values()
        for row in selected_rows:
            if row < len(scene.dialogues):
                d = scene.dialogues[row]
                if character is not None:
                    d.character = character or None
                    # 同步更新 type
                    d.type = "dialogue" if character else "narration"
                if sprite is not None:
                    d.sprite = sprite or None

        self._refresh_dialogue_table()
        self.project_changed.emit()

    # ── 搜尋 ──

    def _on_search_text_changed(self, text: str) -> None:
        self._search_results = []
        self._search_current = -1

        if not text or not self._project:
            self._clear_search_highlight()
            self.lbl_search_count.setText("")
            self.btn_search_prev.setEnabled(False)
            self.btn_search_next.setEnabled(False)
            return

        keyword = text.lower()
        for si, scene in enumerate(self._project.scenes):
            for di, dlg in enumerate(scene.dialogues):
                if keyword in dlg.text.lower() or (
                    dlg.character and keyword in dlg.character.lower()
                ):
                    self._search_results.append((si, di))

        count = len(self._search_results)
        if count > 0:
            self._search_current = 0
            self._goto_search_result()
            self.lbl_search_count.setText(f"1 / {count}")
        else:
            self.lbl_search_count.setText("無結果")
            self._clear_search_highlight()

        self.btn_search_prev.setEnabled(count > 1)
        self.btn_search_next.setEnabled(count > 1)

    def _on_search_next(self) -> None:
        if not self._search_results:
            return
        self._search_current = (self._search_current + 1) % len(self._search_results)
        self._goto_search_result()

    def _on_search_prev(self) -> None:
        if not self._search_results:
            return
        self._search_current = (self._search_current - 1) % len(self._search_results)
        self._goto_search_result()

    def _goto_search_result(self) -> None:
        si, di = self._search_results[self._search_current]
        total = len(self._search_results)
        self.lbl_search_count.setText(f"{self._search_current + 1} / {total}")

        # 切換場景
        if si != self._current_scene_index:
            # 通知外部切換場景
            self._current_scene_index = si
            self._refresh_dialogue_table()

        self.dialogue_table.setCurrentCell(di, 2)
        self._highlight_search_matches()

    def _highlight_search_matches(self) -> None:
        self._clear_search_highlight()
        keyword = self.search_input.text().lower()
        if not keyword:
            return

        highlight_color = QColor(255, 255, 100, 80)
        current_color = QColor(255, 200, 50, 150)

        for si, di in self._search_results:
            if si != self._current_scene_index:
                continue
            is_current = (si, di) == self._search_results[self._search_current]
            color = current_color if is_current else highlight_color
            for col in range(self.dialogue_table.columnCount()):
                item = self.dialogue_table.item(di, col)
                if item:
                    item.setBackground(color)

    def _clear_search_highlight(self) -> None:
        for row in range(self.dialogue_table.rowCount()):
            for col in range(self.dialogue_table.columnCount()):
                item = self.dialogue_table.item(row, col)
                if item:
                    item.setBackground(QColor(0, 0, 0, 0))

    # ── 工具方法 ──

    def _get_current_scene(self) -> Scene | None:
        if (
            not self._project
            or self._current_scene_index < 0
            or self._current_scene_index >= len(self._project.scenes)
        ):
            return None
        return self._project.scenes[self._current_scene_index]

    def _find_character(self, name: str) -> Character | None:
        """從 Project.characters 中查找角色。"""
        if not self._project:
            return None
        for c in self._project.characters:
            if c.name == name:
                return c
        return None
