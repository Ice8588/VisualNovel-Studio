"""中央-右側面板：預覽（上）+ 對話表格（下）。"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QKeySequence, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QSplitter,
    QStyledItemDelegate,
    QStyle,
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

# 半透明 ComboBox：平時低調，hover/focus 顯示邊框
_COMBO_STYLE = (
    "QComboBox{border:none;background:transparent;padding:1px 4px;}"
    "QComboBox:hover,QComboBox:focus{"
    "border:1px solid #555;background:#2a2a2a;border-radius:3px;}"
    "QComboBox::drop-down{border:none;width:14px;}"
    "QComboBox QAbstractItemView{border:1px solid #555;background:#1e1e1e;"
    "selection-background-color:#0057b8;outline:none;}"
)


class _MultilineDelegate(QStyledItemDelegate):
    """台詞欄 delegate：用 QPlainTextEdit 允許 Enter 換行。"""

    def createEditor(self, parent, option, index):
        editor = QPlainTextEdit(parent)
        return editor

    def setEditorData(self, editor: QPlainTextEdit, index) -> None:
        editor.setPlainText(index.data(Qt.ItemDataRole.EditRole) or "")

    def setModelData(self, editor: QPlainTextEdit, model, index) -> None:
        model.setData(index, editor.toPlainText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        rect = option.rect
        if rect.height() < 72:
            rect.setHeight(72)
        editor.setGeometry(rect)


class _IndexDelegate(QStyledItemDelegate):
    """索引欄 delegate：hover 行顯示 ▶ 提示可跳轉預覽。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_row: int = -1

    def paint(self, painter, option, index) -> None:
        if index.row() == self._hovered_row:
            painter.save()
            selected = bool(option.state & QStyle.StateFlag.State_Selected)
            if selected:
                painter.fillRect(option.rect, option.palette.highlight())
                painter.setPen(option.palette.highlightedText().color())
            else:
                painter.fillRect(option.rect, option.palette.base())
                painter.setPen(option.palette.text().color())
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "▶")
            painter.restore()
        else:
            super().paint(painter, option, index)


class _HoverFilter(QObject):
    """Viewport event filter：追蹤滑鼠 hover 行，通知 IndexDelegate 重繪。"""

    def __init__(self, table: QTableWidget, delegate: _IndexDelegate):
        super().__init__(table)
        self._table = table
        self._delegate = delegate
        table.viewport().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if obj is self._table.viewport():
            if event.type() == QEvent.Type.MouseMove:
                row = self._table.rowAt(event.position().toPoint().y())
                if row != self._delegate._hovered_row:
                    self._delegate._hovered_row = row
                    self._table.viewport().update()
            elif event.type() == QEvent.Type.Leave:
                if self._delegate._hovered_row != -1:
                    self._delegate._hovered_row = -1
                    self._table.viewport().update()
        return False


class _BatchToolbar(QWidget):
    """多選 ≥2 行時浮現的批次操作列。"""

    batch_assign = pyqtSignal()
    batch_delete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(6, 2, 6, 2)
        self._lbl = QLabel("已選取 0 行")
        layout.addWidget(self._lbl)
        layout.addStretch()
        btn_assign = PushButton("批次指定角色")
        btn_assign.clicked.connect(self.batch_assign)
        layout.addWidget(btn_assign)
        btn_del = PushButton("刪除選取")
        btn_del.clicked.connect(self.batch_delete)
        layout.addWidget(btn_del)
        self.setLayout(layout)
        self.hide()

    def update_count(self, n: int) -> None:
        self._lbl.setText(f"已選取 {n} 行")
        self.setVisible(n >= 2)


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

        # 批次操作列（多選 ≥2 顯示）
        self._batch_toolbar = _BatchToolbar()
        self._batch_toolbar.batch_assign.connect(self._on_batch_assign)
        self._batch_toolbar.batch_delete.connect(self._on_batch_delete_selected)
        dialogue_layout.addWidget(self._batch_toolbar)

        # 對話表格：6 欄（#、台詞、角色、服裝、表情、效果）
        self.dialogue_table = _DraggableTable()
        self.dialogue_table.setColumnCount(6)
        self.dialogue_table.setHorizontalHeaderLabels(
            ["#", "台詞", "角色", "服裝", "表情", "效果"]
        )
        header = self.dialogue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.dialogue_table.setColumnWidth(0, 40)
        self.dialogue_table.setColumnWidth(2, 100)
        self.dialogue_table.setColumnWidth(3, 90)
        self.dialogue_table.setColumnWidth(4, 90)
        self.dialogue_table.setColumnWidth(5, 100)
        self.dialogue_table.verticalHeader().setDefaultSectionSize(40)
        self.dialogue_table.verticalHeader().setVisible(False)
        self.dialogue_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        # 索引欄 delegate + hover filter
        self._index_delegate = _IndexDelegate()
        self.dialogue_table.setItemDelegateForColumn(0, self._index_delegate)
        self._hover_filter = _HoverFilter(self.dialogue_table, self._index_delegate)

        # 台詞欄 multiline delegate
        self._multiline_delegate = _MultilineDelegate()
        self.dialogue_table.setItemDelegateForColumn(1, self._multiline_delegate)

        # 右鍵選單
        self.dialogue_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.dialogue_table.customContextMenuRequested.connect(self._on_context_menu)

        # 鍵盤快捷鍵
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

        # Preview bridge：自動播放同步表格高亮
        self.preview.bridge.dialogue_advanced.connect(self._on_preview_dialogue_advanced)

        # 信號連接
        self.dialogue_table.cellChanged.connect(self._on_dialogue_edited)
        self.dialogue_table.row_moved.connect(self._on_row_moved)
        self.btn_add_dialogue.clicked.connect(self._on_add_dialogue)
        self.btn_remove_dialogue.clicked.connect(self._on_remove_dialogue)
        self.btn_move_up.clicked.connect(self._on_move_dialogue_up)
        self.btn_move_down.clicked.connect(self._on_move_dialogue_down)
        self.dialogue_table.currentCellChanged.connect(self._on_dialogue_selection_changed)
        self.dialogue_table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
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
        """重建對話表格。6 欄：#、台詞、角色、服裝、表情、效果。"""
        self._updating = True
        self.dialogue_table.clearSpans()
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

            # 欄 1：台詞（可編輯，multiline delegate）
            self.dialogue_table.setItem(row, 1, QTableWidgetItem(dlg.text))

            # 欄 2：角色 ComboBox（所有行都有）
            char_combo = QComboBox()
            char_combo.setStyleSheet(_COMBO_STYLE)
            char_combo.addItem(NARRATION_LABEL, None)
            if self._project:
                for c in self._project.characters:
                    char_combo.addItem(c.name, c.name)
            idx = char_combo.findData(dlg.character)
            char_combo.setCurrentIndex(max(0, idx))
            char_combo.currentIndexChanged.connect(
                lambda _, r=row: self._on_char_combo_changed(r)
            )
            self.dialogue_table.setCellWidget(row, 2, char_combo)

            if dlg.character:
                # 對話行：服裝 + 表情 ComboBox
                char_obj = self._find_character(dlg.character)

                costume_combo = QComboBox()
                costume_combo.setStyleSheet(_COMBO_STYLE)
                costume_combo.addItem(NONE_LABEL, None)
                if char_obj:
                    for cos in char_obj.costumes:
                        costume_combo.addItem(cos.name, cos.name)
                idx = costume_combo.findData(dlg.costume)
                costume_combo.setCurrentIndex(max(0, idx))
                costume_combo.currentIndexChanged.connect(
                    lambda _, r=row: self._on_costume_combo_changed(r)
                )
                self.dialogue_table.setCellWidget(row, 3, costume_combo)

                sprite_combo = QComboBox()
                sprite_combo.setStyleSheet(_COMBO_STYLE)
                sprite_combo.addItem(NONE_LABEL, None)
                if char_obj:
                    selected_cos = self._find_costume(char_obj, dlg.costume)
                    if selected_cos:
                        for sv in selected_cos.expressions:
                            sprite_combo.addItem(sv.label, sv.label)
                idx = sprite_combo.findData(dlg.sprite)
                sprite_combo.setCurrentIndex(max(0, idx))
                sprite_combo.currentIndexChanged.connect(
                    lambda _, r=row: self._on_sprite_combo_changed(r)
                )
                self.dialogue_table.setCellWidget(row, 4, sprite_combo)
            else:
                # 旁白行：欄 3-4 合併顯示 "—"
                narr_item = QTableWidgetItem("—")
                narr_item.setFlags(narr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                narr_item.setForeground(QColor("#555"))
                narr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.dialogue_table.setItem(row, 3, narr_item)
                self.dialogue_table.setSpan(row, 3, 1, 2)

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

        if column == 1:  # 台詞欄
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
        combo = self.dialogue_table.cellWidget(row, 2)
        if not combo:
            return
        char_name = combo.currentData()
        dlg = scene.dialogues[row]
        was_dialogue = bool(dlg.character)
        dlg.character = char_name
        dlg.type = "dialogue" if char_name else "narration"
        dlg.sprite = None
        dlg.costume = None
        is_dialogue = bool(char_name)

        if was_dialogue != is_dialogue:
            # 類型改變：需要全部重建（span / cellWidget 增刪）
            self._refresh_dialogue_table()
            self.project_changed.emit()
            return

        if is_dialogue:
            # 對話→對話（角色切換）：更新服裝和表情 combo
            self._updating = True
            costume_combo = self.dialogue_table.cellWidget(row, 3)
            if costume_combo:
                costume_combo.blockSignals(True)
                costume_combo.clear()
                costume_combo.addItem(NONE_LABEL, None)
                char_obj = self._find_character(char_name)
                if char_obj:
                    for cos in char_obj.costumes:
                        costume_combo.addItem(cos.name, cos.name)
                costume_combo.blockSignals(False)
            sprite_combo = self.dialogue_table.cellWidget(row, 4)
            if sprite_combo:
                sprite_combo.blockSignals(True)
                sprite_combo.clear()
                sprite_combo.addItem(NONE_LABEL, None)
                sprite_combo.blockSignals(False)
            self._updating = False

        self.project_changed.emit()

    def _on_costume_combo_changed(self, row: int) -> None:
        if self._updating:
            return
        scene = self._get_current_scene()
        if not scene or row >= len(scene.dialogues):
            return
        combo = self.dialogue_table.cellWidget(row, 3)
        if not combo:
            return
        costume_name = combo.currentData()
        dlg = scene.dialogues[row]
        dlg.costume = costume_name
        dlg.sprite = None

        self._updating = True
        sprite_combo = self.dialogue_table.cellWidget(row, 4)
        if sprite_combo:
            sprite_combo.blockSignals(True)
            sprite_combo.clear()
            sprite_combo.addItem(NONE_LABEL, None)
            if costume_name and dlg.character:
                char_obj = self._find_character(dlg.character)
                if char_obj:
                    cos = self._find_costume(char_obj, costume_name)
                    if cos:
                        for sv in cos.expressions:
                            sprite_combo.addItem(sv.label, sv.label)
            sprite_combo.blockSignals(False)
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
        if has_selection:
            self.preview.jump_to_dialogue(self._current_scene_index, row)

    def _on_selection_changed(self) -> None:
        """選取行數變化：更新批次工具列。"""
        n = len(self.dialogue_table.selectionModel().selectedRows())
        self._batch_toolbar.update_count(n)

    def _on_add_dialogue(self) -> None:
        if not self._project or not self._project.scenes:
            return
        scene = self._get_current_scene()
        if not scene:
            return
        scene.dialogues.append(Dialogue(type="narration", text=""))
        self._refresh_dialogue_table()
        last_row = len(scene.dialogues) - 1
        self.dialogue_table.setCurrentCell(last_row, 1)
        self.dialogue_table.editItem(self.dialogue_table.item(last_row, 1))
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
        self.dialogue_table.setCurrentCell(insert_after + len(self._clipboard_dialogues), 1)
        self.project_changed.emit()

    def _on_paste_text_to_scene(self) -> None:
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

    # ── 批次操作 ──

    def _on_batch_assign(self) -> None:
        scene = self._get_current_scene()
        if not scene:
            return
        selected_rows = sorted(
            {idx.row() for idx in self.dialogue_table.selectionModel().selectedRows()}
        )
        if not selected_rows:
            row = self.dialogue_table.currentRow()
            if row >= 0:
                selected_rows = [row]
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
                    d.type = "dialogue" if character else "narration"
                if sprite is not None:
                    d.sprite = sprite or None

        self._refresh_dialogue_table()
        self.project_changed.emit()

    def _on_batch_delete_selected(self) -> None:
        """批次刪除選取行。"""
        scene = self._get_current_scene()
        if not scene:
            return
        selected_rows = sorted(
            {idx.row() for idx in self.dialogue_table.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in selected_rows:
            if 0 <= row < len(scene.dialogues):
                scene.dialogues.pop(row)
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

        if si != self._current_scene_index:
            self._current_scene_index = si
            self._refresh_dialogue_table()

        self.dialogue_table.setCurrentCell(di, 1)
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

    # ── Preview 雙向同步 ──

    def _on_preview_dialogue_advanced(self, scene_idx: int, dlg_idx: int) -> None:
        if self._updating:
            return
        if self.dialogue_table.state() == QAbstractItemView.State.EditingState:
            return
        if scene_idx != self._current_scene_index:
            return
        scene = self._get_current_scene()
        if not scene or dlg_idx < 0 or dlg_idx >= len(scene.dialogues):
            return
        self._updating = True
        self.dialogue_table.setCurrentCell(dlg_idx, 0)
        item = self.dialogue_table.item(dlg_idx, 0)
        if item:
            self.dialogue_table.scrollToItem(
                item, QAbstractItemView.ScrollHint.EnsureVisible
            )
        self._updating = False

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
        if not self._project:
            return None
        for c in self._project.characters:
            if c.name == name:
                return c
        return None

    @staticmethod
    def _find_costume(char: Character, costume_name: str | None):
        """找到角色指定服裝，若無則回傳第一個，仍無則 None。"""
        if not char.costumes:
            return None
        if costume_name:
            for cos in char.costumes:
                if cos.name == costume_name:
                    return cos
        return char.costumes[0]
