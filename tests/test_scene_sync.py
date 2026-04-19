"""Phase 1：Scene.insert_dialogue / remove_dialogue / move_dialogue 的 segment 同步。

POC 已驗證行為（experimental/timeline_poc/models.py）；這裡是正式版測試。
"""

from src.core.models import (
    Dialogue,
    EffectSegment,
    EffectTrack,
    Scene,
    StageSegment,
)


def _make_scene(n_dialogues: int = 5) -> Scene:
    return Scene(
        id="s1",
        dialogues=[Dialogue(type="dialogue", text=f"d{i}") for i in range(n_dialogues)],
    )


# --- insert_dialogue ---

def test_insert_at_middle_shifts_subsequent_segments():
    s = _make_scene(5)
    s.stage_left.append(StageSegment(2, 4, "A"))
    s.insert_dialogue(2, Dialogue(type="dialogue", text="new"))
    assert len(s.dialogues) == 6
    # segment 端點 >= 2 都 +1
    assert (s.stage_left[0].start, s.stage_left[0].end) == (3, 5)


def test_insert_inside_segment_extends_end():
    """在 segment 內部插入新對話，segment 端點向後延（包進新對話）。"""
    s = _make_scene(5)
    s.stage_left.append(StageSegment(1, 3, "A"))
    s.insert_dialogue(2, Dialogue(type="dialogue", text="new"))
    # start=1 < 2 不動；end=3 >= 2 → +1
    assert (s.stage_left[0].start, s.stage_left[0].end) == (1, 4)


def test_insert_at_start_shifts_all():
    s = _make_scene(3)
    s.stage_left.append(StageSegment(0, 2, "A"))
    s.insert_dialogue(0, Dialogue(type="dialogue", text="new"))
    assert (s.stage_left[0].start, s.stage_left[0].end) == (1, 3)


def test_insert_at_end_does_not_touch_existing():
    s = _make_scene(3)
    s.stage_left.append(StageSegment(0, 2, "A"))
    s.insert_dialogue(3, Dialogue(type="dialogue", text="new"))
    assert (s.stage_left[0].start, s.stage_left[0].end) == (0, 2)


# --- remove_dialogue ---

def test_remove_single_row_segment_deletes_segment():
    s = _make_scene(5)
    s.stage_left.append(StageSegment(2, 2, "A"))
    s.remove_dialogue(2)
    assert s.stage_left == []


def test_remove_at_segment_end_shrinks_segment():
    s = _make_scene(5)
    s.stage_left.append(StageSegment(1, 4, "A"))
    s.remove_dialogue(4)
    # end >= 4 → -1；start=1 < 4 不動
    assert (s.stage_left[0].start, s.stage_left[0].end) == (1, 3)


def test_remove_inside_segment_shrinks_end():
    s = _make_scene(6)
    s.stage_left.append(StageSegment(1, 4, "A"))
    s.remove_dialogue(2)
    # start=1 不動（不是 > 2）；end=4 >= 2 → -1
    assert (s.stage_left[0].start, s.stage_left[0].end) == (1, 3)


def test_remove_before_segment_shifts_both_endpoints():
    s = _make_scene(5)
    s.stage_left.append(StageSegment(2, 4, "A"))
    s.remove_dialogue(0)
    # start=2 > 0 → 1；end=4 >= 0 → 3
    assert (s.stage_left[0].start, s.stage_left[0].end) == (1, 3)


def test_remove_affects_effect_tracks_too():
    s = _make_scene(5)
    s.effect_tracks.append(EffectTrack("環境", [EffectSegment(1, 3, "rain")]))
    s.remove_dialogue(0)
    assert (s.effect_tracks[0].segments[0].start,
            s.effect_tracks[0].segments[0].end) == (0, 2)


# --- move_dialogue ---

def test_move_simple_forward():
    """src=0 → dst=4：被搬的對話脫離原 segment，rest segments 隨周邊對話 shift。"""
    s = _make_scene(5)
    s.stage_left.append(StageSegment(0, 2, "A"))   # 涵蓋 d0/d1/d2
    s.stage_right.append(StageSegment(4, 4, "B"))  # 涵蓋 d4
    s.move_dialogue(0, 4)
    # 預期（按 POC 驗證的 pop+insert 語意）：
    # left: 原 (0,2) 包含 d0/d1/d2；移除 d0 後變 (0,1)（d1/d2 shift up）；插 d0 到位置 4 → 不影響 left
    assert (s.stage_left[0].start, s.stage_left[0].end) == (0, 1)
    # right: 原 (4,4) 包含 d4；移除 d0 → end 4 -= 1 → (3,3)；插 d0 到 4 → start>=4 不動，end>=4 不動 → (3,3)
    assert (s.stage_right[0].start, s.stage_right[0].end) == (3, 3)


def test_move_backward():
    s = _make_scene(5)
    s.stage_left.append(StageSegment(2, 3, "A"))
    s.move_dialogue(4, 0)
    # remove(4)：start=2<4 不動；end=3>=4? 否 → 不動 → (2,3)
    # insert(0)：start>=0 → +1 → 3；end>=0 → +1 → 4
    assert (s.stage_left[0].start, s.stage_left[0].end) == (3, 4)


def test_move_no_op_when_src_eq_dst():
    s = _make_scene(3)
    s.stage_left.append(StageSegment(0, 2, "A"))
    s.move_dialogue(1, 1)
    assert (s.stage_left[0].start, s.stage_left[0].end) == (0, 2)


def test_move_invalid_src_no_op():
    s = _make_scene(3)
    s.stage_left.append(StageSegment(0, 2, "A"))
    s.move_dialogue(99, 0)  # invalid src
    assert (s.stage_left[0].start, s.stage_left[0].end) == (0, 2)
    assert len(s.dialogues) == 3
