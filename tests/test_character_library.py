"""測試 character_library.py：save → list → load 迴圈、檔名衝突處理。"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.core.character_library import (
    CARD_EXTENSION,
    delete_card,
    list_cards,
    load_card,
    save_card,
)
from src.core.models import Character, Costume, SpriteVariant


def _make_sprite(dir_: Path, name: str, content: bytes = b"fake_png") -> None:
    (dir_ / name).write_bytes(content)


def _build_character(name: str = "小明") -> Character:
    return Character(
        name=name,
        name_color="#4682B4",
        costumes=[
            Costume(name="預設", expressions=[
                SpriteVariant(label="普通", filename="xm_normal.png"),
                SpriteVariant(label="微笑", filename="xm_smile.png"),
            ]),
        ],
    )


class TestSaveListLoad:
    def test_save_creates_vncard(self, tmp_path: Path):
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")

        card_dir = tmp_path / "cards"
        path = save_card(_build_character(), assets, target_dir=card_dir)
        assert path.exists()
        assert path.suffix == CARD_EXTENSION
        assert path.parent == card_dir

        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        assert "character.json" in names
        assert "assets/xm_normal.png" in names
        assert "assets/xm_smile.png" in names

    def test_list_cards(self, tmp_path: Path):
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")

        card_dir = tmp_path / "cards"
        save_card(_build_character("A"), assets, target_dir=card_dir)
        save_card(_build_character("B"), assets, target_dir=card_dir)

        cards = list_cards(card_dir)
        assert len(cards) == 2
        assert all(c.suffix == CARD_EXTENSION for c in cards)

    def test_load_restores_character(self, tmp_path: Path):
        src_assets = tmp_path / "src_assets"
        src_assets.mkdir()
        _make_sprite(src_assets, "xm_normal.png")
        _make_sprite(src_assets, "xm_smile.png")

        card_dir = tmp_path / "cards"
        card_path = save_card(_build_character(), src_assets, target_dir=card_dir)

        dst_assets = tmp_path / "dst_assets"
        char, written = load_card(card_path, dst_assets)

        assert char.name == "小明"
        assert len(char.costumes) == 1
        labels = [e.label for e in char.costumes[0].expressions]
        assert labels == ["普通", "微笑"]
        # 立繪被複製到目的
        assert (dst_assets / "xm_normal.png").exists()
        assert (dst_assets / "xm_smile.png").exists()
        assert set(written) == {"xm_normal.png", "xm_smile.png"}

    def test_load_handles_filename_conflict(self, tmp_path: Path):
        src_assets = tmp_path / "src_assets"
        src_assets.mkdir()
        _make_sprite(src_assets, "xm_normal.png", b"source")

        card_dir = tmp_path / "cards"
        card_path = save_card(_build_character(), src_assets, target_dir=card_dir)

        dst_assets = tmp_path / "dst_assets"
        dst_assets.mkdir()
        # 目的目錄已有同檔名但內容不同
        (dst_assets / "xm_normal.png").write_bytes(b"existing")

        char, written = load_card(card_path, dst_assets)
        # 原檔保留，來源改名
        assert (dst_assets / "xm_normal.png").read_bytes() == b"existing"
        # 新寫入的檔案有 _1 後綴
        assert (dst_assets / "xm_normal_1.png").exists()
        # Character 內 filename 指到改名後版本
        filenames = [e.filename for e in char.costumes[0].expressions]
        assert "xm_normal_1.png" in filenames
        assert "xm_normal.png" not in filenames
        assert "xm_normal_1.png" in written

    def test_save_name_conflict_adds_suffix(self, tmp_path: Path):
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")

        card_dir = tmp_path / "cards"
        first = save_card(_build_character("重複"), assets, target_dir=card_dir)
        second = save_card(_build_character("重複"), assets, target_dir=card_dir)
        assert first != second
        assert "重複_1" in second.name or "重複_1" in str(second)

    def test_unsafe_characters_in_name(self, tmp_path: Path):
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")

        card = _build_character("a/b:c*d?")
        path = save_card(card, assets, target_dir=tmp_path / "cards")
        # 檔名不應包含原始危險字元
        for bad in "/\\:*?":
            assert bad not in path.name.replace(".vncard", "")

    def test_load_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_card(tmp_path / "nope.vncard", tmp_path / "assets")

    def test_load_invalid_card_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.vncard"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("unrelated.txt", "hi")
        with pytest.raises(ValueError):
            load_card(bad, tmp_path / "assets")


class TestDelete:
    def test_delete_removes_card(self, tmp_path: Path):
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")

        path = save_card(_build_character(), assets, target_dir=tmp_path / "cards")
        assert path.exists()
        delete_card(path)
        assert not path.exists()

    def test_delete_missing_silent(self, tmp_path: Path):
        delete_card(tmp_path / "never.vncard")  # 不應拋錯
