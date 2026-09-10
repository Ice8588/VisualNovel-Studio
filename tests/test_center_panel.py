"""CenterPanel 三域結構測試（Phase 2）。"""

import pytest


# qapp fixture 來自 tests/conftest.py（session scope）


def _make_project():
    from src.core.models import (
        Character,
        Costume,
        Dialogue,
        Project,
        Scene,
        SpriteVariant,
        StageSegment,
    )

    proj = Project(
        title="T",
        characters=[
            Character(
                name="小明",
                costumes=[
                    Costume(name="便服", expressions=[SpriteVariant("微笑", "a.png")]),
                ],
            )
        ],
    )
    scene = Scene(id="場景1",
                  dialogues=[Dialogue(type="dialogue", text=f"d{i}", character="小明")
                             for i in range(4)])
    scene.stage_left.append(StageSegment(0, 1, "小明"))
    proj.scenes.append(scene)
    return proj


def test_instantiate_has_three_domain_widgets(qapp):
    from src.ui.center_panel import CenterPanel
    cp = CenterPanel()
    cp.set_project(_make_project())
    assert hasattr(cp, "dialogue_list")
    assert hasattr(cp, "stage_panel")
    assert hasattr(cp, "effect_timeline")
    assert hasattr(cp, "segment_editor")
    assert hasattr(cp, "preview")
    # 舊 QTableWidget 結構已刪除
    assert not hasattr(cp, "dialogue_table")


def test_set_project_binds_scene_to_widgets(qapp):
    from src.ui.center_panel import CenterPanel
    cp = CenterPanel()
    proj = _make_project()
    cp.set_project(proj)
    assert cp.dialogue_list.scene is proj.scenes[0]
    assert cp.stage_panel.scene is proj.scenes[0]
    assert cp.effect_timeline.scene is proj.scenes[0]


def test_add_dialogues_appends(qapp):
    from src.core.models import Dialogue
    from src.ui.center_panel import CenterPanel
    cp = CenterPanel()
    proj = _make_project()
    cp.set_project(proj)
    n0 = len(proj.scenes[0].dialogues)

    emitted: list[bool] = []
    cp.project_changed.connect(lambda: emitted.append(True))

    extras = [Dialogue(type="narration", text="X"),
              Dialogue(type="dialogue", text="Y", character="小明")]
    cp.add_dialogues_to_current_scene(extras)
    assert len(proj.scenes[0].dialogues) == n0 + 2
    assert emitted, "project_changed 應發射"


def test_move_dialogue_keeps_segments_in_sync(qapp):
    """卡片被拖曳 → Scene.move_dialogue → segments 端點同步"""
    from src.core.models import StageSegment
    from src.ui.center_panel import CenterPanel
    cp = CenterPanel()
    proj = _make_project()
    cp.set_project(proj)
    scene = proj.scenes[0]
    # clear existing 以便精確斷言
    scene.stage_left.clear()
    scene.stage_left.append(StageSegment(0, 2, "小明"))

    cp._on_dialogue_moved(0, 3)
    # 按 test_scene_sync 已驗證的語意：seg (0,2) 涵蓋 d0/d1/d2，
    # 移動 d0 到最後 → remove(0) 後 seg 變 (0,1)，insert(3) 不影響 0..1
    assert (scene.stage_left[0].start, scene.stage_left[0].end) == (0, 1)


def test_cleanup_does_not_raise(qapp):
    from src.ui.center_panel import CenterPanel
    cp = CenterPanel()
    cp.set_project(_make_project())
    cp.cleanup()  # 不應丟例外
