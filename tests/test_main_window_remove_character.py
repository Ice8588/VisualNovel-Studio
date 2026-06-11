"""MainWindow._on_remove_character 的 Phase 2 新版行為測試。

移除角色 → 引用此角色的對話降級為旁白；stage 三 lane 中屬於該角色的 segment 被清掉。
"""

from unittest.mock import patch

from src.core.models import (
    Character,
    Dialogue,
    Episode,
    Project,
    Scene,
    StageSegment,
)


def _make_project_with_char() -> Project:
    scene = Scene(
        id="場景1",
        dialogues=[
            Dialogue(type="dialogue", text=f"d{i}", character="小明")
            for i in range(3)
        ],
    )
    scene.stage_left.append(StageSegment(0, 0, "小明"))
    scene.stage_center.append(StageSegment(1, 1, "小明"))
    scene.stage_right.append(StageSegment(2, 2, "小明"))
    # 留一個別的角色 segment，不應受影響
    scene.stage_left.append(StageSegment(2, 2, "小華"))
    return Project(characters=[Character(name="小明"), Character(name="小華")],
                   episodes=[Episode(name="影片1", scenes=[scene])])


def test_remove_character_downgrades_dialogues_and_clears_stage(qapp):
    # main_window 需要 QApplication；qapp fixture 確保之
    from src.ui.main_window import MainWindow
    from PyQt6.QtWidgets import QMessageBox

    w = MainWindow()
    w._project = _make_project_with_char()

    # 略過確認對話框：patch 成 Yes
    with patch.object(QMessageBox, "question",
                      return_value=QMessageBox.StandardButton.Yes):
        w._on_remove_character(0)  # 移除「小明」

    scene = w._project.scenes[0]
    # 對話全變旁白
    for dlg in scene.dialogues:
        assert dlg.type == "narration"
        assert dlg.character is None
    # 三條 lane 的小明 segment 都沒了；小華 segment 還在
    assert scene.stage_left == [StageSegment(2, 2, "小華")]
    assert scene.stage_center == []
    assert scene.stage_right == []
    # characters 列表少了小明
    assert [c.name for c in w._project.characters] == ["小華"]
