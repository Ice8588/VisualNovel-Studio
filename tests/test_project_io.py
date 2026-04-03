"""測試 project_io.py：存讀往返與錯誤處理。"""

import json
from pathlib import Path

import pytest

from src.core.models import Dialogue, Project, Scene
from src.core.project_io import load_project, save_project


@pytest.fixture
def sample_project():
    return Project(
        title="測試故事",
        scenes=[
            Scene(
                id="scene_001",
                background="bg_forest.png",
                bgm="bgm_peaceful.mp3",
                dialogues=[
                    Dialogue(type="narration", text="他站在窗邊。"),
                    Dialogue(type="dialogue", text="你好嗎？", character="小明", sprite="char_xm.png"),
                ],
            ),
            Scene(id="scene_002", dialogues=[]),
        ],
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
