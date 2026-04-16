"""空狀態引導元件：首次啟動或空專案時顯示。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PrimaryPushButton, PushButton


class EmptyStateWidget(QWidget):
    """空專案時在預覽區域顯示的引導畫面。

    提供兩個入口：匯入文字檔、新增第一個場景。
    """

    import_text_clicked = pyqtSignal()
    add_scene_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        title = QLabel("開始你的第一個故事")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("匯入 .txt / .docx 文字檔，或手動新增場景")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)

        layout.addSpacing(8)

        btn_import = PrimaryPushButton("匯入文字檔…")
        btn_import.setFixedWidth(200)
        btn_import.clicked.connect(self.import_text_clicked)
        layout.addWidget(btn_import, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_add = PushButton("新增第一個場景")
        btn_add.setFixedWidth(200)
        btn_add.clicked.connect(self.add_scene_clicked)
        layout.addWidget(btn_add, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
