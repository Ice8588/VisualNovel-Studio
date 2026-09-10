"""SegmentEditor inline 編輯器測試。"""

from src.core.models import (
    Character,
    Costume,
    EffectSegment,
    Project,
    SpriteVariant,
    StageSegment,
)
from src.ui.segment_editor import SegmentEditor


# qapp fixture 來自 tests/conftest.py（session scope）


def _make_project() -> Project:
    xm = Character(
        name="小明",
        costumes=[
            Costume(name="便服", expressions=[SpriteVariant("微笑", "a.png"),
                                              SpriteVariant("生氣", "b.png")]),
            Costume(name="制服", expressions=[SpriteVariant("普通", "c.png")]),
        ],
    )
    xh = Character(name="小華", costumes=[])
    return Project(characters=[xm, xh])


def test_default_mode_is_none(qapp):
    editor = SegmentEditor(_make_project())
    assert editor.current_mode() == SegmentEditor.MODE_NONE


def test_set_stage_segment_shows_character(qapp):
    editor = SegmentEditor(_make_project())
    seg = StageSegment(0, 1, "小明", costume="便服", sprite="微笑")
    editor.set_segment(seg)
    assert editor.current_mode() == SegmentEditor.MODE_STAGE
    assert editor._cb_character.currentText() == "小明"
    assert editor._cb_costume.currentText() == "便服"
    assert editor._cb_sprite.currentText() == "微笑"


def test_set_effect_segment_shows_type(qapp):
    editor = SegmentEditor(_make_project())
    seg = EffectSegment(0, 2, "rain", params={"intensity": 0.5})
    editor.set_segment(seg)
    assert editor.current_mode() == SegmentEditor.MODE_EFFECT
    assert editor._cb_effect_type.currentText() == "rain"
    assert "intensity" in editor._params_edit.toPlainText()


def test_set_none_switches_to_placeholder(qapp):
    editor = SegmentEditor(_make_project())
    editor.set_segment(StageSegment(0, 1, "小明"))
    editor.set_segment(None)
    assert editor.current_mode() == SegmentEditor.MODE_NONE


def test_changing_stage_character_emits_signal_and_resets_costume(qapp):
    project = _make_project()
    editor = SegmentEditor(project)
    seg = StageSegment(0, 1, "小明", costume="便服", sprite="微笑")
    editor.set_segment(seg)

    changes: list = []
    editor.segment_changed.connect(lambda: changes.append(True))

    # 改換成沒有服裝的「小華」：costume / sprite 應 cascade reset
    editor._cb_character.setCurrentText("小華")
    assert changes, "character 變更應發射 segment_changed"
    assert seg.character == "小華"
    assert seg.costume is None
    assert seg.sprite is None


def test_changing_effect_type_emits_signal(qapp):
    editor = SegmentEditor(_make_project())
    seg = EffectSegment(0, 1, "rain")
    editor.set_segment(seg)

    changes: list = []
    editor.segment_changed.connect(lambda: changes.append(True))
    editor._cb_effect_type.setCurrentText("snow")
    assert changes
    assert seg.effect_type == "snow"


def test_commit_params_writes_dict(qapp):
    editor = SegmentEditor(_make_project())
    seg = EffectSegment(0, 1, "rain")
    editor.set_segment(seg)

    changes: list = []
    editor.segment_changed.connect(lambda: changes.append(True))
    editor._params_edit.setPlainText('{"intensity": 0.8}')
    editor._commit_params_json()
    assert changes
    assert seg.params == {"intensity": 0.8}


def test_commit_params_invalid_json_does_not_emit(qapp):
    editor = SegmentEditor(_make_project())
    seg = EffectSegment(0, 1, "rain", params={"x": 1})
    editor.set_segment(seg)

    changes: list = []
    editor.segment_changed.connect(lambda: changes.append(True))
    editor._params_edit.setPlainText("{bad json")
    editor._commit_params_json()
    assert not changes
    assert seg.params == {"x": 1}  # 原值不動
