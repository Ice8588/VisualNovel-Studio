"""檔案對話框包裝：文字、圖片、音訊匯入對話框、影片導出設定、貼上文字、角色編輯。"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSplitter,
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


# Phase 2：批次角色指定對話框已刪除，批次操作改由 timeline 拖 segment 取代。


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

# 預設名牌顏色（淺/深色皆清晰）
_PRESET_COLORS = [
    ("#FFFFFF", "白"), ("#222222", "黑"), ("#E05555", "紅"), ("#4682B4", "藍"),
    ("#4CAF50", "綠"), ("#FFD700", "黃"), ("#FF8C00", "橙"), ("#9B59B6", "紫"),
]


class CharacterEditorDialog(QDialog):
    """新增或編輯角色：名稱、名牌顏色、預設立繪；支援拖曳圖片與角色卡匯入匯出。"""

    def __init__(
        self,
        character: Character | None = None,
        project_dir: Path | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._original = character
        self._project_dir = project_dir or Path(tempfile.gettempdir()) / "vnstudio_unsaved"
        self._selected_color = "#4682B4"
        self._sprite_filename: str | None = None
        # C6：若透過角色卡匯入，除主立繪外還可能夾帶額外差分，存在這裡作為 get_character() 的 costumes 輸出
        self._extra_costumes: list[Costume] = []
        self._loaded_from_card: bool = False
        self.setAcceptDrops(True)
        self.setWindowTitle("編輯角色" if character else "新增角色")
        self.setMinimumWidth(420)
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

        # 名牌顏色：預設色塊
        color_widget = QWidget()
        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(4)
        self._color_btns: list[QPushButton] = []
        for hex_color, label in _PRESET_COLORS:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setToolTip(label)
            btn.setStyleSheet(
                f"background-color:{hex_color}; border:2px solid #888; border-radius:3px;"
            )
            btn.clicked.connect(lambda _, c=hex_color: self._on_color_clicked(c))
            color_layout.addWidget(btn)
            self._color_btns.append(btn)
        self._lbl_color_preview = QLabel()
        self._lbl_color_preview.setFixedSize(60, 22)
        self._lbl_color_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color_layout.addSpacing(4)
        color_layout.addWidget(self._lbl_color_preview)
        color_layout.addStretch()
        color_widget.setLayout(color_layout)
        form.addRow("名牌顏色:", color_widget)

        layout.addLayout(form)

        # 預設立繪（單張）
        sprite_group = QGroupBox("預設立繪")
        sprite_layout = QHBoxLayout()
        self._sprite_preview = QLabel("尚未選擇圖片")
        self._sprite_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sprite_preview.setFixedSize(120, 140)
        self._sprite_preview.setStyleSheet(
            "border:1px solid #555; background:#1e1e1e; color:#888;"
        )
        sprite_layout.addWidget(self._sprite_preview)
        btn_side = QVBoxLayout()
        self.btn_browse_sprite = PushButton("選擇圖片…")
        self.btn_browse_sprite.clicked.connect(self._on_browse_sprite)
        self.btn_clear_sprite = PushButton("清除")
        self.btn_clear_sprite.clicked.connect(self._on_clear_sprite)
        self._lbl_sprite_name = QLabel("（無）")
        self._lbl_sprite_name.setWordWrap(True)
        btn_side.addWidget(self.btn_browse_sprite)
        btn_side.addWidget(self.btn_clear_sprite)
        btn_side.addWidget(self._lbl_sprite_name)
        btn_side.addStretch()
        sprite_layout.addLayout(btn_side)
        sprite_group.setLayout(sprite_layout)
        layout.addWidget(sprite_group)

        # C6 角色卡按鈕列
        card_row = QHBoxLayout()
        self.btn_import_card = PushButton("從角色卡匯入…")
        self.btn_import_card.clicked.connect(self._on_import_card)
        self.btn_export_card = PushButton("儲存為角色卡…")
        self.btn_export_card.clicked.connect(self._on_export_card)
        card_row.addWidget(self.btn_import_card)
        card_row.addWidget(self.btn_export_card)
        card_row.addStretch()
        layout.addLayout(card_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._apply_color(self._selected_color)

    def _load_character(self, char: Character) -> None:
        self.edit_name.setText(char.name)
        self._apply_color(char.name_color)
        if char.sprites:
            sv = char.sprites[0]
            self._sprite_filename = sv.filename
            self._lbl_sprite_name.setText(sv.label)
            full_path = self._project_dir / "assets" / sv.filename
            if full_path.exists():
                pm = QPixmap(str(full_path)).scaled(
                    116, 136, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._sprite_preview.setPixmap(pm)

    def _apply_color(self, hex_color: str) -> None:
        self._selected_color = hex_color
        self._lbl_color_preview.setStyleSheet(
            f"background-color:{hex_color}; border:1px solid #888; border-radius:3px;"
        )
        self._lbl_color_preview.setText(hex_color)
        for btn, (c, _) in zip(self._color_btns, _PRESET_COLORS):
            selected = c.upper() == hex_color.upper()
            btn.setStyleSheet(
                f"background-color:{c}; border:{('3px solid #fff' if selected else '2px solid #888')}; border-radius:3px;"
            )

    def _on_color_clicked(self, hex_color: str) -> None:
        self._apply_color(hex_color)

    def _on_browse_sprite(self) -> None:
        from src.core.asset_manager import import_asset
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇立繪圖片", "", "圖片 (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        try:
            filename = import_asset(Path(file_path), "sprites", self._project_dir)
            self._sprite_filename = filename
            self._lbl_sprite_name.setText(Path(file_path).stem)
            pm = QPixmap(file_path).scaled(
                116, 136, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._sprite_preview.setPixmap(pm)
        except (ValueError, FileNotFoundError, OSError) as e:
            QMessageBox.warning(self, "匯入失敗", str(e))

    def _on_clear_sprite(self) -> None:
        self._sprite_filename = None
        self._lbl_sprite_name.setText("（無）")
        self._sprite_preview.clear()
        self._sprite_preview.setText("尚未選擇圖片")
        self._extra_costumes = []
        self._loaded_from_card = False

    # ── C2：拖曳圖片到對話框任何位置即匯入為立繪 ──

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        from src.core.asset_manager import import_asset
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            p = Path(url.toLocalFile())
            if p.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                continue
            try:
                filename = import_asset(p, "sprites", self._project_dir)
            except (ValueError, FileNotFoundError, OSError) as e:
                QMessageBox.warning(self, "匯入失敗", str(e))
                continue
            self._sprite_filename = filename
            self._lbl_sprite_name.setText(p.stem)
            pm = QPixmap(str(p)).scaled(
                116, 136, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._sprite_preview.setPixmap(pm)
            break  # 多檔拖入時只接受第一張（單一預設立繪）
        event.acceptProposedAction()

    # ── C6：角色卡匯入 / 匯出 ──

    def _on_import_card(self) -> None:
        from src.core.character_library import list_cards, load_card, get_library_dir

        lib_dir = get_library_dir()
        cards = list_cards(lib_dir)
        if not cards:
            QMessageBox.information(
                self, "沒有角色卡",
                f"資料庫為空：{lib_dir}\n\n可先在另一個專案『儲存為角色卡…』後匯入。",
            )
            return

        # 允許選目錄外的卡
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇角色卡",
            str(lib_dir),
            "角色卡 (*.vncard);;所有檔案 (*)",
        )
        if not path:
            return

        try:
            char, _written = load_card(Path(path), self._project_dir / "assets")
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(self, "匯入失敗", str(e))
            return

        # 覆蓋目前編輯值
        self.edit_name.setText(char.name)
        self._apply_color(char.name_color)
        if char.costumes and char.costumes[0].expressions:
            first = char.costumes[0].expressions[0]
            self._sprite_filename = first.filename
            self._lbl_sprite_name.setText(first.label)
            full = self._project_dir / "assets" / first.filename
            if full.exists():
                pm = QPixmap(str(full)).scaled(
                    116, 136, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._sprite_preview.setPixmap(pm)
        # 保留所有服裝（含差分）供 get_character 使用
        self._extra_costumes = list(char.costumes)
        self._loaded_from_card = True

    def _on_export_card(self) -> None:
        from src.core.character_library import save_card

        # 必須先有名稱與立繪
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "缺少名稱", "請先輸入角色名稱才能匯出角色卡。")
            return
        if not self._sprite_filename and not self._extra_costumes:
            QMessageBox.warning(self, "缺少立繪", "請先匯入至少一張立繪才能匯出角色卡。")
            return

        # 編輯中的角色（未 accept）先組一個臨時 Character 出去
        char = self.get_character()
        assets_dir = self._project_dir / "assets"
        try:
            path = save_card(char, assets_dir)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "儲存失敗", str(e))
            return
        QMessageBox.information(
            self, "角色卡已儲存",
            f"角色卡已寫入：\n{path}\n\n日後可在其他專案透過『從角色卡匯入』復用。",
        )

    def _validate_and_accept(self) -> None:
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "缺少名稱", "請輸入角色名稱。")
            return
        self.accept()

    def get_character(self) -> Character:
        name = self.edit_name.text().strip()
        color = self._selected_color or "#4682B4"
        # 若透過角色卡匯入、且未手動覆寫立繪 → 保留卡內所有服裝
        if self._loaded_from_card and self._extra_costumes:
            return Character(name=name, name_color=color, costumes=list(self._extra_costumes))
        sprites = []
        if self._sprite_filename:
            label = self._lbl_sprite_name.text() or "預設"
            sprites.append(SpriteVariant(label=label, filename=self._sprite_filename))
        default_costume = Costume(name="預設", expressions=sprites)
        return Character(
            name=name,
            name_color=color,
            costumes=[default_costume] if sprites else [],
        )


class CostumeEditorDialog(QDialog):
    """服裝/差分分層編輯器：左側服裝列表，右側立繪差分，支援拖曳匯入圖片。"""

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

        # 右側：立繪差分列表（接受拖曳；C3 雙擊可改 label）
        right_widget = _DroppableExprWidget(self)
        right_widget.files_dropped.connect(self._on_files_dropped)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.addWidget(QLabel("立繪差分（可拖曳圖片匯入；雙擊標籤可改名）:"))
        self._expr_list = QListWidget()
        self._expr_list.setIconSize(QSize(48, 48))
        self._expr_list.setMinimumWidth(200)
        self._expr_list.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._expr_list.itemChanged.connect(self._on_expr_label_changed)
        right_layout.addWidget(self._expr_list)
        expr_btns = QHBoxLayout()
        btn_add_expr = PushButton("新增差分")
        btn_rem_expr = PushButton("移除差分")
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
        self._expr_list.blockSignals(True)
        self._expr_list.clear()
        if 0 <= row < len(self._costumes):
            for sv in self._costumes[row].expressions:
                item = QListWidgetItem(sv.label)
                # C3：標記此 item 可編輯（雙擊即進入 label 編輯）
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
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
        self._expr_list.blockSignals(False)

    def _on_expr_label_changed(self, item: QListWidgetItem) -> None:
        """C3：雙擊結束後把新 label 寫回 SpriteVariant。"""
        cos_row = self._costume_list.currentRow()
        expr_row = self._expr_list.row(item)
        if not (0 <= cos_row < len(self._costumes)):
            return
        expressions = self._costumes[cos_row].expressions
        if not (0 <= expr_row < len(expressions)):
            return
        new_label = item.text().strip()
        if not new_label:
            # 空字串還原
            self._expr_list.blockSignals(True)
            item.setText(expressions[expr_row].label)
            self._expr_list.blockSignals(False)
            return
        expressions[expr_row].label = new_label

    def _on_add_costume(self) -> None:
        default_name = f"服裝{len(self._costumes) + 1}"
        name, ok = QInputDialog.getText(self, "新增服裝", "服裝名稱:", text=default_name)
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
            self, "選擇差分圖片", "", "圖片 (*.png *.jpg *.jpeg)"
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
            self, "差分標籤", "標籤名稱:", text=file_path.stem
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



# Phase 2：舞台槽位 / 批次舞台 dialog 已刪除；舞台編輯改走
# src/ui/stage_panel.py + src/ui/segment_editor.py，以時間軸 segment 操作。
