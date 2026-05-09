"""About 對話框：上方放 logo wordmark，下方放版本與描述。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from src.ui import palette
from src.ui.icons import design_asset


_VERSION = "v1.0.0"
_DESCRIPTION = (
    "簡易視覺小說製作工具\n"
    "支援 MP4 影片導出、HTML5 網頁導出"
)


class AboutDialog(QDialog):
    """關於對話框：logo wordmark + 版本 + 描述 + 關閉。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("關於 VisualNovel Studio")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(14)

        wordmark_path = design_asset("logo-wordmark.svg")
        if wordmark_path.is_file():
            wordmark = QSvgWidget(str(wordmark_path))
            # 原圖 360x80；保留比例，固定高度
            wordmark.setFixedSize(360, 80)
            layout.addWidget(wordmark, 0, Qt.AlignmentFlag.AlignHCenter)
        else:
            # 缺檔 fallback：純文字標題
            fallback = QLabel("VisualNovel Studio")
            fallback.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            palette.register_themed(
                fallback,
                lambda p: f"color:{p.text_primary.name()}; font-size:22px; font-weight:700;",
            )
            layout.addWidget(fallback)

        version_label = QLabel(_VERSION)
        version_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        palette.register_themed(
            version_label,
            lambda p: f"color:{p.text_secondary.name()}; font-size:18px;",
        )
        layout.addWidget(version_label)

        desc_label = QLabel(_DESCRIPTION)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addSpacing(4)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)
