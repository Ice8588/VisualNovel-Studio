"""Phase 3：Project.to_script_json 預計算 stage / active_effects 的行為守護。

engine.js 只讀 pre-resolved 欄位；這份測試確保輸出格式穩定。
"""

from src.core.models import (
    Dialogue,
    EffectSegment,
    EffectTrack,
    Episode,
    Project,
    Scene,
    StageSegment,
)


def _make_project() -> Project:
    scene = Scene(
        id="s1",
        background="bg.png",
        dialogues=[
            Dialogue(type="dialogue", text=f"d{i}", character="A", text_effects=(["bold"] if i == 2 else []))
            for i in range(5)
        ],
    )
    # stage_left A 覆蓋 [0,2]，stage_right B 覆蓋 [3,4]
    scene.stage_left.append(StageSegment(0, 2, "A", costume="便服", sprite="微笑"))
    scene.stage_right.append(StageSegment(3, 4, "B"))
    # effect rain 覆蓋 [1,3]；screen_shake 單點 [2,2]
    scene.effect_tracks.append(
        EffectTrack(name="env", segments=[EffectSegment(1, 3, "rain", params={"intensity": 0.7})])
    )
    scene.effect_tracks.append(
        EffectTrack(name="cam", segments=[EffectSegment(2, 2, "screen_shake")])
    )
    return Project(title="T", episodes=[Episode(name="影片1", scenes=[scene])])


def test_each_dialogue_has_stage_and_active_effects():
    out = _make_project().to_script_json()
    dialogues = out["scenes"][0]["dialogues"]
    assert len(dialogues) == 5
    for d in dialogues:
        assert set(d.keys()) >= {"type", "text", "character", "text_effects", "stage", "active_effects"}
        assert set(d["stage"].keys()) == {"left", "center", "right"}
        assert isinstance(d["active_effects"], list)


def test_stage_segment_resolved_for_covered_range():
    out = _make_project().to_script_json()
    dialogues = out["scenes"][0]["dialogues"]
    # d0/d1/d2 左槽 A；d3/d4 右槽 B
    for idx in range(3):
        assert dialogues[idx]["stage"]["left"] == {
            "character": "A", "costume": "便服", "sprite": "微笑",
        }
        assert dialogues[idx]["stage"]["right"] is None
    for idx in (3, 4):
        assert dialogues[idx]["stage"]["left"] is None
        assert dialogues[idx]["stage"]["right"]["character"] == "B"


def test_active_effects_resolved_from_tracks():
    out = _make_project().to_script_json()
    dialogues = out["scenes"][0]["dialogues"]
    # d0：無特效
    assert dialogues[0]["active_effects"] == []
    # d1：rain only
    assert dialogues[1]["active_effects"] == [
        {"effect_type": "rain", "params": {"intensity": 0.7}}
    ]
    # d2：rain + screen_shake（兩條軌道同時 active）
    kinds = {e["effect_type"] for e in dialogues[2]["active_effects"]}
    assert kinds == {"rain", "screen_shake"}
    # d4：rain 已結束、無 shake
    assert dialogues[4]["active_effects"] == []


def test_text_effects_preserved_untouched():
    out = _make_project().to_script_json()
    dialogues = out["scenes"][0]["dialogues"]
    assert dialogues[2]["text_effects"] == ["bold"]
    assert dialogues[0]["text_effects"] == []


def test_scene_no_longer_contains_effect_field():
    """scene-wide effect 已刪除；to_script_json 輸出不應有這個鍵。"""
    out = _make_project().to_script_json()
    scene_out = out["scenes"][0]
    assert "effect" not in scene_out
    # 基本欄位維持
    assert scene_out["id"] == "s1"
    assert scene_out["background"] == "bg.png"


def test_characters_block_unchanged_shape():
    """characters 輸出結構（name_color/position/sprites dict）維持不變，engine.js 仍需這格式。"""
    proj = _make_project()
    from src.core.models import Character, Costume, SpriteVariant
    proj.characters.append(Character(
        name="A", name_color="#FF0000",
        costumes=[Costume(name="便服", expressions=[SpriteVariant("微笑", "a.png")])],
    ))
    out = proj.to_script_json()
    assert "A" in out["characters"]
    assert out["characters"]["A"]["name_color"] == "#FF0000"
    assert out["characters"]["A"]["sprites"] == {"微笑": "a.png"}
