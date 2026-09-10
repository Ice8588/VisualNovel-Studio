"""Phase 1：StageSegment / EffectSegment / EffectTrack 與 Scene 含 segments 的序列化往返。"""

from src.core.models import (
    Dialogue,
    EffectSegment,
    EffectTrack,
    Scene,
    StageSegment,
)


# --- StageSegment ---

def test_stage_segment_to_dict_minimal():
    seg = StageSegment(start=0, end=2, character="小明")
    d = seg.to_dict()
    assert d == {"start": 0, "end": 2, "character": "小明", "costume": None, "sprite": None}


def test_stage_segment_to_dict_full():
    seg = StageSegment(start=3, end=5, character="小華", costume="制服", sprite="微笑")
    assert seg.to_dict() == {
        "start": 3, "end": 5, "character": "小華", "costume": "制服", "sprite": "微笑",
    }


def test_stage_segment_roundtrip():
    seg = StageSegment(start=1, end=10, character="A", costume="X", sprite="Y")
    assert StageSegment.from_dict(seg.to_dict()) == seg


def test_stage_segment_from_dict_str_int_coercion():
    """JSON 解碼後若 start/end 來源為 str 仍能 cast。"""
    seg = StageSegment.from_dict({"start": "2", "end": "4", "character": "A"})
    assert seg.start == 2 and seg.end == 4


# --- EffectSegment ---

def test_effect_segment_to_dict_omits_empty_params():
    seg = EffectSegment(start=0, end=3, effect_type="rain")
    assert seg.to_dict() == {"start": 0, "end": 3, "effect_type": "rain"}


def test_effect_segment_to_dict_includes_params():
    seg = EffectSegment(start=1, end=2, effect_type="rain", params={"intensity": 0.5})
    d = seg.to_dict()
    assert d["params"] == {"intensity": 0.5}


def test_effect_segment_roundtrip():
    seg = EffectSegment(start=0, end=4, effect_type="snow", params={"density": 100})
    assert EffectSegment.from_dict(seg.to_dict()) == seg


# --- EffectTrack ---

def test_effect_track_roundtrip_with_segments():
    track = EffectTrack(name="環境", segments=[
        EffectSegment(0, 5, "rain"),
        EffectSegment(8, 12, "snow", {"intensity": 0.3}),
    ])
    restored = EffectTrack.from_dict(track.to_dict())
    assert restored == track


def test_effect_track_empty_segments():
    track = EffectTrack(name="畫面")
    restored = EffectTrack.from_dict(track.to_dict())
    assert restored.name == "畫面"
    assert restored.segments == []


# --- Scene 含 segments 的整合 roundtrip ---

def test_scene_with_segments_roundtrip():
    scene = Scene(
        id="s1",
        background="bg.png",
        dialogues=[
            Dialogue(type="dialogue", text="hi", character="小明"),
            Dialogue(type="narration", text="..."),
        ],
        stage_left=[StageSegment(0, 1, "小明", "便服", "微笑")],
        stage_center=[],
        stage_right=[StageSegment(0, 0, "小華")],
        effect_tracks=[
            EffectTrack("環境", [EffectSegment(0, 1, "rain")]),
        ],
    )
    restored = Scene.from_dict(scene.to_dict())
    assert restored == scene


def test_scene_to_dict_no_legacy_keys():
    """Phase 1：Scene 不再輸出 effect 欄位（被 effect_tracks 取代）。"""
    scene = Scene(id="s1")
    d = scene.to_dict()
    assert "effect" not in d
    # 三個 stage lane 與 effect_tracks 必須在
    assert "stage_left" in d
    assert "stage_center" in d
    assert "stage_right" in d
    assert "effect_tracks" in d
