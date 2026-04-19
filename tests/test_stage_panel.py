"""StagePanel / StageLaneWidget widget 測試。"""

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent

from src.core.models import Dialogue, Scene, StageSegment
from src.ui import _timeline_shared as shared
from src.ui.stage_panel import StageLaneWidget, StagePanel


# qapp fixture 來自 tests/conftest.py（session scope）


def _make_scene(n: int = 6) -> Scene:
    return Scene(
        id="s1",
        dialogues=[Dialogue(type="dialogue", text=f"d{i}") for i in range(n)],
    )


def _mouse_event(kind, y: int, button=Qt.MouseButton.LeftButton) -> QMouseEvent:
    pos = QPointF(float(shared.LANE_WIDTH // 2), float(y))
    return QMouseEvent(kind, pos, pos, button, button, Qt.KeyboardModifier.NoModifier)


def test_stage_panel_instantiate(qapp):
    scene = _make_scene(5)
    panel = StagePanel(scene)
    assert set(panel.lanes.keys()) == {"left", "center", "right"}
    assert panel.minimumWidth() >= shared.LANE_WIDTH * 3


def test_lane_paint_does_not_crash(qapp):
    scene = _make_scene(4)
    scene.stage_left.append(StageSegment(0, 1, "小明", costume="便服", sprite="微笑"))
    lane = StageLaneWidget(scene, "left")
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 4)
    lane.show()
    qapp.processEvents()
    lane.repaint()
    qapp.processEvents()
    lane.hide()


def test_click_on_segment_emits_selected(qapp):
    scene = _make_scene(5)
    seg = StageSegment(1, 3, "小明")
    scene.stage_left.append(seg)
    lane = StageLaneWidget(scene, "left")
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 5)

    selected: list = []
    lane.segment_selected.connect(selected.append)

    y = shared.idx_to_y(2) + shared.ROW_HEIGHT // 2  # 落在 segment 中段
    lane.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, y))
    assert selected and selected[-1] is seg


def test_double_click_empty_adds_segment(qapp):
    scene = _make_scene(6)
    lane = StageLaneWidget(scene, "center")
    lane.set_character_colors({"小明": "#4682B4"})  # Bug B fix：需先有角色才能新增
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 6)

    changed: list = []
    committed: list = []
    lane.segment_changed.connect(lambda: changed.append(True))
    lane.segment_committed.connect(lambda: committed.append(True))

    y = shared.idx_to_y(2) + 5
    lane.mouseDoubleClickEvent(_mouse_event(QEvent.Type.MouseButtonDblClick, y))

    assert changed == [True]
    assert committed == [True]  # 新增 segment 是 commit 動作
    assert len(scene.stage_center) == 1
    assert scene.stage_center[0].start == 2
    assert scene.stage_center[0].character == "小明"


def test_double_click_no_characters_does_not_add(qapp):
    """Bug B：沒有任何角色時雙擊不應建立 ghost segment（character 必填）。"""
    scene = _make_scene(6)
    lane = StageLaneWidget(scene, "center")
    # 不呼叫 set_character_colors → _character_colors 為空
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 6)

    changed: list = []
    committed: list = []
    lane.segment_changed.connect(lambda: changed.append(True))
    lane.segment_committed.connect(lambda: committed.append(True))

    y = shared.idx_to_y(2) + 5
    lane.mouseDoubleClickEvent(_mouse_event(QEvent.Type.MouseButtonDblClick, y))

    assert changed == []
    assert committed == []
    assert scene.stage_center == []


def test_drag_emits_committed_only_on_release(qapp):
    """Bug A：mouseMove 期間 segment_changed 多次；segment_committed 只在 release 觸發一次。"""
    scene = _make_scene(8)
    seg = StageSegment(2, 3, "小明")
    scene.stage_left.append(seg)
    lane = StageLaneWidget(scene, "left")
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 8)

    changed: list = []
    committed: list = []
    lane.segment_changed.connect(lambda: changed.append(True))
    lane.segment_committed.connect(lambda: committed.append(True))

    # 從 segment 中段按下（觸發 mode="move"），移動數次到下方
    press_y = shared.idx_to_y(2) + shared.ROW_HEIGHT // 2
    lane.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, press_y))
    assert committed == [], "click 但未拖動，不應 commit"

    for offset in (1, 2, 3):
        y = press_y + offset * shared.ROW_HEIGHT
        lane.mouseMoveEvent(_mouse_event(QEvent.Type.MouseMove, y))
    assert len(changed) >= 1, f"mouseMove 應觸發 segment_changed，實際 {len(changed)}"
    assert committed == [], "拖拉中不應 commit"

    lane.mouseReleaseEvent(_mouse_event(QEvent.Type.MouseButtonRelease, press_y + 3 * shared.ROW_HEIGHT))
    assert committed == [True], "release 後應 commit 一次"


def test_click_without_drag_does_not_commit(qapp):
    """Bug A 邊界：純點擊（無拖動）→ segment_committed 不該觸發。"""
    scene = _make_scene(5)
    seg = StageSegment(1, 2, "小明")
    scene.stage_left.append(seg)
    lane = StageLaneWidget(scene, "left")
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 5)

    committed: list = []
    lane.segment_committed.connect(lambda: committed.append(True))

    y = shared.idx_to_y(1) + shared.ROW_HEIGHT // 2
    lane.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, y))
    lane.mouseReleaseEvent(_mouse_event(QEvent.Type.MouseButtonRelease, y))
    assert committed == []


def test_delete_key_removes_selected_segment(qapp):
    scene = _make_scene(5)
    seg = StageSegment(1, 2, "小明")
    scene.stage_left.append(seg)
    lane = StageLaneWidget(scene, "left")

    committed: list = []
    lane.segment_committed.connect(lambda: committed.append(True))

    # 手動選中
    lane._selected = seg

    # 發送 Delete 鍵（用 QKeyEvent 觸發 keyPressEvent）
    from PyQt6.QtGui import QKeyEvent
    ev = QKeyEvent(QEvent.Type.KeyPress, int(Qt.Key.Key_Delete), Qt.KeyboardModifier.NoModifier)
    lane.keyPressEvent(ev)

    assert scene.stage_left == []
    assert committed == [True]  # Delete 也是 commit 動作


# ── Phase 4：跨 lane 拖拉 ──

def test_cross_lane_transfer_to_empty_target(qapp):
    """把 left lane 的 segment 拖到 right lane（空）→ 轉移成功，原 lane 不再有此 seg。"""
    scene = _make_scene(6)
    seg = StageSegment(1, 3, "小明")
    scene.stage_left.append(seg)
    panel = StagePanel(scene)
    panel.show()
    qapp.processEvents()

    committed: list = []
    panel.segment_committed.connect(lambda: committed.append(True))

    left_lane = panel.lanes["left"]
    right_lane = panel.lanes["right"]

    # 模擬 release 在 right lane 的中央
    right_local_center = QPointF(float(right_lane.width() / 2), float(shared.idx_to_y(2)))
    release_global = right_lane.mapToGlobal(right_local_center.toPoint())
    panel._on_request_lane_transfer = panel._on_request_lane_transfer  # noqa: silence flake
    # 直接呼叫：模擬從 left lane sender 觸發
    # 由於 _on_request_lane_transfer 用 self.sender()，這裡需用 emit 才正確接通
    left_lane.request_lane_transfer.emit(seg, release_global)

    panel.hide()

    assert seg not in scene.stage_left
    assert seg in scene.stage_right
    assert committed and committed[-1] is True


def test_cross_lane_transfer_rejects_when_overlap(qapp):
    """目標 lane 已有同範圍 segment → 拒絕轉移。"""
    scene = _make_scene(6)
    seg = StageSegment(1, 3, "小明")
    blocker = StageSegment(2, 2, "小華")  # 與 seg [1,3] 重疊
    scene.stage_left.append(seg)
    scene.stage_right.append(blocker)
    panel = StagePanel(scene)
    panel.show()
    qapp.processEvents()

    right_lane = panel.lanes["right"]
    release_global = right_lane.mapToGlobal(
        QPointF(float(right_lane.width() / 2), float(shared.idx_to_y(2))).toPoint()
    )
    panel.lanes["left"].request_lane_transfer.emit(seg, release_global)

    panel.hide()

    assert seg in scene.stage_left  # 留原位
    assert seg not in scene.stage_right
    assert blocker in scene.stage_right  # 阻擋者也還在


def test_cross_lane_transfer_release_outside_no_lane(qapp):
    """release 點不在任何 lane 上 → seg 留在原 lane（emit committed 即可）。"""
    scene = _make_scene(6)
    seg = StageSegment(1, 3, "小明")
    scene.stage_left.append(seg)
    panel = StagePanel(scene)
    panel.show()
    qapp.processEvents()

    # 用一個極遠的全域座標
    far_pos = panel.mapToGlobal(panel.rect().bottomRight())
    far_pos.setX(far_pos.x() + 9999)
    panel.lanes["left"].request_lane_transfer.emit(seg, far_pos)

    panel.hide()

    assert seg in scene.stage_left
