"""Tests for Dialogue.stage field — Block 1."""

import pytest

from src.core.models import Dialogue, Scene, Project, Character, GameSettings


def _make_project_with_stage(stage_data):
    """建立含一個 Scene、一條 Dialogue 的最小 Project，設定指定 stage。"""
    d = Dialogue(type="dialogue", text="test", character="A", stage=stage_data)
    scene = Scene(id="scene_001", dialogues=[d])
    project = Project(
        title="test",
        characters=[],
        scenes=[scene],
        assets={},
        game_settings=GameSettings(),
    )
    return project


# --- from_dict 向下相容 ---

def test_from_dict_no_stage_defaults_to_all_none():
    """舊 JSON（無 stage 鍵）→ 三槽皆 None。"""
    data = {"type": "dialogue", "text": "hello"}
    d = Dialogue.from_dict(data)
    assert d.stage == {"left": None, "center": None, "right": None}


def test_from_dict_full_stage_roundtrip():
    """完整 stage → round-trip 正確。"""
    slot = {"character": "小明", "sprite": "普通", "costume": None}
    data = {
        "type": "dialogue",
        "text": "hello",
        "stage": {"left": slot, "center": None, "right": None},
    }
    d = Dialogue.from_dict(data)
    assert d.stage["left"] == slot
    assert d.stage["center"] is None
    assert d.stage["right"] is None


def test_from_dict_partial_stage_fills_missing_keys():
    """部分 stage（只有 left）→ 其他槽位補 None。"""
    slot = {"character": "小明", "sprite": "普通", "costume": None}
    data = {
        "type": "dialogue",
        "text": "hello",
        "stage": {"left": slot},
    }
    d = Dialogue.from_dict(data)
    assert d.stage["left"] == slot
    assert d.stage["center"] is None
    assert d.stage["right"] is None


def test_from_dict_null_stage_treated_as_empty():
    """stage 為 null → 三槽皆 None（與無 stage 等效）。"""
    data = {"type": "dialogue", "text": "hello", "stage": None}
    d = Dialogue.from_dict(data)
    assert d.stage == {"left": None, "center": None, "right": None}


# --- to_dict 序列化 ---

def test_to_dict_all_none_omits_stage_key():
    """三槽皆 None → to_dict() 不輸出 stage 鍵（舊檔 diff 乾淨）。"""
    d = Dialogue(type="dialogue", text="hello")
    result = d.to_dict()
    assert "stage" not in result


def test_to_dict_with_stage_includes_stage_key():
    """有任一槽位非 None → to_dict() 輸出 stage 鍵。"""
    slot = {"character": "小明", "sprite": "普通", "costume": None}
    d = Dialogue(
        type="dialogue",
        text="hello",
        stage={"left": slot, "center": None, "right": None},
    )
    result = d.to_dict()
    assert "stage" in result
    assert result["stage"]["left"] == slot
    assert result["stage"]["center"] is None
    assert result["stage"]["right"] is None


def test_to_dict_from_dict_roundtrip():
    """to_dict() → from_dict() 資料完整保留。"""
    slot = {"character": "小明", "sprite": "普通", "costume": "制服"}
    original = Dialogue(
        type="dialogue",
        text="hello",
        stage={"left": None, "center": slot, "right": None},
    )
    restored = Dialogue.from_dict(original.to_dict())
    assert restored.stage == original.stage


# --- to_script_json 傳遞 stage ---

def test_to_script_json_dialogue_includes_stage():
    """Project.to_script_json() 的 dialogue 區段含有 stage 結構（有值時）。"""
    slot = {"character": "小明", "sprite": "普通", "costume": None}
    stage = {"left": slot, "center": None, "right": None}
    project = _make_project_with_stage(stage)
    script = project.to_script_json()
    dlg = script["scenes"][0]["dialogues"][0]
    assert "stage" in dlg
    assert dlg["stage"]["left"] == slot


def test_to_script_json_dialogue_omits_stage_when_empty():
    """全空 stage → script.json dialogue 不含 stage 鍵。"""
    project = _make_project_with_stage({"left": None, "center": None, "right": None})
    script = project.to_script_json()
    dlg = script["scenes"][0]["dialogues"][0]
    assert "stage" not in dlg


# --- Bug 3：set_stage_slot 同列內去重 ---

def test_stage_dedup_same_character_across_slots():
    """left=A 時設 center=A → 自動清 left；center 保留。"""
    d = Dialogue(
        type="dialogue",
        text="x",
        stage={"left": {"character": "小明", "sprite": None, "costume": None},
               "center": None, "right": None},
    )
    d.set_stage_slot("center", {"character": "小明", "sprite": "微笑", "costume": None})
    assert d.stage["left"] is None
    assert d.stage["center"] == {"character": "小明", "sprite": "微笑", "costume": None}
    assert d.stage["right"] is None


def test_stage_dedup_different_character_untouched():
    """left=A 時設 center=B → left 不動。"""
    d = Dialogue(
        type="dialogue",
        text="x",
        stage={"left": {"character": "小明", "sprite": None, "costume": None},
               "center": None, "right": None},
    )
    d.set_stage_slot("center", {"character": "小華", "sprite": None, "costume": None})
    assert d.stage["left"] == {"character": "小明", "sprite": None, "costume": None}
    assert d.stage["center"] == {"character": "小華", "sprite": None, "costume": None}


def test_stage_dedup_clear_does_not_trigger():
    """clear（value=None）不應觸發去重邏輯。"""
    d = Dialogue(
        type="dialogue",
        text="x",
        stage={"left": {"character": "小明", "sprite": None, "costume": None},
               "center": {"character": "小華", "sprite": None, "costume": None},
               "right": None},
    )
    d.set_stage_slot("right", None)
    assert d.stage["left"] == {"character": "小明", "sprite": None, "costume": None}
    assert d.stage["center"] == {"character": "小華", "sprite": None, "costume": None}
    assert d.stage["right"] is None


def test_stage_dedup_same_slot_update():
    """同槽更新（在 left 重設 left=同角色）→ 不應自我清空。"""
    d = Dialogue(
        type="dialogue",
        text="x",
        stage={"left": {"character": "小明", "sprite": "微笑", "costume": None},
               "center": None, "right": None},
    )
    d.set_stage_slot("left", {"character": "小明", "sprite": "生氣", "costume": None})
    assert d.stage["left"] == {"character": "小明", "sprite": "生氣", "costume": None}


def test_stage_set_slot_invalid_position():
    """無效 position 字串 → ValueError。"""
    d = Dialogue(type="dialogue", text="x")
    with pytest.raises(ValueError):
        d.set_stage_slot("top", {"character": "小明"})
