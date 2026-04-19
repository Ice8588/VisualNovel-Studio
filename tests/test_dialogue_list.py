"""DialogueColumn（src/ui/dialogue_list.py）widget 測試。

需要 QT_QPA_PLATFORM=offscreen 執行。
"""

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent

from src.core.models import Dialogue, Scene
from src.ui import _timeline_shared as shared
from src.ui.dialogue_list import DialogueColumn


# qapp fixture 來自 tests/conftest.py（session scope）


def _make_scene(n: int = 4) -> Scene:
    return Scene(
        id="s1",
        dialogues=[
            Dialogue(type="dialogue" if i % 2 == 0 else "narration",
                     text=f"台詞{i}",
                     character="小明" if i % 2 == 0 else None)
            for i in range(n)
        ],
    )


def _mouse_event(kind, y: int, button=Qt.MouseButton.LeftButton) -> QMouseEvent:
    pos = QPointF(20.0, float(y))
    return QMouseEvent(kind, pos, pos, button, button, Qt.KeyboardModifier.NoModifier)


def test_instantiate_and_minimum_height(qapp):
    scene = _make_scene(4)
    w = DialogueColumn(scene)
    assert w.minimumHeight() == shared.ROW_HEIGHT * 4


def test_paint_does_not_crash(qapp):
    scene = _make_scene(3)
    w = DialogueColumn(scene)
    w.resize(400, shared.ROW_HEIGHT * 3)
    w.show()
    qapp.processEvents()
    w.repaint()
    qapp.processEvents()
    w.hide()


def test_click_emits_selection_and_cursor(qapp):
    scene = _make_scene(4)
    w = DialogueColumn(scene)
    w.resize(400, shared.ROW_HEIGHT * 4)

    sel: list[int] = []
    cur: list[int] = []
    w.selection_changed.connect(sel.append)
    w.cursor_changed.connect(cur.append)

    y_mid_row2 = shared.ROW_HEIGHT * 2 + shared.ROW_HEIGHT // 2
    w.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, y_mid_row2))
    w.mouseReleaseEvent(_mouse_event(QEvent.Type.MouseButtonRelease, y_mid_row2))

    assert sel == [2]
    assert cur == [2]


def test_drag_emits_dialogue_moved(qapp):
    scene = _make_scene(5)
    w = DialogueColumn(scene)
    w.resize(400, shared.ROW_HEIGHT * 5)

    moves: list[tuple[int, int]] = []
    w.dialogue_moved.connect(lambda a, b: moves.append((a, b)))

    # Press on row 0, move to row 3 mid, release → src=0 dst=3（pop+insert 正規化後）
    press_y = shared.ROW_HEIGHT * 0 + 10
    move_y = shared.ROW_HEIGHT * 3 + shared.ROW_HEIGHT // 2 + 2
    w.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, press_y))
    w.mouseMoveEvent(_mouse_event(QEvent.Type.MouseMove, move_y))
    w.mouseReleaseEvent(_mouse_event(QEvent.Type.MouseButtonRelease, move_y))

    assert len(moves) == 1
    src, dst = moves[0]
    assert src == 0
    # dst 應是「移動後的最終索引」，= 預測插入點 - 1（因 src < 插入點）
    assert dst >= 1 and dst <= 4
