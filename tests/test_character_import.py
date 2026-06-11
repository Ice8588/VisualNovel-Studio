"""CharacterImportDialog 勾選器 + MainWindow 匯入 handler。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from src.core.models import Character, Costume, Episode, Project, Scene, SpriteVariant
from src.core.project_io import save_project


def _source_project(tmp_path: Path) -> Path:
    """造一個含兩個角色的來源作品（立繪用 Pillow 產生，確保是合法 PNG）。"""
    from PIL import Image

    src_dir = tmp_path / "source_work"
    (src_dir / "assets").mkdir(parents=True)
    Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(src_dir / "assets" / "mei.png")
    p = Project(title="來源作品", characters=[
        Character(name="小美", name_color="#E05555", costumes=[
            Costume(name="校服", expressions=[SpriteVariant("微笑", "mei.png")]),
        ]),
        Character(name="小明", name_color="#336699", costumes=[]),
    ])
    proj_file = src_dir / "source.vnsproj"
    p.project_path = proj_file
    save_project(p, proj_file)
    return proj_file


def test_dialog_lists_characters_checked_by_default(qapp, tmp_path):
    from src.core.project_io import load_project
    from src.ui.character_import import CharacterImportDialog

    proj_file = _source_project(tmp_path)
    source = load_project(proj_file)
    dlg = CharacterImportDialog(source, proj_file.parent / "assets")
    assert dlg._char_list.count() == 2
    assert "小美" in dlg._char_list.item(0).text()
    assert dlg._char_list.item(0).checkState() == Qt.CheckState.Checked
    assert len(dlg.selected_characters()) == 2

    dlg._char_list.item(1).setCheckState(Qt.CheckState.Unchecked)
    assert [c.name for c in dlg.selected_characters()] == ["小美"]


def test_main_window_import_flow(qapp, tmp_path, monkeypatch):
    from src.ui.main_window import MainWindow
    import src.ui.character_import as ci

    proj_file = _source_project(tmp_path)
    w = MainWindow()
    try:
        target_file = tmp_path / "target" / "t.vnsproj"
        target_file.parent.mkdir(parents=True)
        monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **kw: None))
        w._project.project_path = target_file

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **kw: (str(proj_file), "")),
        )
        monkeypatch.setattr(ci.CharacterImportDialog, "exec", lambda self: QDialog.DialogCode.Accepted)

        w._on_import_characters_from_work()
        names = [c.name for c in w._project.characters]
        assert names == ["小美", "小明"]
        assert (target_file.parent / "assets" / "mei.png").exists()
        assert "mei.png" in w._project.assets["sprites"]
    finally:
        w.center_panel.cleanup()
        w.deleteLater()


def test_same_name_skip_on_no(qapp, tmp_path, monkeypatch):
    from src.ui.main_window import MainWindow
    import src.ui.character_import as ci

    proj_file = _source_project(tmp_path)
    w = MainWindow()
    try:
        w._project.project_path = tmp_path / "t2" / "t.vnsproj"
        w._project.project_path.parent.mkdir(parents=True)
        w._project.characters.append(Character(name="小美", name_color="#000000"))

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **kw: (str(proj_file), "")),
        )
        monkeypatch.setattr(ci.CharacterImportDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No))
        monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **kw: None))

        w._on_import_characters_from_work()
        # 小美被略過（保留原本黑色版本），小明照常匯入
        mei = [c for c in w._project.characters if c.name == "小美"]
        assert len(mei) == 1 and mei[0].name_color == "#000000"
        assert any(c.name == "小明" for c in w._project.characters)
    finally:
        w.center_panel.cleanup()
        w.deleteLater()
