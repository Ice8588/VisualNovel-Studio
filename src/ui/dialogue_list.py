"""Domain 1：對話卡片列。自繪 QWidget + 手動處理拖拉重排。

固定列高 (ROW_HEIGHT)，與右側 stage/effect 共用 Y 軸。

Phase 2 移植自 experimental/timeline_poc/dialogue_column.py，import 改為正式資料模型。
"""

from __future__ import annotations

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from src.core.models import Dialogue, Scene
from src.ui import _timeline_shared as shared


class DialogueColumn(QWidget):
    cursor_changed = pyqtSignal(int)       # 使用者點/hover 某列
    dialogue_moved = pyqtSignal(int, int)  # src_idx, dst_idx
    selection_changed = pyqtSignal(int)    # 單選簡化版
    speaker_changed = pyqtSignal(int)      # task.md #8：點 chip 改說話者
    content_changed = pyqtSignal()         # Task 6：刪除 / 編輯文字 / 插入 等內容變更

    WIDTH_HINT = 360

    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._cursor_idx: int | None = None
        self._selected_idx: int | None = None
        self._drag_src: int | None = None
        self._drag_press_y: int = 0
        self._drag_current_y: int = 0
        self._is_dragging: bool = False
        self._character_colors: dict[str, str] = {}
        self._text_editor = None  # Task 6：inline 文字編輯 overlay（同時最多一個）
        self.setMouseTracking(True)
        self.setMinimumWidth(self.WIDTH_HINT)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)  # Task 6：收 keyPress（Delete / Ctrl+C）
        self._update_height()

    def _update_height(self):
        self.setMinimumHeight(shared.idx_to_y(len(self.scene.dialogues)))

    def _font_size_px(self) -> int:
        """task.md #12：自繪文字大小跟 QApplication 主 font；fallback 20。"""
        sz = self.font().pixelSize()
        if sz <= 0:
            # pointSize 退回估算（pt → px 約 1.33 倍）
            pt = self.font().pointSize()
            sz = int(pt * 1.33) if pt > 0 else 20
        return max(18, min(28, sz))

    def set_cursor(self, idx: int | None):
        if idx == self._cursor_idx:
            return
        self._cursor_idx = idx
        self.update()

    def set_character_colors(self, mapping: dict[str, str]) -> None:
        """MainWindow 指定角色 → name_color 的映射，供卡片繪 chip 時使用。"""
        self._character_colors = dict(mapping or {})
        self.update()

    def refresh(self):
        self._update_height()
        self.update()

    # --- 繪製 ---

    def _build_display_list(self) -> list[tuple[int, object, bool]]:
        """回傳 [(display_idx, dlg, is_ghost), ...]。

        - 非拖拉狀態：照原順序、is_ghost 全 False。
        - 拖拉狀態：模擬「pop src + insert at predicted dst」後的排列，
          被拖的那一列回傳 is_ghost=True；其他卡片的 display_idx 已是
          drop 後的最終位置，因此自然「讓出空間」。
        """
        if not (self._is_dragging and self._drag_src is not None):
            return [(i, d, False) for i, d in enumerate(self.scene.dialogues)]

        src = self._drag_src
        insert_at = self._drop_target_idx(self._drag_current_y)
        # pop(src) + insert(final_pos)；對應 mouseRelease 的計算
        final_pos = insert_at if insert_at <= src else insert_at - 1
        final_pos = max(0, min(final_pos, len(self.scene.dialogues) - 1))

        rest = [d for i, d in enumerate(self.scene.dialogues) if i != src]
        new_list = rest[:final_pos] + [self.scene.dialogues[src]] + rest[final_pos:]
        return [(i, d, i == final_pos) for i, d in enumerate(new_list)]

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), shared.BG_PANEL)

        display = self._build_display_list()
        for display_idx, dlg, is_ghost in display:
            top = shared.idx_to_y(display_idx)
            rect = QRect(0, top, self.width(), shared.ROW_HEIGHT)
            if is_ghost:
                self._paint_ghost_card(p, rect, display_idx, dlg)
            else:
                self._paint_card(p, rect, display_idx, dlg)

        # Phase 4：原本的橫向虛線游標移除；現在用「左豎條 + 卡片暖色 tint」標示當前對話。
        # 舞台 / 特效 lane 的虛線游標保留作為 Y 軸對齊輔助。

        p.end()

    def _paint_card(self, p: QPainter, rect: QRect, idx: int, dlg):
        inner = rect.adjusted(6, 4, -6, -4)

        # 卡片底色（主題感知）
        is_narration = dlg.type == "narration"
        is_selected = idx == self._selected_idx
        is_current = idx == self._cursor_idx  # Phase 4：當前預覽位置
        bg = shared.CARD_NARRATION_BG if is_narration else shared.CARD_DIALOGUE_BG
        if is_current:
            # 當前對話：朝 CURSOR_LINE (#FFB300 暖橘) 混合 25% 取得 tint，
            # 同時適用深淺色——深色底會變亮、淺色底會變暖黃。
            cl = shared.CURSOR_LINE
            t = 0.25
            bg = QColor(
                round(bg.red()   * (1 - t) + cl.red()   * t),
                round(bg.green() * (1 - t) + cl.green() * t),
                round(bg.blue()  * (1 - t) + cl.blue()  * t),
            )
        elif is_selected:
            bg = bg.lighter(115) if shared.is_light() else bg.lighter(130)
        p.setBrush(bg)
        p.setPen(QPen(shared.GRID_LINE, 1))
        p.drawRoundedRect(inner, 6, 6)

        # 當前對話：左側 4px 豎條（最顯眼的「正在這裡」標示）
        if is_current:
            bar_rect = QRect(inner.x(), inner.y() + 2, 4, inner.height() - 4)
            p.setBrush(shared.CURSOR_LINE)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(bar_rect, 2, 2)

        # 選中邊框（次要：和 current 不同視覺；只在「不是當前」時加邊框）
        if is_selected and not is_current:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(shared.CURSOR_LINE, 2))
            p.drawRoundedRect(inner.adjusted(1, 1, -1, -1), 6, 6)

        # 三欄區塊邊界（任務 #9：索引｜角色｜台詞 顯式分欄）
        idx_col_x = inner.x()
        char_col_x = idx_col_x + shared.COL_INDEX_W
        text_col_x = char_col_x + shared.COL_CHARACTER_W

        # 欄分隔線（垂直細線，跟主題感知）
        p.setPen(QPen(shared.GRID_LINE, 1))
        p.drawLine(char_col_x, inner.y() + 4, char_col_x, inner.bottom() - 4)
        p.drawLine(text_col_x, inner.y() + 4, text_col_x, inner.bottom() - 4)

        # ── 索引欄：數字 + 類型 icon（▶ 對話 / ▒ 旁白）──
        idx_text = str(idx + 1)
        icon = "▶" if not is_narration else "▒"
        idx_font = shared.ui_sans_font(self._font_size_px(), base=self.font())
        p.setFont(idx_font)
        # 數字置左半，icon 置右半
        half = shared.COL_INDEX_W // 2
        p.setPen(shared.TEXT_MUTED)
        p.drawText(
            QRect(idx_col_x, inner.y(), half, inner.height()),
            Qt.AlignmentFlag.AlignCenter, idx_text,
        )
        p.setPen(shared.TEXT_MUTED if is_narration else shared.TEXT_PRIMARY)
        p.drawText(
            QRect(idx_col_x + half, inner.y(), half, inner.height()),
            Qt.AlignmentFlag.AlignCenter, icon,
        )

        # ── 角色欄：chip 居中 ──
        if dlg.character:
            chip_color = shared.character_color(
                dlg.character, self._character_colors.get(dlg.character)
            )
            chip_font = shared.ui_sans_font(self._font_size_px(), bold=True, base=self.font())
            metrics = QFontMetrics(chip_font)
            label = dlg.character
            chip_w = min(
                shared.COL_CHARACTER_W - 12,
                metrics.horizontalAdvance(label) + 16,
            )
            chip_h = 30  # 18px font + ~6px 上下留白
            chip_rect = QRect(
                char_col_x + (shared.COL_CHARACTER_W - chip_w) // 2,
                inner.y() + (inner.height() - chip_h) // 2,
                chip_w, chip_h,
            )
            p.setBrush(chip_color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(chip_rect, 11, 11)
            from src.ui import palette as _pal
            p.setFont(chip_font)
            p.setPen(_pal.contrast_text(chip_color))
            elided_lbl = metrics.elidedText(label, Qt.TextElideMode.ElideRight, chip_w - 8)
            p.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, elided_lbl)

        # ── 台詞欄 ──
        text_x = text_col_x + 8
        text_right = inner.right() - 4

        # 文字效果 chip（右側貼邊；在台詞欄內）— 字體 ≥ 18px
        if dlg.text_effects:
            eff_label = " ".join(f"·{e}" for e in dlg.text_effects)
            eff_font = shared.ui_sans_font(self._font_size_px(), base=self.font())
            metrics = QFontMetrics(eff_font)
            chip_w = metrics.horizontalAdvance(eff_label) + 12
            chip_h = 28
            chip_rect = QRect(
                text_right - chip_w,
                inner.y() + (inner.height() - chip_h) // 2,
                chip_w, chip_h,
            )
            chip_bg = QColor(0, 0, 0, 30) if shared.is_light() else QColor(255, 255, 255, 30)
            p.setBrush(chip_bg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(chip_rect, 8, 8)
            p.setFont(eff_font)
            p.setPen(shared.TEXT_MUTED)
            p.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, eff_label)
            text_right -= chip_w + 6

        text_rect = QRect(text_x, inner.y(), text_right - text_x, inner.height())
        # 全專案字體規範：台詞主文 ≥ 18px；用 ui sans fallback chain 並繼承 app font 大小
        main_font = shared.ui_sans_font(self._font_size_px(), base=self.font())
        p.setFont(main_font)
        p.setPen(shared.TEXT_PRIMARY if not is_narration else shared.TEXT_MUTED)
        metrics = QFontMetrics(p.font())
        elided = metrics.elidedText(dlg.text, Qt.TextElideMode.ElideRight, text_rect.width())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

    def _paint_ghost_card(self, p: QPainter, rect: QRect, display_idx: int, dlg):
        """拖拉中的「目標位置」幽靈卡：虛線邊框 + 淡色，標示「放開後會在這裡」。"""
        inner = rect.adjusted(6, 4, -6, -4)
        p.setBrush(QColor(shared.DROP_INDICATOR.red(), shared.DROP_INDICATOR.green(),
                          shared.DROP_INDICATOR.blue(), 40))
        p.setPen(QPen(shared.DROP_INDICATOR, 2, Qt.PenStyle.DashLine))
        p.drawRoundedRect(inner, 6, 6)

        # 三欄分隔線（虛線淡色）
        char_col_x = inner.x() + shared.COL_INDEX_W
        text_col_x = char_col_x + shared.COL_CHARACTER_W
        p.setPen(QPen(shared.GRID_LINE, 1))
        p.drawLine(char_col_x, inner.y() + 4, char_col_x, inner.bottom() - 4)
        p.drawLine(text_col_x, inner.y() + 4, text_col_x, inner.bottom() - 4)

        # 索引欄
        idx_font = shared.ui_sans_font(self._font_size_px(), bold=True, base=self.font())
        p.setFont(idx_font)
        p.setPen(shared.DROP_INDICATOR)
        p.drawText(
            QRect(inner.x(), inner.y(), shared.COL_INDEX_W, inner.height()),
            Qt.AlignmentFlag.AlignCenter,
            str(display_idx + 1),
        )

        # 角色欄（若有）
        if dlg.character:
            ch_font = shared.ui_sans_font(self._font_size_px(), base=self.font())
            p.setFont(ch_font)
            p.drawText(
                QRect(char_col_x, inner.y(), shared.COL_CHARACTER_W, inner.height()),
                Qt.AlignmentFlag.AlignCenter,
                dlg.character,
            )

        # 台詞欄（半透明）— ≥ 18px
        p.setOpacity(0.7)
        ghost_font = shared.ui_sans_font(self._font_size_px(), base=self.font())
        p.setFont(ghost_font)
        p.setPen(shared.TEXT_PRIMARY)
        text_rect = QRect(text_col_x + 8, inner.y(),
                          inner.right() - text_col_x - 12, inner.height())
        metrics = QFontMetrics(p.font())
        label = metrics.elidedText(dlg.text, Qt.TextElideMode.ElideRight, text_rect.width())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
        p.setOpacity(1.0)

    # --- 互動 ---

    def _idx_at(self, y: int) -> int | None:
        idx = y // shared.ROW_HEIGHT
        if 0 <= idx < len(self.scene.dialogues):
            return idx
        return None

    def _drop_target_idx(self, y: int) -> int:
        """拖拉放開時的目標位置（插入點）。"""
        raw = y // shared.ROW_HEIGHT
        if (y % shared.ROW_HEIGHT) > shared.ROW_HEIGHT // 2:
            raw += 1
        return max(0, min(raw, len(self.scene.dialogues)))

    def mousePressEvent(self, ev: QMouseEvent):
        self.setFocus()  # Task 6：收 keyPress（Delete / Ctrl+C）
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._idx_at(ev.pos().y())
        if idx is None:
            return
        # 先選中該行（讓預覽跟上）
        self._selected_idx = idx
        self.selection_changed.emit(idx)
        self.cursor_changed.emit(idx)

        # task.md #8：點到角色欄就彈 ComboBox（不啟動 drag）
        char_rect = self._character_col_rect(idx)
        if char_rect.contains(ev.pos()):
            self._popup_speaker_combo(idx, char_rect)
            self.update()
            return

        self._drag_src = idx
        self._drag_press_y = ev.pos().y()
        self._drag_current_y = ev.pos().y()
        self._is_dragging = False
        self.update()

    def _character_col_rect(self, idx: int) -> QRect:
        """回傳該 row 角色欄的命中區（與 paintEvent 計算一致）。"""
        rect = QRect(0, idx * shared.ROW_HEIGHT, self.width(), shared.ROW_HEIGHT)
        inner = rect.adjusted(6, 4, -6, -4)
        idx_col_x = inner.x()
        char_col_x = idx_col_x + shared.COL_INDEX_W
        return QRect(char_col_x, inner.y(), shared.COL_CHARACTER_W, inner.height())

    def _popup_speaker_combo(self, idx: int, anchor: QRect) -> None:
        """task.md #8：浮動 ComboBox 改說話者，選完即套用。"""
        from qfluentwidgets import ComboBox
        combo = ComboBox(self)
        combo.addItem("（無）")
        names = list(self._character_colors.keys())
        for name in names:
            combo.addItem(name)
        cur = self.scene.dialogues[idx].character
        if cur and cur in names:
            combo.setCurrentText(cur)
        else:
            combo.setCurrentIndex(0)

        def on_text_changed(text: str) -> None:
            new_speaker = None if text == "（無）" else text
            dlg = self.scene.dialogues[idx]
            if dlg.character == new_speaker:
                combo.deleteLater()
                return
            dlg.character = new_speaker
            self.speaker_changed.emit(idx)
            self.update()
            combo.deleteLater()

        combo.currentTextChanged.connect(on_text_changed)
        combo.setGeometry(
            anchor.x(), anchor.y(),
            max(140, anchor.width()), max(28, anchor.height()),
        )
        combo.show()
        combo.raise_()
        # qfluentwidgets ComboBox（v1.11.2）不是 QComboBox 子類，沒有 showPopup()。
        # 正確的展開方法是 _showComboMenu()；使用 hasattr 防衛以避免未來版本異動時崩潰。
        if hasattr(combo, "_showComboMenu"):
            combo._showComboMenu()  # noqa: SLF001 — 依賴 qfluentwidgets 1.11.2 內部 API

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._drag_src is not None:
            if abs(ev.pos().y() - self._drag_press_y) > shared.DRAG_THRESHOLD:
                self._is_dragging = True
            self._drag_current_y = ev.pos().y()
            self.update()
        else:
            # task.md #3：hover 只更新本 widget 視覺 cursor，不再 emit
            # cursor_changed（避免預覽頻繁跳動）。換預覽由 mousePressEvent 觸發。
            idx = self._idx_at(ev.pos().y())
            if idx is not None and idx != self._cursor_idx:
                self._cursor_idx = idx
                self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if self._drag_src is None:
            return
        if self._is_dragging:
            dst = self._drop_target_idx(ev.pos().y())
            # 正規化：dst 是插入點，如果 src < dst，實際移動到 dst-1
            if dst > self._drag_src:
                dst -= 1
            if dst != self._drag_src:
                self.dialogue_moved.emit(self._drag_src, dst)
                self._selected_idx = dst
        self._drag_src = None
        self._is_dragging = False
        self.update()

    # --- Task 6：刪除 / 複製（鍵盤） ---

    def keyPressEvent(self, ev: QKeyEvent):
        """Delete/Backspace 刪除選取句；Ctrl+C 複製選取句文字。"""
        if ev.matches(QKeySequence.StandardKey.Copy):
            if self._selected_idx is not None and 0 <= self._selected_idx < len(self.scene.dialogues):
                QApplication.clipboard().setText(self.scene.dialogues[self._selected_idx].text)
                ev.accept()
                return
        if ev.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            idx = self._selected_idx
            if idx is not None and 0 <= idx < len(self.scene.dialogues):
                self._delete_dialogue(idx)
                ev.accept()
                return
        super().keyPressEvent(ev)

    def _delete_dialogue(self, idx: int) -> None:
        """經 Scene.remove_dialogue 刪除（自動 shift segment），再修正選取 / 游標。"""
        self.scene.remove_dialogue(idx)
        n = len(self.scene.dialogues)
        if n == 0:
            self._selected_idx = None
            self._cursor_idx = None
        else:
            self._selected_idx = min(idx, n - 1)
            if self._cursor_idx is not None:
                self._cursor_idx = min(self._cursor_idx, n - 1)
        self.refresh()
        self.content_changed.emit()

    # --- Task 6：雙擊編輯文字（inline overlay） ---

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        idx = self._idx_at(ev.pos().y())
        if idx is None:
            return
        # 角色欄交給 _popup_speaker_combo（單擊已處理）；雙擊角色欄不開文字編輯
        if self._character_col_rect(idx).contains(ev.pos()):
            return
        self._begin_text_edit(idx)

    def _text_col_rect(self, idx: int) -> QRect:
        """回傳該 row 台詞欄的命中區（與 paintEvent 三欄計算一致）。"""
        rect = QRect(0, idx * shared.ROW_HEIGHT, self.width(), shared.ROW_HEIGHT)
        inner = rect.adjusted(6, 4, -6, -4)
        text_col_x = inner.x() + shared.COL_INDEX_W + shared.COL_CHARACTER_W
        return QRect(text_col_x, inner.y(), inner.right() - text_col_x, inner.height())

    def _begin_text_edit(self, idx: int) -> None:
        """在台詞欄浮一個 LineEdit 編輯文字；Enter/失焦提交、Esc 取消。"""
        from qfluentwidgets import LineEdit

        if self._text_editor is not None:
            self._text_editor.deleteLater()
            self._text_editor = None

        self._selected_idx = idx
        editor = LineEdit(self)
        editor.setText(self.scene.dialogues[idx].text)
        editor.selectAll()
        anchor = self._text_col_rect(idx)
        editor.setGeometry(anchor.x(), anchor.y(), anchor.width(), max(28, anchor.height()))
        self._text_editor = editor
        self._edit_committed = False  # 防 Enter + focusOut 重複提交

        def commit() -> None:
            if self._edit_committed:
                return
            self._edit_committed = True
            self._commit_text_edit(idx, editor.text())

        def cancel() -> None:
            if self._edit_committed:
                return
            self._edit_committed = True
            self._close_text_editor()

        editor.returnPressed.connect(commit)
        editor.editingFinished.connect(commit)  # 失焦提交

        # Esc 取消：覆寫 keyPressEvent
        def key_press(ev: QKeyEvent, _orig=editor.keyPressEvent) -> None:
            if ev.key() == Qt.Key.Key_Escape:
                cancel()
                return
            _orig(ev)

        editor.keyPressEvent = key_press
        editor.show()
        editor.raise_()
        editor.setFocus()

    def _commit_text_edit(self, idx: int, new_text: str) -> None:
        """提交 inline 編輯：strip 後同原文或空 → 不套用；否則更新並重判 type。"""
        from src.core.text_parser import classify_line

        if not (0 <= idx < len(self.scene.dialogues)):
            self._close_text_editor()
            return
        dlg = self.scene.dialogues[idx]
        stripped = new_text.strip()
        if not stripped or stripped == dlg.text:
            self._close_text_editor()
            return
        dlg.text = stripped
        new_type = classify_line(stripped)
        if new_type == "dialogue":
            dlg.type = "dialogue"  # character 保留原值
        else:
            dlg.type = "narration"
            dlg.character = None
        self._close_text_editor()
        self.refresh()
        self.content_changed.emit()

    def _close_text_editor(self) -> None:
        if self._text_editor is not None:
            self._text_editor.deleteLater()
            self._text_editor = None
        self.update()

    # --- Task 6：右鍵選單（編輯 / 插入 / 刪除） ---

    def contextMenuEvent(self, ev):
        menu = QMenu(self)
        idx = self._idx_at(ev.pos().y())
        if idx is not None:
            self._selected_idx = idx
            self.update()
            menu.addAction("編輯文字", lambda: self._begin_text_edit(idx))
            menu.addAction("在下方插入台詞", lambda: self._insert_dialogue_after(idx, "dialogue"))
            menu.addAction("在下方插入旁白", lambda: self._insert_dialogue_after(idx, "narration"))
            menu.addSeparator()
            menu.addAction("刪除此句", lambda: self._delete_dialogue(idx))
        else:
            menu.addAction("新增台詞", lambda: self._append_dialogue("dialogue"))
            menu.addAction("新增旁白", lambda: self._append_dialogue("narration"))
        menu.exec(ev.globalPos())

    def _new_dialogue(self, kind: str) -> Dialogue:
        """依類型建立預設新句：台詞 text=「」、旁白 text=""。"""
        if kind == "dialogue":
            return Dialogue(type="dialogue", text="「」", character=None)
        return Dialogue(type="narration", text="", character=None)

    def _insert_dialogue_after(self, idx: int, kind: str) -> None:
        """在 idx 下方插入新句，選中並立即開編輯 overlay。"""
        new_idx = idx + 1
        self.scene.insert_dialogue(new_idx, self._new_dialogue(kind))
        self._select_and_edit_new(new_idx)

    def _append_dialogue(self, kind: str) -> None:
        """在末尾新增新句，選中並立即開編輯 overlay。"""
        new_idx = len(self.scene.dialogues)
        self.scene.insert_dialogue(new_idx, self._new_dialogue(kind))
        self._select_and_edit_new(new_idx)

    def _select_and_edit_new(self, new_idx: int) -> None:
        self._selected_idx = new_idx
        self.refresh()
        self.content_changed.emit()
        self._begin_text_edit(new_idx)
