"""Phase 1：state_at(scene, dlg_idx) 行為測試。"""

from src.core.models import (
    Dialogue,
    EffectSegment,
    EffectTrack,
    Scene,
    StageSegment,
)
from src.core.scene_state import state_at


def _scene_with_5_dialogues():
    return Scene(
        id="s1",
        dialogues=[
            Dialogue(type="dialogue", text="d0", character="小明", text_effects=["bold"]),
            Dialogue(type="narration", text="d1"),
            Dialogue(type="dialogue", text="d2", character="小華"),
            Dialogue(type="dialogue", text="d3", character="小明"),
            Dialogue(type="narration", text="d4"),
        ],
    )


# --- 基本欄位 ---

def test_state_at_returns_speaker_and_type():
    s = _scene_with_5_dialogues()
    st = state_at(s, 0)
    assert st["speaker"] == "小明"
    assert st["type"] == "dialogue"
    assert st["text"] == "d0"


def test_state_at_returns_text_effects_copy():
    s = _scene_with_5_dialogues()
    st = state_at(s, 0)
    assert st["text_effects"] == ["bold"]
    # 確認是 copy，回傳 list 修改不會影響原 dialogue
    st["text_effects"].append("italic")
    assert s.dialogues[0].text_effects == ["bold"]


def test_state_at_narration_speaker_is_none():
    s = _scene_with_5_dialogues()
    st = state_at(s, 1)
    assert st["speaker"] is None
    assert st["type"] == "narration"


# --- stage 三槽 active ---

def test_state_at_stage_active_segment():
    s = _scene_with_5_dialogues()
    s.stage_left.append(StageSegment(0, 2, "小明", "便服", "微笑"))
    st = state_at(s, 1)
    assert st["stage"]["left"].character == "小明"
    assert st["stage"]["center"] is None
    assert st["stage"]["right"] is None


def test_state_at_stage_outside_range():
    s = _scene_with_5_dialogues()
    s.stage_left.append(StageSegment(0, 1, "小明"))
    st = state_at(s, 3)
    assert st["stage"]["left"] is None


def test_state_at_three_lanes_simultaneously():
    s = _scene_with_5_dialogues()
    s.stage_left.append(StageSegment(2, 3, "小明"))
    s.stage_center.append(StageSegment(2, 3, "小華"))
    s.stage_right.append(StageSegment(2, 3, "阿姨"))
    st = state_at(s, 2)
    assert st["stage"]["left"].character == "小明"
    assert st["stage"]["center"].character == "小華"
    assert st["stage"]["right"].character == "阿姨"


# --- effects active list ---

def test_state_at_effects_empty_list_when_no_active():
    s = _scene_with_5_dialogues()
    st = state_at(s, 0)
    assert st["effects"] == []


def test_state_at_single_effect_active():
    s = _scene_with_5_dialogues()
    s.effect_tracks.append(EffectTrack("環境", [EffectSegment(1, 3, "rain")]))
    st = state_at(s, 2)
    assert len(st["effects"]) == 1
    assert st["effects"][0].effect_type == "rain"


def test_state_at_multiple_effects_across_tracks():
    """多軌道、各自的 segment 同時 active 時，effects 全部回傳。"""
    s = _scene_with_5_dialogues()
    s.effect_tracks.append(EffectTrack("環境", [EffectSegment(0, 4, "rain")]))
    s.effect_tracks.append(EffectTrack("畫面", [EffectSegment(2, 2, "screen_shake")]))
    s.effect_tracks.append(EffectTrack("自訂", [EffectSegment(2, 2, "crt")]))
    st = state_at(s, 2)
    types = sorted(e.effect_type for e in st["effects"])
    assert types == ["crt", "rain", "screen_shake"]


# --- 邊界 ---

def test_state_at_out_of_range_returns_empty_dict():
    s = _scene_with_5_dialogues()
    assert state_at(s, -1) == {}
    assert state_at(s, 99) == {}


def test_state_at_empty_scene_returns_empty_dict():
    s = Scene(id="empty")
    assert state_at(s, 0) == {}
