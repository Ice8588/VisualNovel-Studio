"""POC entry：三欄水平 + 共用 Y 軸 + 跨 domain 同步。

啟動：python -m experimental.timeline_poc.main
（從 repo root 執行，因為使用相對 import）
"""

from __future__ import annotations
import sys
from pathlib import Path

# 允許從 repo root 直接執行
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPalette, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from experimental.timeline_poc import shared
from experimental.timeline_poc.dialogue_column import DialogueColumn
from experimental.timeline_poc.effect_timeline import EffectTimelineHeader, EffectTimelineWidget
from experimental.timeline_poc.mock_data import build_mock_scene
from experimental.timeline_poc.models import EffectSegment, Scene, StageSegment, state_at
from experimental.timeline_poc.stage_panel import StageHeader, StagePanel


class PreviewPlaceholder(QWidget):
    """佔位用「假預覽」：顯示當前 dlg_idx 的 state_at。"""

    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._idx = 0
        self.setMinimumHeight(180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.title = QLabel("[ 預覽佔位 — 顯示 state_at(idx) ]")
        self.title.setStyleSheet("color:#9AA0A6; font-weight:bold;")
        layout.addWidget(self.title)

        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.body.setStyleSheet(
            "background:#0F0F11; color:#E8E8E8; "
            "font-family:Consolas,monospace; font-size:11px; border:1px solid #333;"
        )
        layout.addWidget(self.body, 1)

    def set_idx(self, idx: int):
        self._idx = idx
        self.refresh()

    def refresh(self):
        st = state_at(self.scene, self._idx)
        if not st:
            self.body.setPlainText("(超出範圍)")
            return

        def fmt_seg(label, seg):
            if seg is None:
                return f"  {label}: —"
            if isinstance(seg, StageSegment):
                return f"  {label}: {seg.character} / {seg.costume or '—'} / {seg.sprite or '—'}  ({seg.start}-{seg.end})"
            return f"  {label}: {seg}"

        lines = [
            f"dlg_idx = {self._idx}",
            f"speaker = {st['speaker']}",
            f"type    = {st['type']}",
            f"text    = {st['text']}",
            f"text_fx = {st['text_effects']}",
            "stage:",
            fmt_seg("left  ", st["stage"]["left"]),
            fmt_seg("center", st["stage"]["center"]),
            fmt_seg("right ", st["stage"]["right"]),
            "effects (active):",
        ]
        for s in st["effects"]:
            lines.append(f"  · {s.effect_type}  ({s.start}-{s.end})  params={s.params}")
        self.body.setPlainText("\n".join(lines))


class TimelineCanvas(QWidget):
    """三欄水平 widget，放進共用 QScrollArea。"""

    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.dialogue_col = DialogueColumn(scene)
        self.stage_panel = StagePanel(scene)
        self.effect_timeline = EffectTimelineWidget(scene)

        layout.addWidget(self.dialogue_col, 1)
        layout.addWidget(self.stage_panel, 0)
        layout.addWidget(self.effect_timeline, 0)
        layout.addStretch(0)

        # 確保高度一致
        h = shared.idx_to_y(len(scene.dialogues))
        self.setMinimumHeight(h)


class POCMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Timeline POC — VisualNovel Studio")
        self.resize(1280, 860)

        self.scene = build_mock_scene()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # 上：預覽（用 splitter 讓使用者調高度）
        v_split = QSplitter(Qt.Orientation.Vertical)
        self.preview = PreviewPlaceholder(self.scene)
        v_split.addWidget(self.preview)

        # 下：三欄 timeline canvas（共用 scrollarea）
        bottom_wrap = QWidget()
        bottom_layout = QVBoxLayout(bottom_wrap)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        # Header（不捲動）：對話列空白 + 三 lane 標籤 + 特效標籤
        header = self._build_header()
        bottom_layout.addWidget(header)

        # 主 canvas（捲動區）
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:#1E1E1E;")
        self.canvas = TimelineCanvas(self.scene)
        self.scroll.setWidget(self.canvas)
        bottom_layout.addWidget(self.scroll, 1)

        # 底部狀態列
        self.status = QLabel("提示：拖卡片重排對話 / 拖 segment 端點改範圍 / 雙擊空白新增 segment / Delete 刪除選取 segment / 上方「+」新增特效軌道")
        self.status.setStyleSheet("color:#9AA0A6; padding:4px 8px; background:#252526; border-top:1px solid #333;")
        bottom_layout.addWidget(self.status)

        v_split.addWidget(bottom_wrap)
        v_split.setStretchFactor(0, 0)
        v_split.setStretchFactor(1, 1)
        v_split.setSizes([200, 660])

        root.addWidget(v_split)

        self._wire_signals()
        self._apply_dark_palette()
        self.preview.set_idx(0)

    def _build_header(self) -> QWidget:
        wrap = QWidget()
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 對話欄標籤（與卡片欄等寬）
        dlg_label = QLabel("對話")
        dlg_label.setMinimumWidth(DialogueColumn.WIDTH_HINT)
        dlg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlg_label.setStyleSheet("color:#E8E8E8; background:#2D2D30; padding:6px 0; font-weight:bold;")
        layout.addWidget(dlg_label, 1)

        # 舞台 header
        stage_header = StageHeader()
        layout.addWidget(stage_header, 0)

        # 特效 header（含「+ 新增軌道」）
        self.effect_header = EffectTimelineHeader(self.scene, on_add_track=self._add_track)
        layout.addWidget(self.effect_header, 0)

        layout.addStretch(0)
        return wrap

    def _wire_signals(self):
        c = self.canvas
        # 卡片欄 → 預覽 + 其他兩欄游標
        c.dialogue_col.cursor_changed.connect(self._on_cursor)
        c.dialogue_col.dialogue_moved.connect(self._on_dialogue_moved)
        c.dialogue_col.selection_changed.connect(self._on_cursor)

        # 舞台 → 預覽 + 其他兩欄游標
        c.stage_panel.cursor_changed.connect(self._on_cursor)
        c.stage_panel.segment_changed.connect(self.preview.refresh)
        c.stage_panel.segment_selected.connect(lambda s: self._show_payload("stage", s))

        # 特效 → 預覽 + 其他兩欄游標
        c.effect_timeline.cursor_changed.connect(self._on_cursor)
        c.effect_timeline.segment_changed.connect(self.preview.refresh)
        c.effect_timeline.segment_selected.connect(lambda s: self._show_payload("effect", s))

    def _on_cursor(self, idx: int):
        self.canvas.dialogue_col.set_cursor(idx)
        self.canvas.stage_panel.set_cursor(idx)
        self.canvas.effect_timeline.set_cursor(idx)
        self.preview.set_idx(idx)

    def _on_dialogue_moved(self, src: int, dst: int):
        self.scene.move_dialogue(src, dst)
        self.canvas.dialogue_col.refresh()
        self.canvas.stage_panel.refresh()
        self.canvas.effect_timeline.refresh()
        self.preview.refresh()
        self.status.setText(f"已重排對話：{src + 1} → {dst + 1}（其他軌道 segment 已自動同步）")

    def _add_track(self, name: str):
        self.canvas.effect_timeline.add_track(name)
        self.effect_header.append_track(name)
        self.status.setText(f"已新增特效軌道：{name}")

    def _show_payload(self, domain: str, seg):
        if seg is None:
            return
        if isinstance(seg, StageSegment):
            self.status.setText(
                f"[舞台 segment] {seg.character} / {seg.costume} / {seg.sprite}  範圍 {seg.start}-{seg.end}"
            )
        elif isinstance(seg, EffectSegment):
            self.status.setText(
                f"[特效 segment] {seg.effect_type}  範圍 {seg.start}-{seg.end}  params={seg.params}"
            )

    def _apply_dark_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#1E1E1E"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#E8E8E8"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#252526"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#E8E8E8"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#2D2D30"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#E8E8E8"))
        self.setPalette(pal)
        self.setStyleSheet(
            "QMainWindow{background:#1E1E1E;} "
            "QSplitter::handle{background:#3D3D40;}"
        )


def main():
    app = QApplication(sys.argv)
    win = POCMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
