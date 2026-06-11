"""character_transfer：檔案去重複製、角色搬運（filename 改寫、缺檔回報）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.character_transfer import copy_file_dedup, import_character
from src.core.models import Character, Costume, SpriteVariant


class TestCopyFileDedup:
    def test_copies_new_file(self, tmp_path):
        src = tmp_path / "a.png"
        src.write_bytes(b"data")
        target = tmp_path / "assets"
        assert copy_file_dedup(src, target) == "a.png"
        assert (target / "a.png").read_bytes() == b"data"

    def test_same_content_reuses_existing(self, tmp_path):
        src = tmp_path / "a.png"
        src.write_bytes(b"data")
        target = tmp_path / "assets"
        target.mkdir()
        (target / "a.png").write_bytes(b"data")
        assert copy_file_dedup(src, target) == "a.png"
        assert list(target.iterdir()) == [target / "a.png"]  # 沒有 a_1.png

    def test_different_content_adds_suffix(self, tmp_path):
        src = tmp_path / "a.png"
        src.write_bytes(b"new")
        target = tmp_path / "assets"
        target.mkdir()
        (target / "a.png").write_bytes(b"old")
        assert copy_file_dedup(src, target) == "a_1.png"
        assert (target / "a.png").read_bytes() == b"old"   # 既有檔不被覆寫
        assert (target / "a_1.png").read_bytes() == b"new"


class TestImportCharacter:
    def _char(self) -> Character:
        return Character(name="小美", name_color="#E05555", costumes=[
            Costume(name="校服", expressions=[
                SpriteVariant("微笑", "smile.png"),
                SpriteVariant("生氣", "angry.png"),
            ]),
        ])

    def test_copies_sprites_and_returns_new_character(self, tmp_path):
        src_assets = tmp_path / "src"
        src_assets.mkdir()
        (src_assets / "smile.png").write_bytes(b"s")
        (src_assets / "angry.png").write_bytes(b"a")
        target = tmp_path / "dst"

        original = self._char()
        new_char, missing = import_character(original, src_assets, target)
        assert missing == []
        assert (target / "smile.png").exists()
        assert (target / "angry.png").exists()
        assert new_char is not original           # 深拷貝
        assert original.costumes[0].expressions[0].filename == "smile.png"  # 原物件不動

    def test_conflict_rewrites_filename(self, tmp_path):
        src_assets = tmp_path / "src"
        src_assets.mkdir()
        (src_assets / "smile.png").write_bytes(b"from-source")
        (src_assets / "angry.png").write_bytes(b"a")
        target = tmp_path / "dst"
        target.mkdir()
        (target / "smile.png").write_bytes(b"already-here")

        new_char, _ = import_character(self._char(), src_assets, target)
        filenames = [e.filename for e in new_char.costumes[0].expressions]
        assert "smile_1.png" in filenames  # 衝突改名且寫回 Character

    def test_missing_source_file_reported(self, tmp_path):
        src_assets = tmp_path / "src"
        src_assets.mkdir()
        (src_assets / "smile.png").write_bytes(b"s")
        # angry.png 缺檔

        new_char, missing = import_character(self._char(), src_assets, tmp_path / "dst")
        assert missing == ["angry.png"]
        # 缺檔差分保留原 filename，不複製
        assert new_char.costumes[0].expressions[1].filename == "angry.png"
