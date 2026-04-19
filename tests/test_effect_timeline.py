"""EffectTimelineWidget / EffectLaneWidget widget 測試。"""

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from src.core.models import Dialogue, EffectSegment, EffectTrack, Scene
from src.ui import _timeline_shared as shared
from src.ui.effect_timeline import EffectLaneWidget, EffectTimelineWidget


# qapp fixture 來自 tests/conftest.py（session scope）


def _make_scene_with_track(n_dialogues: int = 6, n_segments: int = 0) -> Scene:
    scene = Scene(
        id="s1",
        dialogues=[Dialogue(type="dialogue", text=f"d{i}") for i in range(n_dialogues)],
    )
    segs = [EffectSegment(i, i, "rain") for i in range(n_segments)]
    scene.effect_tracks.append(EffectTrack(name="環境", segments=segs))
    return scene


def _mouse_event(kind, y: int) -> QMouseEvent:
    pos = QPointF(float(shared.LANE_WIDTH // 2), float(y))
    return QMouseEvent(kind, pos, pos, Qt.MouseButton.LeftButton,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)


def test_timeline_instantiate_with_existing_tracks(qapp):
    scene = _make_scene_with_track(n_dialogues=4)
    widget = EffectTimelineWidget(scene)
    assert "環境" in widget.lanes


def test_add_track_builds_new_lane(qapp):
    scene = _make_scene_with_track(n_dialogues=4)
    widget = EffectTimelineWidget(scene)
    widget.add_track("鏡頭")
    assert "鏡頭" in widget.lanes
    assert scene.effect_tracks[-1].name == "鏡頭"


def test_lane_paint_does_not_crash(qapp):
    scene = _make_scene_with_track(n_dialogues=4)
    scene.effect_tracks[0].segments.append(EffectSegment(0, 2, "rain"))
    lane = EffectLaneWidget(scene, scene.effect_tracks[0])
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 4)
    lane.show()
    qapp.processEvents()
    lane.repaint()
    qapp.processEvents()
    lane.hide()


def test_double_click_adds_segment(qapp):
    scene = _make_scene_with_track(n_dialogues=6)
    lane = EffectLaneWidget(scene, scene.effect_tracks[0])
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 6)

    changed: list = []
    committed: list = []
    lane.segment_changed.connect(lambda: changed.append(True))
    lane.segment_committed.connect(lambda: committed.append(True))

    y = shared.idx_to_y(2) + 5
    lane.mouseDoubleClickEvent(_mouse_event(QEvent.Type.MouseButtonDblClick, y))

    assert changed == [True]
    assert committed == [True]
    assert len(scene.effect_tracks[0].segments) == 1
    assert scene.effect_tracks[0].segments[0].effect_type == "rain"


def test_drag_emits_committed_only_on_release(qapp):
    """Bug A：拖端點過程 segment_changed 多次；segment_committed 僅在 release 觸發一次。"""
    scene = _make_scene_with_track(n_dialogues=8)
    seg = EffectSegment(2, 3, "rain")
    scene.effect_tracks[0].segments.append(seg)
    lane = EffectLaneWidget(scene, scene.effect_tracks[0])
    lane.resize(shared.LANE_WIDTH, shared.ROW_HEIGHT * 8)

    changed: list = []
    committed: list = []
    lane.segment_changed.connect(lambda: changed.append(True))
    lane.segment_committed.connect(lambda: committed.append(True))

    press_y = shared.idx_to_y(2) + shared.ROW_HEIGHT // 2  # segment 中段
    lane.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, press_y))
    for offset in (1, 2):
        y = press_y + offset * shared.ROW_HEIGHT
        lane.mouseMoveEvent(_mouse_event(QEvent.Type.MouseMove, y))
    assert len(changed) >= 1
    assert committed == [], "拖拉中不應 commit"

    lane.mouseReleaseEvent(_mouse_event(QEvent.Type.MouseButtonRelease, press_y + 2 * shared.ROW_HEIGHT))
    assert committed == [True]


def test_add_track_emits_committed(qapp):
    """add_track（新增軌道）視為 commit 動作，caller 用此觸發 reload preview。"""
    scene = _make_scene_with_track(n_dialogues=4)
    widget = EffectTimelineWidget(scene)

    committed: list = []
    widget.segment_committed.connect(lambda: committed.append(True))

    widget.add_track("鏡頭")
    assert committed == [True]


def test_delete_key_removes_selected(qapp):
    scene = _make_scene_with_track(n_dialogues=5)
    seg = EffectSegment(1, 2, "rain")
    scene.effect_tracks[0].segments.append(seg)
    lane = EffectLaneWidget(scene, scene.effect_tracks[0])
    lane._selected = seg

    committed: list = []
    lane.segment_committed.connect(lambda: committed.append(True))

    ev = QKeyEvent(QEvent.Type.KeyPress, int(Qt.Key.Key_Delete), Qt.KeyboardModifier.NoModifier)
    lane.keyPressEvent(ev)

    assert scene.effect_tracks[0].segments == []
    assert committed == [True]


# ── Phase 4 lane mgmt ──

def test_rename_track_succeeds_when_unique(qapp):
    scene = _make_scene_with_track(n_dialogues=4)
    widget = EffectTimelineWidget(scene)
    committed: list = []
    widget.segment_committed.connect(lambda: committed.append(True))

    ok = widget.rename_track("環境", "天氣")
    assert ok
    assert "環境" not in widget.lanes
    assert "天氣" in widget.lanes
    assert scene.effect_tracks[0].name == "天氣"
    assert committed == [True]


def test_rename_track_rejects_duplicate(qapp):
    scene = _make_scene_with_track(n_dialogues=4)
    scene.effect_tracks.append(EffectTrack(name="畫面", segments=[]))
    widget = EffectTimelineWidget(scene)
    assert widget.rename_track("環境", "畫面") is False
    assert scene.effect_tracks[0].name == "環境"  # 未動


def test_rename_track_rejects_empty_or_same(qapp):
    scene = _make_scene_with_track(n_dialogues=4)
    widget = EffectTimelineWidget(scene)
    assert widget.rename_track("環境", "") is False
    assert widget.rename_track("環境", "環境") is False
    assert widget.rename_track("不存在", "新名") is False


def test_remove_track_pops_lane_and_segments(qapp):
    scene = _make_scene_with_track(n_dialogues=4)
    scene.effect_tracks[0].segments.append(EffectSegment(0, 2, "rain"))
    widget = EffectTimelineWidget(scene)
    committed: list = []
    widget.segment_committed.connect(lambda: committed.append(True))

    ok = widget.remove_track("環境")
    assert ok
    assert scene.effect_tracks == []
    assert "環境" not in widget.lanes
    assert committed == [True]


def test_remove_track_unknown_returns_false(qapp):
    scene = _make_scene_with_track(n_dialogues=4)
    widget = EffectTimelineWidget(scene)
    assert widget.remove_track("不存在") is False
