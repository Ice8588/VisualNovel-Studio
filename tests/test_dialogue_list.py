"""DialogueColumn（src/ui/dialogue_list.py）widget 測試。

需要 QT_QPA_PLATFORM=offscreen 執行。
"""

from PyQt6.QtCore import QEvent, QPointF, QRect, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.core.models import Dialogue, Scene, StageSegment
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


# ── Task 3：_popup_speaker_combo 修復回歸測試 ─────────────────────────────


def _make_scene_with_chars() -> Scene:
    """含角色的場景（用於說話者 combo 測試）。"""
    return Scene(
        id="s2",
        dialogues=[
            Dialogue(type="dialogue", text="你好", character="小明"),
            Dialogue(type="dialogue", text="再見", character="小華"),
            Dialogue(type="narration", text="旁白行", character=None),
        ],
    )


def test_popup_speaker_combo_no_exception(qapp):
    """回歸測試：呼叫 _popup_speaker_combo 不得拋任何例外（修復前會 AttributeError）。"""
    scene = _make_scene_with_chars()
    w = DialogueColumn(scene)
    w.set_character_colors({"小明": "#FF0000", "小華": "#00FF00"})
    w.resize(400, shared.ROW_HEIGHT * 3)

    # 直接呼叫內部方法；不得拋例外
    anchor = QRect(50, shared.ROW_HEIGHT // 4, shared.COL_CHARACTER_W, shared.ROW_HEIGHT // 2)
    w._popup_speaker_combo(0, anchor)
    qapp.processEvents()

    # combo 應已建立並顯示（它是 w 的 child）
    from qfluentwidgets import ComboBox
    combos = [c for c in w.children() if isinstance(c, ComboBox)]
    assert len(combos) >= 1, "combo 應存在於 widget children 中"

    combo = combos[0]
    # 選項應包含「（無）」+ 兩個角色名
    texts = [combo.items[i].text for i in range(len(combo.items))]
    assert "（無）" in texts
    assert "小明" in texts
    assert "小華" in texts


def test_popup_speaker_combo_apply_character(qapp):
    """選擇角色名 → dialogue.character 更新、speaker_changed 訊號發射。"""
    scene = _make_scene_with_chars()
    w = DialogueColumn(scene)
    w.set_character_colors({"小明": "#FF0000", "小華": "#00FF00"})
    w.resize(400, shared.ROW_HEIGHT * 3)

    changed: list[int] = []
    w.speaker_changed.connect(changed.append)

    anchor = QRect(50, shared.ROW_HEIGHT // 4, shared.COL_CHARACTER_W, shared.ROW_HEIGHT // 2)
    w._popup_speaker_combo(0, anchor)
    qapp.processEvents()

    from qfluentwidgets import ComboBox
    combos = [c for c in w.children() if isinstance(c, ComboBox)]
    assert combos, "combo 應存在"
    combo = combos[0]

    # 模擬選擇「小華」（原為「小明」）→ on_text_changed 觸發
    combo.setCurrentText("小華")
    qapp.processEvents()

    assert scene.dialogues[0].character == "小華"
    assert 0 in changed


def test_popup_speaker_combo_select_none(qapp):
    """選擇「（無）」→ dialogue.character 設為 None、speaker_changed 發射。"""
    scene = _make_scene_with_chars()
    w = DialogueColumn(scene)
    w.set_character_colors({"小明": "#FF0000", "小華": "#00FF00"})
    w.resize(400, shared.ROW_HEIGHT * 3)

    changed: list[int] = []
    w.speaker_changed.connect(changed.append)

    anchor = QRect(50, shared.ROW_HEIGHT // 4, shared.COL_CHARACTER_W, shared.ROW_HEIGHT // 2)
    w._popup_speaker_combo(0, anchor)
    qapp.processEvents()

    from qfluentwidgets import ComboBox
    combos = [c for c in w.children() if isinstance(c, ComboBox)]
    assert combos, "combo 應存在"
    combo = combos[0]

    # 選擇「（無）」→ character = None
    combo.setCurrentText("（無）")
    qapp.processEvents()

    assert scene.dialogues[0].character is None
    assert 0 in changed


def test_click_character_col_no_exception(qapp):
    """QTest.mouseClick 點角色欄中心走完整 mousePressEvent 路徑，不得拋例外。"""
    scene = _make_scene_with_chars()
    w = DialogueColumn(scene)
    w.set_character_colors({"小明": "#FF0000", "小華": "#00FF00"})
    w.resize(400, shared.ROW_HEIGHT * 3)
    w.show()
    qapp.processEvents()

    # 取第 0 列角色欄中心點
    char_rect = w._character_col_rect(0)
    center = char_rect.center()

    # 點擊不得拋例外
    QTest.mouseClick(w, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)
    qapp.processEvents()

    w.hide()


# ── Task 6：刪除 / 編輯文字 / 插入 / 複製 ───────────────────────────────


def test_delete_removes_dialogue_and_shifts_segments(qapp):
    """Delete 選取句 → 經 Scene.remove_dialogue，segment 端點同步 shift。"""
    scene = _make_scene(3)
    scene.stage_center.append(StageSegment(start=1, end=2, character="小明"))
    w = DialogueColumn(scene)
    w.resize(400, shared.ROW_HEIGHT * 3)

    fired: list[int] = []
    w.content_changed.connect(lambda: fired.append(1))

    # 選 row0
    y_row0 = shared.ROW_HEIGHT // 2
    w.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, y_row0))
    assert w._selected_idx == 0

    QTest.keyClick(w, Qt.Key.Key_Delete)

    assert len(scene.dialogues) == 2
    # segment (1,2) → (0,1)
    seg = scene.stage_center[0]
    assert (seg.start, seg.end) == (0, 1)
    assert fired  # content_changed 有發射


def test_double_click_edit_text_retypes(qapp):
    """雙擊台詞區 → overlay LineEdit；改成台詞 / 旁白各自重判 type。"""
    from qfluentwidgets import LineEdit

    scene = _make_scene(3)  # row0 dialogue character="小明"
    w = DialogueColumn(scene)
    w.set_character_colors({"小明": "#FF0000"})
    w.resize(400, shared.ROW_HEIGHT * 3)

    # 雙擊 row0 台詞區
    text_rect = w._text_col_rect(0)
    center_y = text_rect.center().y()
    w.mouseDoubleClickEvent(_mouse_event(QEvent.Type.MouseButtonDblClick, center_y))
    qapp.processEvents()

    editors = [c for c in w.children() if isinstance(c, LineEdit)]
    assert editors, "overlay LineEdit 應出現"
    editor = editors[0]

    # 改成台詞 → type=="dialogue"，character 保留
    editor.setText("「新台詞」")
    editor.returnPressed.emit()
    qapp.processEvents()
    assert scene.dialogues[0].text == "「新台詞」"
    assert scene.dialogues[0].type == "dialogue"
    assert scene.dialogues[0].character == "小明"

    # 再改成旁白 → type=="narration" 且 character is None
    w.mouseDoubleClickEvent(_mouse_event(QEvent.Type.MouseButtonDblClick, center_y))
    qapp.processEvents()
    editor2 = [c for c in w.children() if isinstance(c, LineEdit)][0]
    editor2.setText("普通旁白文字")
    editor2.returnPressed.emit()
    qapp.processEvents()
    assert scene.dialogues[0].type == "narration"
    assert scene.dialogues[0].character is None


def test_edit_text_esc_cancels(qapp):
    """Esc 取消 → model 不變。"""
    from qfluentwidgets import LineEdit

    scene = _make_scene(2)
    orig = scene.dialogues[0].text
    w = DialogueColumn(scene)
    w.resize(400, shared.ROW_HEIGHT * 2)

    w._begin_text_edit(0)
    qapp.processEvents()
    editor = [c for c in w.children() if isinstance(c, LineEdit)][0]
    editor.setText("不應套用")
    QTest.keyClick(editor, Qt.Key.Key_Escape)
    qapp.processEvents()

    assert scene.dialogues[0].text == orig


def test_insert_dialogue_after_shifts_segments(qapp):
    """右鍵插入 → 句數+1、位置正確、segment 端點 shift。"""
    scene = _make_scene(3)
    scene.stage_center.append(StageSegment(start=1, end=2, character="小明"))
    w = DialogueColumn(scene)
    w.resize(400, shared.ROW_HEIGHT * 3)

    fired: list[int] = []
    w.content_changed.connect(lambda: fired.append(1))

    # 在 row0 下方插入旁白 → 新句在 index 1
    w._insert_dialogue_after(0, "narration")

    assert len(scene.dialogues) == 4
    assert scene.dialogues[1].type == "narration"
    assert scene.dialogues[1].text == ""
    # segment 在插入點之後 → (1,2) → (2,3)
    seg = scene.stage_center[0]
    assert (seg.start, seg.end) == (2, 3)
    assert fired


def test_append_dialogue_at_end(qapp):
    """右鍵空白處新增台詞 → append 末尾，預設 text=「」。"""
    scene = _make_scene(2)
    w = DialogueColumn(scene)
    w.resize(400, shared.ROW_HEIGHT * 2)

    w._append_dialogue("dialogue")
    assert len(scene.dialogues) == 3
    assert scene.dialogues[2].type == "dialogue"
    assert scene.dialogues[2].text == "「」"


def test_ctrl_c_copies_text(qapp):
    """Ctrl+C → clipboard 為選取句的 text。"""
    scene = _make_scene(3)
    w = DialogueColumn(scene)
    w.resize(400, shared.ROW_HEIGHT * 3)

    y_row1 = shared.ROW_HEIGHT + shared.ROW_HEIGHT // 2
    w.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, y_row1))
    assert w._selected_idx == 1

    QTest.keyClick(w, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    qapp.processEvents()

    assert QApplication.clipboard().text() == scene.dialogues[1].text
