"""檔案對話框包裝：文字、圖片、音訊匯入對話框、影片導出設定、貼上文字、角色編輯。"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.models import Character, SpriteVariant


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
        self.combo_resolution = QComboBox()
        self.combo_resolution.addItems(RESOLUTION_OPTIONS.keys())
        form.addRow("解析度:", self.combo_resolution)

        # 停留時間說明
        lbl_duration = QLabel("停留時間依字數自動計算（1.5～8 秒）")
        lbl_duration.setStyleSheet("color: #888;")
        form.addRow("停留時間:", lbl_duration)

        # 輸出路徑
        path_layout = QHBoxLayout()
        self.edit_path = QLineEdit()
        self.edit_path.setPlaceholderText("選擇輸出路徑…")
        btn_browse = QPushButton("瀏覽…")
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
        self.edit_character = QLineEdit()
        self.edit_character.setPlaceholderText("輸入角色名稱（留空清除）")
        char_row.addWidget(self.chk_character)
        char_row.addWidget(self.edit_character, 1)
        form.addRow("角色:", char_row)

        # 立繪
        sprite_row = QHBoxLayout()
        self.chk_sprite = QCheckBox("變更")
        self.chk_sprite.setChecked(False)
        self.combo_sprite = QComboBox()
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
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("角色名稱")
        form.addRow("名稱:", self.edit_name)

        # 名稱顏色
        color_row = QHBoxLayout()
        self.edit_color = QLineEdit("#4682B4")
        self.edit_color.setMaximumWidth(100)
        self.btn_pick_color = QPushButton("選色…")
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
        self.combo_position = QComboBox()
        self.combo_position.addItems(POSITION_OPTIONS.keys())
        self.combo_position.setCurrentText("中")
        form.addRow("螢幕位置:", self.combo_position)

        layout.addLayout(form)

        # 表情差分列表
        sprite_group = QGroupBox("表情差分列表")
        sprite_layout = QVBoxLayout()

        self.sprite_table = QTableWidget()
        self.sprite_table.setColumnCount(3)
        self.sprite_table.setHorizontalHeaderLabels(["標籤", "檔案名稱", "操作"])
        header = self.sprite_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.sprite_table.setColumnWidth(2, 70)
        sprite_layout.addWidget(self.sprite_table)

        sprite_btn_layout = QHBoxLayout()
        btn_add_sprite = QPushButton("新增差分")
        btn_remove_sprite = QPushButton("移除差分")
        btn_add_sprite.clicked.connect(self._on_add_sprite)
        btn_remove_sprite.clicked.connect(self._on_remove_sprite)
        sprite_btn_layout.addWidget(btn_add_sprite)
        sprite_btn_layout.addWidget(btn_remove_sprite)
        sprite_btn_layout.addStretch()
        sprite_layout.addLayout(sprite_btn_layout)

        sprite_group.setLayout(sprite_layout)
        layout.addWidget(sprite_group)

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

        self.sprite_table.setRowCount(len(char.sprites))
        for row, sv in enumerate(char.sprites):
            self.sprite_table.setItem(row, 0, QTableWidgetItem(sv.label))
            self.sprite_table.setItem(row, 1, QTableWidgetItem(sv.filename))
            self._add_browse_button(row)

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

    def _add_browse_button(self, row: int) -> None:
        """在指定行的操作欄加入瀏覽按鈕。"""
        btn = QPushButton("瀏覽…")
        btn.clicked.connect(self._on_browse_sprite_clicked)
        self.sprite_table.setCellWidget(row, 2, btn)

    def _on_browse_sprite_clicked(self) -> None:
        """找出觸發點擊的按鈕所在行，呼叫瀏覽圖片。"""
        btn = self.sender()
        for row in range(self.sprite_table.rowCount()):
            if self.sprite_table.cellWidget(row, 2) is btn:
                self._on_browse_sprite(row)
                return

    def _on_browse_sprite(self, row: int) -> None:
        """開啟圖片選擇對話框，複製圖片到素材目錄，回填檔名欄。"""
        from src.core.asset_manager import import_asset

        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇表情圖片", "", "圖片 (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        try:
            filename = import_asset(Path(file_path), "sprites", self._project_dir)
            self.sprite_table.setItem(row, 1, QTableWidgetItem(filename))
        except (ValueError, FileNotFoundError, OSError) as e:
            QMessageBox.warning(self, "匯入失敗", str(e))

    def _on_add_sprite(self) -> None:
        row = self.sprite_table.rowCount()
        self.sprite_table.insertRow(row)
        self.sprite_table.setItem(row, 0, QTableWidgetItem(""))
        self.sprite_table.setItem(row, 1, QTableWidgetItem(""))
        self._add_browse_button(row)
        self.sprite_table.setCurrentCell(row, 0)
        self.sprite_table.editItem(self.sprite_table.item(row, 0))

    def _on_remove_sprite(self) -> None:
        row = self.sprite_table.currentRow()
        if row >= 0:
            self.sprite_table.removeRow(row)

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
        for row in range(self.sprite_table.rowCount()):
            label_item = self.sprite_table.item(row, 0)
            file_item = self.sprite_table.item(row, 1)
            label = label_item.text().strip() if label_item else ""
            filename = file_item.text().strip() if file_item else ""
            if label and filename:
                sprites.append(SpriteVariant(label=label, filename=filename))

        return Character(
            name=name,
            name_color=color,
            position=position,
            sprites=sprites,
        )


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
        self._combo_font = QComboBox()
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
        from PyQt6.QtWidgets import QDoubleSpinBox, QSpinBox
        layout = QVBoxLayout()

        form = QFormLayout()

        self._spin_dlg_font = QSpinBox()
        self._spin_dlg_font.setRange(14, 32)
        self._spin_dlg_font.setValue(self._gs.dialogue_font_size)
        form.addRow("對話文字大小 (px):", self._spin_dlg_font)

        self._spin_name_font = QSpinBox()
        self._spin_name_font.setRange(12, 28)
        self._spin_name_font.setValue(self._gs.name_font_size)
        form.addRow("角色名稱大小 (px):", self._spin_name_font)

        self._spin_opacity = QDoubleSpinBox()
        self._spin_opacity.setRange(0.5, 1.0)
        self._spin_opacity.setSingleStep(0.05)
        self._spin_opacity.setDecimals(2)
        self._spin_opacity.setValue(self._gs.dialogue_box_opacity)
        form.addRow("對話框透明度:", self._spin_opacity)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_settings(self):
        """回傳更新後的 GameSettings。"""
        from src.core.models import GameSettings
        return GameSettings(
            dialogue_font_size=self._spin_dlg_font.value(),
            name_font_size=self._spin_name_font.value(),
            dialogue_box_opacity=self._spin_opacity.value(),
        )
