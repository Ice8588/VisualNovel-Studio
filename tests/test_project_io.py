"""測試 project_io.py：存讀往返與錯誤處理。"""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.models import Dialogue, Episode, Project, Scene
from src.core.project_io import load_project, save_project


@pytest.fixture
def sample_project():
    return Project(
        title="測試故事",
        episodes=[Episode(name="影片1", scenes=[
            Scene(
                id="scene_001",
                background="bg_forest.png",
                bgm="bgm_peaceful.mp3",
                dialogues=[
                    Dialogue(type="narration", text="他站在窗邊。"),
                    Dialogue(type="dialogue", text="你好嗎？", character="小明"),
                ],
            ),
            Scene(id="scene_002", dialogues=[]),
        ])],
        assets={
            "backgrounds": ["bg_forest.png"],
            "sprites": ["char_xm.png"],
            "music": ["bgm_peaceful.mp3"],
        },
    )


class TestSaveAndLoad:
    def test_roundtrip(self, tmp_path, sample_project):
        filepath = tmp_path / "test.vnsproj"
        save_project(sample_project, filepath)

        loaded = load_project(filepath)
        assert loaded.title == "測試故事"
        assert len(loaded.scenes) == 2
        assert loaded.scenes[0].background == "bg_forest.png"
        assert len(loaded.scenes[0].dialogues) == 2
        assert loaded.scenes[0].dialogues[1].character == "小明"
        assert loaded.assets["sprites"] == ["char_xm.png"]
        assert loaded.project_path == filepath

    def test_save_creates_file(self, tmp_path, sample_project):
        filepath = tmp_path / "output.vnsproj"
        save_project(sample_project, filepath)
        assert filepath.exists()

    def test_save_is_valid_json(self, tmp_path, sample_project):
        filepath = tmp_path / "test.vnsproj"
        save_project(sample_project, filepath)
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data["title"] == "測試故事"

    def test_save_updates_project_path(self, tmp_path, sample_project):
        filepath = tmp_path / "test.vnsproj"
        save_project(sample_project, filepath)
        assert sample_project.project_path == filepath

    def test_load_nonexistent_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_project(tmp_path / "nonexistent.vnsproj")

    def test_load_invalid_json(self, tmp_path):
        filepath = tmp_path / "bad.vnsproj"
        filepath.write_text("not valid json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_project(filepath)

    def test_empty_project_roundtrip(self, tmp_path):
        project = Project()
        filepath = tmp_path / "empty.vnsproj"
        save_project(project, filepath)

        loaded = load_project(filepath)
        assert loaded.title == "Untitled"
        assert loaded.scenes == []

    def test_chinese_content_preserved(self, tmp_path):
        """確保中文內容不會被轉為 unicode escape。"""
        project = Project(title="繁體中文標題")
        filepath = tmp_path / "chinese.vnsproj"
        save_project(project, filepath)

        raw = filepath.read_text(encoding="utf-8")
        assert "繁體中文標題" in raw  # 不應是 \u escape


class TestSaveMigratesAssets:
    """Bug 1：save_project 必須把 assets/ 從來源搬到目標。"""

    def test_save_migrates_assets_from_temp(self, tmp_path, monkeypatch):
        """首次另存（project_path=None）→ 從 %TEMP%/vnstudio_unsaved/assets 搬到目標。"""
        fake_tmp = tmp_path / "tmpdir"
        fake_tmp.mkdir()
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(fake_tmp))

        unsaved = fake_tmp / "vnstudio_unsaved" / "assets"
        unsaved.mkdir(parents=True)
        (unsaved / "bg.png").write_bytes(b"fake-bg")

        target_dir = tmp_path / "project"
        target_dir.mkdir()
        target = target_dir / "proj.vnsproj"

        project = Project(title="t")
        save_project(project, target)

        assert (target_dir / "assets" / "bg.png").exists()
        assert (target_dir / "assets" / "bg.png").read_bytes() == b"fake-bg"

    def test_save_as_copies_across_dirs(self, tmp_path):
        """既存專案另存到別處 → 從 dir1/assets 複製到 dir2/assets，dir1 仍保留。"""
        dir1 = tmp_path / "p1"
        dir1.mkdir()
        (dir1 / "assets").mkdir()
        (dir1 / "assets" / "bg.png").write_bytes(b"abc")
        proj1_path = dir1 / "p1.vnsproj"
        project = Project(title="t", project_path=proj1_path)

        dir2 = tmp_path / "p2"
        dir2.mkdir()
        proj2_path = dir2 / "p2.vnsproj"

        save_project(project, proj2_path)

        assert (dir2 / "assets" / "bg.png").exists()
        assert (dir2 / "assets" / "bg.png").read_bytes() == b"abc"
        assert (dir1 / "assets" / "bg.png").exists()  # 來源不該被 move

    def test_save_in_place_idempotent(self, tmp_path):
        """同位置重複 save 不應崩潰（src.resolve() == dst.resolve() → 跳過 copytree）。"""
        d = tmp_path / "p"
        d.mkdir()
        (d / "assets").mkdir()
        (d / "assets" / "bg.png").write_bytes(b"x")
        path = d / "p.vnsproj"
        project = Project(title="t", project_path=path)

        save_project(project, path)
        save_project(project, path)  # 第二次：source == target

        assert (d / "assets" / "bg.png").exists()
        assert (d / "assets" / "bg.png").read_bytes() == b"x"
