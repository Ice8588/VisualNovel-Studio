"""Phase 2：選中 segment 時顯示對應 payload 的 inline 編輯器。

模式：
- StageSegment：Character / Costume / Sprite 級聯 ComboBox
- EffectSegment：effect_type ComboBox + params JSON 編輯器
- None：placeholder
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QStackedLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import BodyLabel, ComboBox

from src.core.models import EffectSegment, StageSegment
from src.ui.icons import design_icon_tinted

if TYPE_CHECKING:
    from src.core.models import Project


_KNOWN_EFFECT_TYPES = ["rain", "snow", "crt", "screen_shake", "pixel_dark"]


class SegmentEditor(QWidget):
    """選中 segment 時顯示對應 payload 的 inline 編輯器（Phase 4 改為浮動視窗）。"""

    segment_changed = pyqtSignal()  # payload 改動（UI 端需重繪 / 預覽 refresh）
    closed = pyqtSignal()           # Phase 4：使用者按 X 或 ESC 關閉浮動視窗

    # 方便單測以字串比對模式
    MODE_NONE = "none"
    MODE_STAGE = "stage"
    MODE_EFFECT = "effect"

    def __init__(self, project_ref=None, parent=None):
        super().__init__(parent)
        self._project: "Project | None" = project_ref
        self._segment: object | None = None
        self._suppress_signals: bool = False
        # Phase 4：浮動視窗外觀（陰影 + 邊框 + 圓角）
        self.setObjectName("segmentEditorPopup")
        self.setStyleSheet(
            "#segmentEditorPopup { background:#2D2D30; border:1px solid #3D8AC4;"
            " border-radius:6px; }"
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # 收 ESC
        self._build_ui()
        self.set_segment(None)

    # ── 對外 API ─────────────────────────────────────────────

    def set_project(self, project) -> None:
        self._project = project
        # 若正在編輯 StageSegment，更新下拉內容
        if isinstance(self._segment, StageSegment):
            self._load_stage_segment(self._segment)

    def set_segment(self, seg) -> None:
        self._segment = seg
        if seg is None:
            self._stack.setCurrentIndex(0)  # placeholder
            return
        if isinstance(seg, StageSegment):
            self._stack.setCurrentIndex(1)
            self._load_stage_segment(seg)
        elif isinstance(seg, EffectSegment):
            self._stack.setCurrentIndex(2)
            self._load_effect_segment(seg)
        else:
            self._stack.setCurrentIndex(0)

    def current_mode(self) -> str:
        idx = self._stack.currentIndex()
        return (self.MODE_NONE, self.MODE_STAGE, self.MODE_EFFECT)[idx]

    # ── UI 建構 ─────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Header：標題 + 關閉 X 鈕
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._title = BodyLabel("Segment 編輯器")
        self._title.setFont(QFont("sans", 10, QFont.Weight.Bold))
        header.addWidget(self._title, 1)
        # 浮動視窗背景固定為深色 (#2D2D30)，icon 用淺色才看得到
        self._btn_close = QToolButton()
        self._btn_close.setIcon(design_icon_tinted("close", "#9AA0A6"))
        self._btn_close.setIconSize(QSize(14, 14))
        self._btn_close.setToolTip("關閉")
        self._btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_close.setStyleSheet(
            "QToolButton { border:none; padding:2px 6px; }"
            "QToolButton:hover { background:rgba(255,255,255,0.08); border-radius:3px; }"
        )
        self._btn_close.clicked.connect(self.closed.emit)
        header.addWidget(self._btn_close, 0)
        root.addLayout(header)

        self._stack = QStackedLayout()
        root.addLayout(self._stack, 1)

        # 0: placeholder
        ph = QWidget()
        ph_layout = QVBoxLayout(ph)
        ph_layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder_label = QLabel("未選取 segment")
        self._placeholder_label.setStyleSheet("color:#9AA0A6;")
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.addWidget(self._placeholder_label)
        self._stack.addWidget(ph)

        # 1: stage segment
        stage = QWidget()
        form_stage = QFormLayout(stage)
        form_stage.setContentsMargins(0, 0, 0, 0)
        form_stage.setSpacing(6)
        self._cb_character = ComboBox()
        self._cb_costume = ComboBox()
        self._cb_sprite = ComboBox()
        self._cb_character.currentTextChanged.connect(self._on_stage_character_changed)
        self._cb_costume.currentTextChanged.connect(self._on_stage_costume_changed)
        self._cb_sprite.currentTextChanged.connect(self._on_stage_sprite_changed)
        form_stage.addRow(BodyLabel("角色"), self._cb_character)
        form_stage.addRow(BodyLabel("服裝"), self._cb_costume)
        form_stage.addRow(BodyLabel("差分"), self._cb_sprite)
        self._stack.addWidget(stage)

        # 2: effect segment
        effect = QWidget()
        form_effect = QFormLayout(effect)
        form_effect.setContentsMargins(0, 0, 0, 0)
        form_effect.setSpacing(6)
        self._cb_effect_type = ComboBox()
        self._cb_effect_type.addItems(_KNOWN_EFFECT_TYPES)
        self._cb_effect_type.currentTextChanged.connect(self._on_effect_type_changed)
        self._params_edit = QPlainTextEdit()
        self._params_edit.setPlaceholderText('{"intensity": 0.5}')
        self._params_edit.setMaximumHeight(80)
        self._params_edit.setFont(QFont("monospace", 9))
        self._params_edit.installEventFilter(self)
        form_effect.addRow(BodyLabel("特效類型"), self._cb_effect_type)
        form_effect.addRow(BodyLabel("Params (JSON)"), self._params_edit)
        self._stack.addWidget(effect)

    # ── StageSegment 模式 ──────────────────────────────────

    def _load_stage_segment(self, seg: StageSegment) -> None:
        self._suppress_signals = True
        try:
            self._cb_character.clear()
            chars = list(self._project.characters) if self._project else []
            for c in chars:
                self._cb_character.addItem(c.name)
            if not chars:
                self._cb_character.addItem(seg.character or "")
            # 選中當前角色
            idx = self._cb_character.findText(seg.character or "")
            if idx < 0:
                self._cb_character.insertItem(0, seg.character or "")
                idx = 0
            self._cb_character.setCurrentIndex(idx)

            self._reload_costume_options(seg.character, seg.costume)
            self._reload_sprite_options(seg.character, seg.costume, seg.sprite)
        finally:
            self._suppress_signals = False

    def _reload_costume_options(self, character: str | None, preferred: str | None) -> None:
        self._cb_costume.clear()
        char_obj = self._find_character(character)
        names = [c.name for c in (char_obj.costumes if char_obj else [])]
        self._cb_costume.addItems(["（無）"] + names)
        if preferred and preferred in names:
            self._cb_costume.setCurrentText(preferred)
        else:
            self._cb_costume.setCurrentIndex(0)

    def _reload_sprite_options(self, character: str | None, costume: str | None, preferred: str | None) -> None:
        self._cb_sprite.clear()
        char_obj = self._find_character(character)
        cos_obj = None
        if char_obj and costume:
            cos_obj = next((c for c in char_obj.costumes if c.name == costume), None)
        labels = [e.label for e in (cos_obj.expressions if cos_obj else [])]
        self._cb_sprite.addItems(["（無）"] + labels)
        if preferred and preferred in labels:
            self._cb_sprite.setCurrentText(preferred)
        else:
            self._cb_sprite.setCurrentIndex(0)

    def _find_character(self, name: str | None):
        if not name or not self._project:
            return None
        return next((c for c in self._project.characters if c.name == name), None)

    def _on_stage_character_changed(self, new_name: str) -> None:
        if self._suppress_signals or not isinstance(self._segment, StageSegment):
            return
        self._segment.character = new_name
        # cascade reset：角色變 → 服裝改為第一個（或 None）、差分同步
        self._suppress_signals = True
        try:
            self._reload_costume_options(new_name, None)
            new_costume = self._combo_value(self._cb_costume)
            self._segment.costume = new_costume
            self._reload_sprite_options(new_name, new_costume, None)
            self._segment.sprite = self._combo_value(self._cb_sprite)
        finally:
            self._suppress_signals = False
        self.segment_changed.emit()

    def _on_stage_costume_changed(self, new_costume: str) -> None:
        if self._suppress_signals or not isinstance(self._segment, StageSegment):
            return
        value = None if new_costume == "（無）" else new_costume
        self._segment.costume = value
        self._suppress_signals = True
        try:
            self._reload_sprite_options(self._segment.character, value, None)
            self._segment.sprite = self._combo_value(self._cb_sprite)
        finally:
            self._suppress_signals = False
        self.segment_changed.emit()

    def _on_stage_sprite_changed(self, new_sprite: str) -> None:
        if self._suppress_signals or not isinstance(self._segment, StageSegment):
            return
        self._segment.sprite = None if new_sprite == "（無）" else new_sprite
        self.segment_changed.emit()

    @staticmethod
    def _combo_value(cb: ComboBox) -> str | None:
        v = cb.currentText()
        return None if (not v or v == "（無）") else v

    # ── EffectSegment 模式 ─────────────────────────────────

    def _load_effect_segment(self, seg: EffectSegment) -> None:
        self._suppress_signals = True
        try:
            if self._cb_effect_type.findText(seg.effect_type) < 0:
                self._cb_effect_type.insertItem(0, seg.effect_type)
            self._cb_effect_type.setCurrentText(seg.effect_type)
            self._params_edit.setPlainText(
                json.dumps(seg.params, ensure_ascii=False, indent=2) if seg.params else ""
            )
        finally:
            self._suppress_signals = False

    def _on_effect_type_changed(self, new_type: str) -> None:
        if self._suppress_signals or not isinstance(self._segment, EffectSegment):
            return
        self._segment.effect_type = new_type
        self.segment_changed.emit()

    def eventFilter(self, obj, event):
        # params 編輯框 blur（失焦）時嘗試寫回 JSON
        if obj is self._params_edit and event.type().name == "FocusOut":
            self._commit_params_json()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.closed.emit()
            return
        super().keyPressEvent(event)

    def _commit_params_json(self) -> None:
        if not isinstance(self._segment, EffectSegment):
            return
        text = self._params_edit.toPlainText().strip()
        if not text:
            if self._segment.params:
                self._segment.params = {}
                self.segment_changed.emit()
            return
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                return  # 非 dict 不寫回
            self._segment.params = parsed
            self.segment_changed.emit()
        except json.JSONDecodeError:
            # 解析失敗：保持原值，不 emit；使用者可繼續編輯
            return
