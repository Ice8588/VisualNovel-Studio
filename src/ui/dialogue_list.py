"""Domain 1：對話卡片列。自繪 QWidget + 手動處理拖拉重排。

固定列高 (ROW_HEIGHT)，與右側 stage/effect 共用 Y 軸。

Phase 2 移植自 experimental/timeline_poc/dialogue_column.py，import 改為正式資料模型。
"""

from __future__ import annotations

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from src.core.models import Scene
from src.ui import _timeline_shared as shared


class DialogueColumn(QWidget):
    cursor_changed = pyqtSignal(int)       # 使用者點/hover 某列
    dialogue_moved = pyqtSignal(int, int)  # src_idx, dst_idx
    selection_changed = pyqtSignal(int)    # 單選簡化版

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
        self.setMouseTracking(True)
        self.setMinimumWidth(self.WIDTH_HINT)
        self._update_height()

    def _update_height(self):
        self.setMinimumHeight(shared.idx_to_y(len(self.scene.dialogues)))

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
        idx_font = QFont("sans"); idx_font.setPixelSize(18)
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
            chip_font = QFont("sans"); chip_font.setPixelSize(18); chip_font.setBold(True)
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
            eff_font = QFont("sans"); eff_font.setPixelSize(18)
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
        # 全專案字體規範：台詞主文 ≥ 18px
        main_font = QFont("sans")
        main_font.setPixelSize(18)
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
        idx_font = QFont("sans"); idx_font.setPixelSize(18); idx_font.setBold(True)
        p.setFont(idx_font)
        p.setPen(shared.DROP_INDICATOR)
        p.drawText(
            QRect(inner.x(), inner.y(), shared.COL_INDEX_W, inner.height()),
            Qt.AlignmentFlag.AlignCenter,
            str(display_idx + 1),
        )

        # 角色欄（若有）
        if dlg.character:
            ch_font = QFont("sans"); ch_font.setPixelSize(18)
            p.setFont(ch_font)
            p.drawText(
                QRect(char_col_x, inner.y(), shared.COL_CHARACTER_W, inner.height()),
                Qt.AlignmentFlag.AlignCenter,
                dlg.character,
            )

        # 台詞欄（半透明）— ≥ 18px
        p.setOpacity(0.7)
        ghost_font = QFont("sans")
        ghost_font.setPixelSize(18)
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
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._idx_at(ev.pos().y())
        if idx is None:
            return
        self._selected_idx = idx
        self.selection_changed.emit(idx)
        self.cursor_changed.emit(idx)
        self._drag_src = idx
        self._drag_press_y = ev.pos().y()
        self._drag_current_y = ev.pos().y()
        self._is_dragging = False
        self.update()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._drag_src is not None:
            if abs(ev.pos().y() - self._drag_press_y) > shared.DRAG_THRESHOLD:
                self._is_dragging = True
            self._drag_current_y = ev.pos().y()
            self.update()
        else:
            idx = self._idx_at(ev.pos().y())
            if idx is not None and idx != self._cursor_idx:
                self._cursor_idx = idx
                self.cursor_changed.emit(idx)
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
