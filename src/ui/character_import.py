"""「從其他作品匯入角色」對話框：列出來源作品的角色，勾選後匯入。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import BodyLabel, ListWidget, StrongBodyLabel

from src.core.models import Character, Project


def _char_thumb(char: Character, assets_dir: Path) -> QPixmap:
    """角色縮圖：第一張立繪縮放 40px；無立繪用名牌色色塊。"""
    if char.sprites:
        path = assets_dir / char.sprites[0].filename
        if path.exists():
            pm = QPixmap(str(path))
            if not pm.isNull():
                return pm.scaled(
                    40, 40,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
    pm = QPixmap(40, 40)
    pm.fill(QColor(char.name_color))
    return pm


class CharacterImportDialog(QDialog):
    """勾選來源作品中要帶進本作品的角色（預設全勾）。"""

    def __init__(self, source_project: Project, source_assets: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self._chars = source_project.characters
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(f"從「{source_project.title}」匯入角色")
        self.setMinimumSize(380, 360)

        layout = QVBoxLayout()
        layout.addWidget(StrongBodyLabel("勾選要帶進本作品的角色："))
        self._char_list = ListWidget()
        self._char_list.setIconSize(QSize(40, 40))
        for char in self._chars:
            item = QListWidgetItem(
                f"{char.name}（{len(char.costumes)} 套服裝 · {len(char.sprites)} 張差分）"
            )
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setIcon(QIcon(_char_thumb(char, Path(source_assets))))
            self._char_list.addItem(item)
        layout.addWidget(self._char_list)
        layout.addWidget(BodyLabel("匯入會把角色連同立繪複製進本作品，之後與來源作品互不影響。"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def selected_characters(self) -> list[Character]:
        return [
            c for i, c in enumerate(self._chars)
            if self._char_list.item(i).checkState() == Qt.CheckState.Checked
        ]
