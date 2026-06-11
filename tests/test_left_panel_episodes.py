"""LeftPanel 影片切換列：漸進揭露、切換、新增、刪除。"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from src.core.models import Episode, Project, Scene
from src.ui.left_panel import LeftPanel


def test_episode_bar_hidden_when_single_episode(qapp):
    panel = LeftPanel()
    panel.set_project(Project())
    assert not panel._episode_bar.isVisibleTo(panel)


def test_episode_bar_visible_when_multi(qapp):
    p = Project(episodes=[Episode(name="一"), Episode(name="二")])
    panel = LeftPanel()
    panel.set_project(p)
    assert panel._episode_bar.isVisibleTo(panel)
    assert [panel.combo_episode.itemText(i) for i in range(panel.combo_episode.count())] == ["一", "二"]


def test_combo_switch_updates_active_and_scene_list(qapp):
    e1 = Episode(name="一", scenes=[Scene(id="A")])
    e2 = Episode(name="二", scenes=[Scene(id="B"), Scene(id="C")])
    p = Project(episodes=[e1, e2])
    panel = LeftPanel()
    panel.set_project(p)
    fired = []
    panel.episode_switched.connect(fired.append)

    panel.combo_episode.setCurrentIndex(1)
    assert p.active_episode_index == 1
    assert fired == [1]
    assert panel.scene_list.count() == 2  # 已切到第二集的場景


def test_add_episode_switches_and_reveals_bar(qapp, monkeypatch):
    monkeypatch.setattr(
        QInputDialog, "getText",
        staticmethod(lambda *a, **kw: ("第二集", True)),
    )
    p = Project()
    panel = LeftPanel()
    panel.set_project(p)
    fired = []
    panel.episodes_changed.connect(lambda: fired.append(1))

    panel.add_episode()
    assert [e.name for e in p.episodes] == ["影片1", "第二集"]
    assert p.active_episode_index == 1
    assert panel._episode_bar.isVisibleTo(panel)
    assert fired == [1]


def test_remove_episode_with_confirm(qapp, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )
    p = Project(episodes=[Episode(name="一"), Episode(name="二", scenes=[Scene(id="B")])])
    p.active_episode_index = 1
    panel = LeftPanel()
    panel.set_project(p)

    panel._on_remove_episode()
    assert [e.name for e in p.episodes] == ["一"]
    assert p.active_episode_index == 0
    assert not panel._episode_bar.isVisibleTo(panel)  # 回到單影片 → 隱藏


def test_remove_episode_cancelled(qapp, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No),
    )
    p = Project(episodes=[Episode(name="一"), Episode(name="二")])
    panel = LeftPanel()
    panel.set_project(p)
    panel._on_remove_episode()
    assert len(p.episodes) == 2
