"""CostumeEditorDialog：零服裝自動建服裝、移除確認。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from src.core.models import Character, Costume, SpriteVariant
from src.ui.dialogs import CostumeEditorDialog


def _png(tmp_path: Path, name: str = "pic.png") -> Path:
    """用 Pillow 產生合法 PNG——拖入流程會經 normalize_sprite 的 Pillow 解碼，假 bytes 會炸。"""
    from PIL import Image

    p = tmp_path / name
    Image.new("RGBA", (4, 4), (120, 160, 200, 255)).save(p)
    return p


def test_drop_image_on_empty_character_creates_costume(qapp, tmp_path, monkeypatch):
    """零服裝時拖圖進來 → 自動建「服裝1」並收下差分（修走查陷阱 P6）。"""
    monkeypatch.setattr(
        QInputDialog, "getText",
        staticmethod(lambda *a, **kw: ("微笑", True)),
    )
    char = Character(name="小美", costumes=[])
    dlg = CostumeEditorDialog(char, tmp_path)
    dlg._on_files_dropped([_png(tmp_path)])

    costumes = dlg.get_costumes()
    assert len(costumes) == 1
    assert costumes[0].name == "服裝1"
    assert [e.label for e in costumes[0].expressions] == ["微笑"]


def test_ensure_costume_reuses_existing(qapp, tmp_path):
    char = Character(name="小美", costumes=[Costume(name="校服")])
    dlg = CostumeEditorDialog(char, tmp_path)
    assert dlg._ensure_costume() == 0
    assert len(dlg.get_costumes()) == 1


def test_remove_costume_with_expressions_asks(qapp, tmp_path, monkeypatch):
    """移除含差分的服裝 → 跳確認；按 No 不刪（修走查陷阱 P7）。"""
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No),
    )
    char = Character(name="小美", costumes=[
        Costume(name="校服", expressions=[SpriteVariant("微笑", "a.png")]),
    ])
    dlg = CostumeEditorDialog(char, tmp_path)
    dlg._costume_list.setCurrentRow(0)
    dlg._on_remove_costume()
    assert len(dlg.get_costumes()) == 1


def test_remove_empty_costume_no_confirm(qapp, tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: asked.append(1) or QMessageBox.StandardButton.Yes),
    )
    char = Character(name="小美", costumes=[Costume(name="空服裝")])
    dlg = CostumeEditorDialog(char, tmp_path)
    dlg._costume_list.setCurrentRow(0)
    dlg._on_remove_costume()
    assert asked == []
    assert dlg.get_costumes() == []
