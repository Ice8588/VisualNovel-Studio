"""檔案對話框包裝：文字、圖片、音訊匯入對話框、影片導出設定、貼上文字、角色編輯。"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ComboBox, LineEdit, PushButton

from src.core.models import Character, Costume, SpriteVariant


def open_text_file(parent: QWidget) -> Path | None:
    """開啟文字檔案對話框，回傳選取的檔案路徑。"""
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "匯入文字檔案",
        "",
        "文字檔案 (*.txt *.docx);;所有檔案 (*)",
    )
    return Path(path) if path else None


def open_image_files(parent: QWidget) -> list[Path]:
    """開啟圖片檔案對話框（可多選），回傳檔案路徑列表。"""
    paths, _ = QFileDialog.getOpenFileNames(
        parent,
        "匯入圖片",
        "",
        "圖片檔案 (*.png *.jpg *.jpeg);;所有檔案 (*)",
    )
    return [Path(p) for p in paths]


def open_audio_files(parent: QWidget) -> list[Path]:
    """開啟音訊檔案對話框（可多選），回傳檔案路徑列表。"""
    paths, _ = QFileDialog.getOpenFileNames(
        parent,
        "匯入音樂",
        "",
        "音訊檔案 (*.mp3 *.wav);;所有檔案 (*)",
    )
    return [Path(p) for p in paths]


def save_project_dialog(parent: QWidget) -> Path | None:
    """另存專案對話框，回傳儲存路徑。"""
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "儲存專案",
        "",
        "VisualNovel 專案 (*.vnsproj)",
    )
    return Path(path) if path else None


def open_project_dialog(parent: QWidget) -> Path | None:
    """開啟專案對話框，回傳檔案路徑。"""
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "開啟專案",
        "",
        "VisualNovel 專案 (*.vnsproj);;所有檔案 (*)",
    )
    return Path(path) if path else None


def export_zip_dialog(parent: QWidget) -> Path | None:
    """導出 ZIP 對話框，回傳儲存路徑。"""
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "導出網頁",
        "",
        "ZIP 壓縮檔 (*.zip)",
    )
    return Path(path) if path else None


def show_error(parent: QWidget, title: str, message: str) -> None:
    """顯示錯誤訊息對話框。"""
    QMessageBox.critical(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    """顯示資訊訊息對話框。"""
    QMessageBox.information(parent, title, message)


# ── 影片導出設定對話框 ──

RESOLUTION_OPTIONS = {
    "1920 × 1080 (Full HD)": (1920, 1080),
    "1280 × 720 (HD)": (1280, 720),
    "3840 × 2160 (4K)": (3840, 2160),
}


class VideoExportDialog(QDialog):
    """影片導出設定對話框。"""

    def __init__(self, project, parent: QWidget | None = None):
        super().__init__(parent)
        self._project = project
        self.setWindowTitle("導出影片 (MP4)")
        self.setMinimumWidth(420)
        self._setup_ui()
        self._check_ffmpeg()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        form = QFormLayout()

        # 解析度
        self.combo_resolution = ComboBox()
        self.combo_resolution.addItems(RESOLUTION_OPTIONS.keys())
        form.addRow("解析度:", self.combo_resolution)

        # 停留時間說明
        lbl_duration = QLabel("停留時間依字數自動計算（1.5～8 秒）")
        lbl_duration.setStyleSheet("color: #888;")
        form.addRow("停留時間:", lbl_duration)

        # 輸出路徑
        path_layout = QHBoxLayout()
        self.edit_path = LineEdit()
        self.edit_path.setPlaceholderText("選擇輸出路徑…")
        btn_browse = PushButton("瀏覽…")
        btn_browse.clicked.connect(self._browse_output)
        path_layout.addWidget(self.edit_path, 1)
        path_layout.addWidget(btn_browse)
        form.addRow("輸出路徑:", path_layout)

        layout.addLayout(form)

        # ffmpeg 警告
        self.lbl_ffmpeg_warning = QLabel()
        self.lbl_ffmpeg_warning.setStyleSheet("color: red;")
        self.lbl_ffmpeg_warning.setWordWrap(True)
        self.lbl_ffmpeg_warning.hide()
        layout.addWidget(self.lbl_ffmpeg_warning)

        # 按鈕
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "輸出影片", "", "MP4 影片 (*.mp4)"
        )
        if path:
            self.edit_path.setText(path)

    def _check_ffmpeg(self) -> None:
        from src.core.ffmpeg_manager import is_available
        if not is_available():
            self.lbl_ffmpeg_warning.setText(
                "ℹ 尚未安裝 FFmpeg，點擊確定後將自動下載。"
            )
            self.lbl_ffmpeg_warning.setStyleSheet("color: #e0a020;")
            self.lbl_ffmpeg_warning.show()

    def _validate_and_accept(self) -> None:
        if not self.edit_path.text().strip():
            QMessageBox.warning(self, "缺少路徑", "請指定輸出路徑。")
            return
        self.accept()

    def get_settings(self) -> dict:
        res_key = self.combo_resolution.currentText()
        return {
            "resolution": RESOLUTION_OPTIONS[res_key],
            "output_path": Path(self.edit_path.text()),
        }


# ── 批次角色指定對話框 ──

NONE_LABEL = "(不變更)"


class BatchAssignDialog(QDialog):
    """批次指定角色名稱與立繪。留空欄位表示不變更。"""

    def __init__(self, sprites: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("批次指定角色")
        self.setMinimumWidth(350)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("勾選要變更的欄位，未勾選的欄位將保持不變。"))

        form = QFormLayout()

        # 角色名稱
        char_row = QHBoxLayout()
        self.chk_character = QCheckBox("變更")
        self.chk_character.setChecked(True)
        self.edit_character = LineEdit()
        self.edit_character.setPlaceholderText("輸入角色名稱（留空清除）")
        char_row.addWidget(self.chk_character)
        char_row.addWidget(self.edit_character, 1)
        form.addRow("角色:", char_row)

        # 立繪
        sprite_row = QHBoxLayout()
        self.chk_sprite = QCheckBox("變更")
        self.chk_sprite.setChecked(False)
        self.combo_sprite = ComboBox()
        self.combo_sprite.addItem("(無)")
        self.combo_sprite.addItems(sprites)
        self.combo_sprite.setEnabled(False)
        sprite_row.addWidget(self.chk_sprite)
        sprite_row.addWidget(self.combo_sprite, 1)
        form.addRow("立繪:", sprite_row)

        layout.addLayout(form)

        self.chk_character.toggled.connect(self.edit_character.setEnabled)
        self.chk_sprite.toggled.connect(self.combo_sprite.setEnabled)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_values(self) -> tuple[str | None, str | None]:
        """回傳 (character, sprite)。None 表示該欄位不變更。"""
        character = None
        if self.chk_character.isChecked():
            character = self.edit_character.text().strip()

        sprite = None
        if self.chk_sprite.isChecked():
            text = self.combo_sprite.currentText()
            sprite = "" if text == "(無)" else text

        return character, sprite


# ── 貼上文字對話框 ──


class PasteTextDialog(QDialog):
    """貼上純文字並解析為對話/旁白。支援加到末尾或插入到選取位置之後。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("貼上文字")
        self.setMinimumSize(500, 400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        layout.addWidget(QLabel("將文字貼到下方區域，系統會自動辨識台詞與旁白："))

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            "在此貼上文字…\n\n"
            "判斷規則：\n"
            "  ‧ 以「」包圍的整行 → 台詞\n"
            "  ‧ 其他 → 旁白\n"
            "  ‧ 空行自動略過"
        )
        layout.addWidget(self.text_edit, 1)

        # 插入位置選項
        position_group = QGroupBox("插入位置")
        position_layout = QVBoxLayout()
        self.radio_append = QRadioButton("加到末尾")
        self.radio_insert = QRadioButton("插入到選取位置之後")
        self.radio_append.setChecked(True)
        position_layout.addWidget(self.radio_append)
        position_layout.addWidget(self.radio_insert)
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        # 按鈕
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _validate_and_accept(self) -> None:
        if not self.text_edit.toPlainText().strip():
            QMessageBox.warning(self, "無內容", "請先貼上文字。")
            return
        self.accept()

    def get_text(self) -> str:
        """回傳使用者貼上的原始文字。"""
        return self.text_edit.toPlainText()

    def is_insert_mode(self) -> bool:
        """回傳 True 表示插入到選取位置之後，False 表示加到末尾。"""
        return self.radio_insert.isChecked()


# ── 角色編輯對話框 ──

POSITION_OPTIONS = {"左": "left", "中": "center", "右": "right"}
POSITION_LABELS = {v: k for k, v in POSITION_OPTIONS.items()}


class CharacterEditorDialog(QDialog):
    """新增或編輯角色：名稱、顏色、位置、表情差分列表。"""

    def __init__(
        self,
        character: Character | None = None,
        project_dir: Path | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._original = character
        self._project_dir = project_dir or Path(tempfile.gettempdir()) / "vnstudio_unsaved"
        self.setWindowTitle("編輯角色" if character else "新增角色")
        self.setMinimumWidth(480)
        self._setup_ui()
        if character:
            self._load_character(character)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        form = QFormLayout()

        # 名稱
        self.edit_name = LineEdit()
        self.edit_name.setPlaceholderText("角色名稱")
        form.addRow("名稱:", self.edit_name)

        # 名稱顏色
        color_row = QHBoxLayout()
        self.edit_color = LineEdit()
        self.edit_color.setText("#4682B4")
        self.edit_color.setMaximumWidth(100)
        self.btn_pick_color = PushButton("選色…")
        self.btn_pick_color.clicked.connect(self._on_pick_color)
        self._color_preview = QLabel("  ")
        self._color_preview.setFixedSize(24, 24)
        self._update_color_preview("#4682B4")
        color_row.addWidget(self.edit_color)
        color_row.addWidget(self._color_preview)
        color_row.addWidget(self.btn_pick_color)
        color_row.addStretch()
        form.addRow("名稱顏色:", color_row)

        self.edit_color.textChanged.connect(self._update_color_preview)

        # 螢幕位置
        self.combo_position = ComboBox()
        self.combo_position.addItems(POSITION_OPTIONS.keys())
        self.combo_position.setCurrentText("中")
        form.addRow("螢幕位置:", self.combo_position)

        layout.addLayout(form)

        # 表情差分列表
        sprite_group = QGroupBox("表情差分列表")
        sprite_layout = QVBoxLayout()

        # 水平佈局：左側 tree + 按鈕，右側預覽
        sprite_content = QHBoxLayout()

        # 左側：樹狀結構
        left_side = QVBoxLayout()
        self.sprite_tree = QTreeWidget()
        self.sprite_tree.setColumnCount(2)
        self.sprite_tree.setHeaderLabels(["標籤", ""])
        self.sprite_tree.setIconSize(QSize(48, 48))
        self.sprite_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sprite_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.sprite_tree.header().resizeSection(1, 60)
        self.sprite_tree.setMinimumHeight(180)

        # 根節點（不可選取，僅作分組標題）
        self._sprite_root = QTreeWidgetItem(self.sprite_tree, ["立繪"])
        self._sprite_root.setExpanded(True)
        self._sprite_root.setFlags(
            self._sprite_root.flags() & ~Qt.ItemFlag.ItemIsSelectable
        )

        left_side.addWidget(self.sprite_tree)

        sprite_btn_layout = QHBoxLayout()
        btn_add_sprite = PushButton("新增差分")
        btn_remove_sprite = PushButton("移除差分")
        btn_add_sprite.clicked.connect(self._on_add_sprite)
        btn_remove_sprite.clicked.connect(self._on_remove_sprite)
        sprite_btn_layout.addWidget(btn_add_sprite)
        sprite_btn_layout.addWidget(btn_remove_sprite)
        sprite_btn_layout.addStretch()
        left_side.addLayout(sprite_btn_layout)

        sprite_content.addLayout(left_side, 2)

        # 右側：圖片預覽
        self._sprite_preview = QLabel("選擇差分\n以預覽")
        self._sprite_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sprite_preview.setMinimumSize(160, 180)
        self._sprite_preview.setStyleSheet("border: 1px solid #555; background: #1e1e1e; color: #888;")
        sprite_content.addWidget(self._sprite_preview, 1)

        sprite_layout.addLayout(sprite_content)
        sprite_group.setLayout(sprite_layout)
        layout.addWidget(sprite_group)

        self.sprite_tree.currentItemChanged.connect(self._on_sprite_selected)

        # 按鈕
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _load_character(self, char: Character) -> None:
        """載入既有角色資料。"""
        self.edit_name.setText(char.name)
        self.edit_color.setText(char.name_color)
        pos_label = POSITION_LABELS.get(char.position, "中")
        self.combo_position.setCurrentText(pos_label)

        for sv in char.sprites:
            item = QTreeWidgetItem(self._sprite_root, [sv.label])
            item.setData(0, Qt.ItemDataRole.UserRole, sv.filename)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            # 載入縮圖
            full_path = self._project_dir / "assets" / sv.filename
            if full_path.exists():
                pm = QPixmap(str(full_path)).scaled(
                    48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                item.setIcon(0, QIcon(pm))
            # 瀏覽按鈕
            btn = PushButton("瀏覽…")
            btn.setFixedHeight(24)
            btn.clicked.connect(lambda _, i=item: self._on_browse_sprite(i))
            self.sprite_tree.setItemWidget(item, 1, btn)
        self._sprite_root.setExpanded(True)

    def _on_pick_color(self) -> None:
        from PyQt6.QtGui import QColor

        initial = QColor(self.edit_color.text())
        color = QColorDialog.getColor(initial, self, "選擇名稱顏色")
        if color.isValid():
            self.edit_color.setText(color.name())

    def _update_color_preview(self, color_text: str) -> None:
        self._color_preview.setStyleSheet(
            f"background-color: {color_text}; border: 1px solid #888; border-radius: 3px;"
        )

    def _on_browse_sprite(self, item: QTreeWidgetItem) -> None:
        """開啟圖片選擇對話框，複製圖片到素材目錄，更新縮圖與 UserRole。"""
        from src.core.asset_manager import import_asset

        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇表情圖片", "", "圖片 (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        try:
            filename = import_asset(Path(file_path), "sprites", self._project_dir)
            item.setData(0, Qt.ItemDataRole.UserRole, filename)
            # 更新縮圖 icon
            pm = QPixmap(file_path).scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            item.setIcon(0, QIcon(pm))
            # 若此 item 正被選中，更新右側預覽
            if self.sprite_tree.currentItem() is item:
                self._on_sprite_selected(item, None)
        except (ValueError, FileNotFoundError, OSError) as e:
            QMessageBox.warning(self, "匯入失敗", str(e))

    def _on_add_sprite(self) -> None:
        count = self._sprite_root.childCount()
        default_label = f"差分{count + 1}"
        item = QTreeWidgetItem(self._sprite_root, [default_label])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        # 瀏覽按鈕
        btn = QPushButton("瀏覽…")
        btn.setFixedHeight(24)
        btn.clicked.connect(lambda _, i=item: self._on_browse_sprite(i))
        self.sprite_tree.setItemWidget(item, 1, btn)
        self.sprite_tree.setCurrentItem(item)
        self.sprite_tree.editItem(item, 0)

    def _on_remove_sprite(self) -> None:
        current = self.sprite_tree.currentItem()
        if current and current.parent() == self._sprite_root:
            self._sprite_root.removeChild(current)
            self._sprite_preview.clear()
            self._sprite_preview.setText("選擇差分\n以預覽")

    def _on_sprite_selected(self, current, _previous) -> None:
        """選中 tree item 時更新右側圖片預覽。"""
        if current and current.parent() == self._sprite_root:
            filename = current.data(0, Qt.ItemDataRole.UserRole)
            if filename:
                full_path = self._project_dir / "assets" / filename
                if full_path.exists():
                    pm = QPixmap(str(full_path))
                    scaled = pm.scaled(
                        self._sprite_preview.width(),
                        self._sprite_preview.height(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self._sprite_preview.setPixmap(scaled)
                    return
        self._sprite_preview.clear()
        self._sprite_preview.setText("選擇差分\n以預覽")

    def _validate_and_accept(self) -> None:
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "缺少名稱", "請輸入角色名稱。")
            return
        self.accept()

    def get_character(self) -> Character:
        """從對話框欄位建立 Character 物件。"""
        name = self.edit_name.text().strip()
        color = self.edit_color.text().strip() or "#4682B4"
        pos_label = self.combo_position.currentText()
        position = POSITION_OPTIONS.get(pos_label, "center")

        sprites = []
        for i in range(self._sprite_root.childCount()):
            child = self._sprite_root.child(i)
            label = child.text(0).strip()
            filename = (child.data(0, Qt.ItemDataRole.UserRole) or "").strip()
            if not filename:
                continue  # 沒有選擇圖片的差分跳過
            if not label:
                label = f"差分{i + 1}"  # 自動補標籤
            sprites.append(SpriteVariant(label=label, filename=filename))

        default_costume = Costume(name="預設", expressions=sprites)
        return Character(
            name=name,
            name_color=color,
            position=position,
            costumes=[default_costume] if sprites else [],
        )


class CostumeEditorDialog(QDialog):
    """服裝/表情分層編輯器：左側服裝列表，右側表情差分，支援拖曳匯入圖片。"""

    def __init__(
        self,
        character: Character,
        project_dir: Path,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        import copy
        self._project_dir = Path(project_dir)
        self._costumes: list[Costume] = copy.deepcopy(character.costumes)
        self.setWindowTitle(f"編輯服裝 — {character.name}")
        self.setMinimumSize(580, 380)
        self._setup_ui()
        self._populate_costume_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左側：服裝列表
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.addWidget(QLabel("服裝:"))
        self._costume_list = QListWidget()
        self._costume_list.setMinimumWidth(140)
        left_layout.addWidget(self._costume_list)
        cos_btns = QHBoxLayout()
        btn_add_cos = PushButton("新增")
        btn_rem_cos = PushButton("移除")
        btn_add_cos.clicked.connect(self._on_add_costume)
        btn_rem_cos.clicked.connect(self._on_remove_costume)
        cos_btns.addWidget(btn_add_cos)
        cos_btns.addWidget(btn_rem_cos)
        left_layout.addLayout(cos_btns)
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        # 右側：表情差分列表（接受拖曳）
        right_widget = _DroppableExprWidget(self)
        right_widget.files_dropped.connect(self._on_files_dropped)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.addWidget(QLabel("表情差分（可拖曳圖片匯入）:"))
        self._expr_list = QListWidget()
        self._expr_list.setIconSize(QSize(48, 48))
        self._expr_list.setMinimumWidth(200)
        right_layout.addWidget(self._expr_list)
        expr_btns = QHBoxLayout()
        btn_add_expr = PushButton("新增表情")
        btn_rem_expr = PushButton("移除表情")
        btn_add_expr.clicked.connect(self._on_add_expression)
        btn_rem_expr.clicked.connect(self._on_remove_expression)
        expr_btns.addWidget(btn_add_expr)
        expr_btns.addWidget(btn_rem_expr)
        right_layout.addLayout(expr_btns)
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        splitter.setSizes([160, 380])
        layout.addWidget(splitter)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self._costume_list.currentRowChanged.connect(self._on_costume_selected)

    def _populate_costume_list(self) -> None:
        self._costume_list.clear()
        for cos in self._costumes:
            self._costume_list.addItem(cos.name)
        if self._costumes:
            self._costume_list.setCurrentRow(0)
        else:
            self._expr_list.clear()

    def _on_costume_selected(self, row: int) -> None:
        self._expr_list.clear()
        if 0 <= row < len(self._costumes):
            for sv in self._costumes[row].expressions:
                item = QListWidgetItem(sv.label)
                item.setData(Qt.ItemDataRole.UserRole, sv.filename)
                if sv.filename:
                    path = self._project_dir / "assets" / sv.filename
                    if path.exists():
                        pm = QPixmap(str(path)).scaled(
                            48, 48,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        item.setIcon(QIcon(pm))
                self._expr_list.addItem(item)

    def _on_add_costume(self) -> None:
        name, ok = QInputDialog.getText(self, "新增服裝", "服裝名稱:")
        if ok and name.strip():
            self._costumes.append(Costume(name=name.strip()))
            self._populate_costume_list()
            self._costume_list.setCurrentRow(len(self._costumes) - 1)

    def _on_remove_costume(self) -> None:
        row = self._costume_list.currentRow()
        if 0 <= row < len(self._costumes):
            self._costumes.pop(row)
            self._populate_costume_list()

    def _on_add_expression(self) -> None:
        cos_row = self._costume_list.currentRow()
        if cos_row < 0 or cos_row >= len(self._costumes):
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇表情圖片", "", "圖片 (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        self._import_expression(cos_row, Path(file_path))

    def _on_remove_expression(self) -> None:
        cos_row = self._costume_list.currentRow()
        expr_row = self._expr_list.currentRow()
        if (
            0 <= cos_row < len(self._costumes)
            and 0 <= expr_row < len(self._costumes[cos_row].expressions)
        ):
            self._costumes[cos_row].expressions.pop(expr_row)
            self._on_costume_selected(cos_row)

    def _on_files_dropped(self, paths: list[Path]) -> None:
        """拖曳圖片到右側面板時批量匯入。"""
        cos_row = self._costume_list.currentRow()
        if cos_row < 0 or cos_row >= len(self._costumes):
            return
        for p in paths:
            if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                self._import_expression(cos_row, p)

    def _import_expression(self, cos_row: int, file_path: Path) -> None:
        try:
            from src.core.asset_manager import import_asset
            filename = import_asset(file_path, "sprites", self._project_dir)
        except (ValueError, FileNotFoundError, OSError) as e:
            QMessageBox.warning(self, "匯入失敗", str(e))
            return
        label, ok = QInputDialog.getText(
            self, "表情標籤", "標籤名稱:", text=file_path.stem
        )
        if not ok or not label.strip():
            return
        self._costumes[cos_row].expressions.append(
            SpriteVariant(label=label.strip(), filename=filename)
        )
        self._on_costume_selected(cos_row)

    def get_costumes(self) -> list[Costume]:
        """回傳編輯後的服裝列表。"""
        return self._costumes


class _DroppableExprWidget(QWidget):
    """接受圖片拖曳的容器 widget。"""

    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()


class AppearanceSettingsDialog(QDialog):
    """外觀設定：主題切換 + UI 字體大小。"""

    def __init__(self, current_theme: str, current_font_size: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("外觀設定")
        self.setMinimumWidth(300)
        self._theme = current_theme
        self._font_size = current_font_size
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        # 主題選擇
        theme_group = QGroupBox("主題")
        theme_layout = QVBoxLayout()
        self._radio_dark = QRadioButton("深色")
        self._radio_light = QRadioButton("淺色")
        if self._theme == "dark":
            self._radio_dark.setChecked(True)
        else:
            self._radio_light.setChecked(True)
        theme_layout.addWidget(self._radio_dark)
        theme_layout.addWidget(self._radio_light)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # 字體大小
        font_group = QGroupBox("UI 字體大小")
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("大小 (px):"))
        self._combo_font = ComboBox()
        self._combo_font.addItems(["12", "14", "16", "18", "20"])
        self._combo_font.setCurrentText(str(self._font_size))
        font_layout.addWidget(self._combo_font)
        font_layout.addStretch()
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_settings(self) -> tuple[str, int]:
        """回傳 (theme_name, font_size)。"""
        theme = "dark" if self._radio_dark.isChecked() else "light"
        font_size = int(self._combo_font.currentText())
        return theme, font_size


class GameSettingsDialog(QDialog):
    """遊戲顯示設定：對話字體大小、名稱大小、對話框透明度。"""

    def __init__(self, game_settings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("遊戲設定")
        self.setMinimumWidth(320)
        self._gs = game_settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        from PyQt6.QtWidgets import QDoubleSpinBox, QGroupBox, QSpinBox
        layout = QVBoxLayout()

        form = QFormLayout()

        self._spin_dlg_font = QSpinBox()
        self._spin_dlg_font.setRange(12, 86)
        self._spin_dlg_font.setValue(self._gs.dialogue_font_size)
        form.addRow("對話文字大小 (px):", self._spin_dlg_font)

        self._spin_name_font = QSpinBox()
        self._spin_name_font.setRange(12, 86)
        self._spin_name_font.setValue(self._gs.name_font_size)
        form.addRow("角色名稱大小 (px):", self._spin_name_font)

        self._spin_opacity = QDoubleSpinBox()
        self._spin_opacity.setRange(0.5, 1.0)
        self._spin_opacity.setSingleStep(0.05)
        self._spin_opacity.setDecimals(2)
        self._spin_opacity.setValue(self._gs.dialogue_box_opacity)
        form.addRow("對話框透明度:", self._spin_opacity)

        layout.addLayout(form)

        # 建議範圍提示
        tip = QLabel(
            "建議：\n"
            "  720p → 對話 18~28px、名稱 16~24px\n"
            "  1080p → 對話 24~40px、名稱 20~32px\n"
            "  4K → 對話 36~56px、名稱 28~48px"
        )
        tip.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(tip)

        # 即時預覽區
        preview_group = QGroupBox("預覽")
        preview_layout = QVBoxLayout()
        self._preview_name = QLabel("角色名稱")
        self._preview_name.setStyleSheet("color: #4682B4; font-weight: bold;")
        self._preview_text = QLabel(
            "這是一段預覽文字，用來確認字體大小是否合適。\n"
            "This is a preview text for checking font size."
        )
        self._preview_text.setWordWrap(True)
        self._preview_text.setStyleSheet(
            "color: #eee; background: rgba(20,20,40,200); padding: 12px; border-radius: 4px;"
        )
        preview_layout.addWidget(self._preview_name)
        preview_layout.addWidget(self._preview_text)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # 連接即時預覽
        self._spin_dlg_font.valueChanged.connect(self._update_preview)
        self._spin_name_font.valueChanged.connect(self._update_preview)
        self._spin_opacity.valueChanged.connect(self._update_preview)
        self._update_preview()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _update_preview(self) -> None:
        dlg_size = self._spin_dlg_font.value()
        name_size = self._spin_name_font.value()
        self._preview_name.setStyleSheet(
            f"color: #4682B4; font-weight: bold; font-size: {name_size}px;"
        )
        self._preview_text.setStyleSheet(
            f"color: #eee; background: rgba(20,20,40,200); "
            f"padding: 12px; border-radius: 4px; font-size: {dlg_size}px;"
        )

    def get_settings(self):
        """回傳更新後的 GameSettings。"""
        from src.core.models import GameSettings
        return GameSettings(
            dialogue_font_size=self._spin_dlg_font.value(),
            name_font_size=self._spin_name_font.value(),
            dialogue_box_opacity=self._spin_opacity.value(),
        )


# ── 舞台槽位 Picker ──


class StageSlotPickerDialog(QDialog):
    """為單一舞台槽位（left/center/right）選取角色 + 服裝 + 表情。"""

    def __init__(
        self,
        characters: list[Character],
        current: dict | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("設置舞台槽位")
        self.setMinimumWidth(340)
        self._characters = characters
        self._result: dict | None = None

        layout = QVBoxLayout()
        form = QFormLayout()

        # 角色
        self._combo_char = ComboBox()
        self._combo_char.addItem("(無)")
        for c in characters:
            self._combo_char.addItem(c.name)
        form.addRow("角色:", self._combo_char)

        # 服裝
        self._combo_costume = ComboBox()
        form.addRow("服裝:", self._combo_costume)

        # 表情
        self._combo_sprite = ComboBox()
        form.addRow("表情:", self._combo_sprite)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

        # 信號串聯
        self._combo_char.currentIndexChanged.connect(self._on_char_changed)
        self._combo_costume.currentIndexChanged.connect(self._on_costume_changed)

        # 預填現有值
        if current and current.get("character"):
            idx = self._combo_char.findText(current["character"])
            if idx >= 0:
                self._combo_char.setCurrentIndex(idx)
            self._on_char_changed(self._combo_char.currentIndex())
            if current.get("costume"):
                cidx = self._combo_costume.findText(current["costume"])
                if cidx >= 0:
                    self._combo_costume.setCurrentIndex(cidx)
                self._on_costume_changed(self._combo_costume.currentIndex())
            if current.get("sprite"):
                sidx = self._combo_sprite.findText(current["sprite"])
                if sidx >= 0:
                    self._combo_sprite.setCurrentIndex(sidx)
        else:
            self._on_char_changed(0)

    def _on_char_changed(self, index: int) -> None:
        self._combo_costume.clear()
        char_name = self._combo_char.currentText()
        char = next((c for c in self._characters if c.name == char_name), None)
        if char:
            for cos in char.costumes:
                self._combo_costume.addItem(cos.name)
        self._on_costume_changed(0)

    def _on_costume_changed(self, index: int) -> None:
        self._combo_sprite.clear()
        char_name = self._combo_char.currentText()
        char = next((c for c in self._characters if c.name == char_name), None)
        if not char:
            return
        cos_name = self._combo_costume.currentText()
        cos = next((c for c in char.costumes if c.name == cos_name), None)
        if cos:
            self._combo_sprite.addItem("(預設)")
            for expr in cos.expressions:
                self._combo_sprite.addItem(expr.label)

    def get_value(self) -> dict | None:
        """回傳 {"character": str, "costume": str|None, "sprite": str|None}，或 None（選(無)）。"""
        char_name = self._combo_char.currentText()
        if char_name == "(無)":
            return None
        cos_name = self._combo_costume.currentText() or None
        sprite_text = self._combo_sprite.currentText()
        sprite = None if (not sprite_text or sprite_text == "(預設)") else sprite_text
        return {"character": char_name, "costume": cos_name, "sprite": sprite}
