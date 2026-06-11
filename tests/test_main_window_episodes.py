"""MainWindow 與影片切換的整合：切換後中央面板重新綁定、dirty 標記。"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QInputDialog

from src.core.models import Dialogue, Episode, Project, Scene
from src.ui.main_window import MainWindow


@pytest.fixture
def window(qapp):
    w = MainWindow()
    yield w
    w.center_panel.cleanup()
    w.deleteLater()


def test_switch_episode_rebinds_center_panel(window):
    e1 = Episode(name="一", scenes=[Scene(id="A", dialogues=[Dialogue(type="narration", text="x")])])
    e2 = Episode(name="二", scenes=[Scene(id="B")])
    window._project = Project(episodes=[e1, e2])
    window._rebuild_ui()

    window.left_panel.combo_episode.setCurrentIndex(1)
    # 中央面板的當前場景應屬於第二集
    assert window.center_panel._get_current_scene().id == "B"
    assert window._dirty


def test_menu_add_episode_creates_and_marks_dirty(window, monkeypatch):
    monkeypatch.setattr(
        QInputDialog, "getText",
        staticmethod(lambda *a, **kw: ("續集", True)),
    )
    window._dirty = False
    window._on_add_episode_menu()
    assert [e.name for e in window._project.episodes] == ["影片1", "續集"]
    assert window._project.active_episode_index == 1
    assert window._dirty
