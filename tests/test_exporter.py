"""測試 exporter.py：ZIP 導出結構與內容。"""

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.exporter import ENGINE_DIR, export_zip
from src.core.models import Dialogue, Episode, Project, Scene


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
                    Dialogue(type="dialogue", text="你好", character="小明"),
                ],
            ),
        ])],
        assets={
            "backgrounds": ["bg_forest.png"],
            "sprites": ["char_xm.png"],
            "music": ["bgm_peaceful.mp3"],
        },
    )


@pytest.fixture
def fake_engine(tmp_path):
    """在暫存目錄建立假的 engine 檔案。"""
    engine_dir = tmp_path / "engine"
    engine_dir.mkdir()
    (engine_dir / "index.html").write_text(
        '<!DOCTYPE html><head><link rel="stylesheet" href="style.css"></head>'
        "<body><script src='engine.js'></script></body>",
        encoding="utf-8",
    )
    (engine_dir / "engine.js").write_text("// engine", encoding="utf-8")
    (engine_dir / "style.css").write_text("body { margin: 0; }", encoding="utf-8")
    return engine_dir


@pytest.fixture
def fake_assets(tmp_path):
    """在暫存目錄建立假的素材檔案。"""
    assets_dir = tmp_path / "project" / "assets"
    assets_dir.mkdir(parents=True)
    (assets_dir / "bg_forest.png").write_bytes(b"fake png")
    (assets_dir / "char_xm.png").write_bytes(b"fake sprite")
    (assets_dir / "bgm_peaceful.mp3").write_bytes(b"fake audio")
    return tmp_path / "project"


class TestExportZip:
    def test_creates_valid_zip(self, tmp_path, sample_project, fake_engine):
        output = tmp_path / "output.zip"
        with patch("src.core.exporter.ENGINE_DIR", fake_engine):
            export_zip(sample_project, output)
        assert output.exists()
        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
            assert "index.html" in names
            assert "engine.js" in names
            assert "data.js" in names
            assert "README.txt" in names

    def test_inlines_css(self, tmp_path, sample_project, fake_engine):
        output = tmp_path / "output.zip"
        with patch("src.core.exporter.ENGINE_DIR", fake_engine):
            export_zip(sample_project, output)
        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
            assert "style.css" not in names
            html = zf.read("index.html").decode("utf-8")
            assert "<style>" in html
            assert "body { margin: 0; }" in html
            assert 'href="style.css"' not in html

    def test_includes_assets(self, tmp_path, sample_project, fake_engine, fake_assets):
        sample_project.project_path = fake_assets / "test.vnsproj"
        output = tmp_path / "output.zip"
        with patch("src.core.exporter.ENGINE_DIR", fake_engine):
            export_zip(sample_project, output)
        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
            assert "assets/bg_forest.png" in names
            assert "assets/char_xm.png" in names
            assert "assets/bgm_peaceful.mp3" in names

    def test_data_js_content(self, tmp_path, sample_project, fake_engine):
        output = tmp_path / "output.zip"
        with patch("src.core.exporter.ENGINE_DIR", fake_engine):
            export_zip(sample_project, output)
        with zipfile.ZipFile(output, "r") as zf:
            data_js = zf.read("data.js").decode("utf-8")
            assert data_js.startswith("var SCRIPT_DATA = ")
            # 解析 data.js 中的 JSON
            json_str = data_js[len("var SCRIPT_DATA = "):-1]  # 去掉前綴和結尾分號
            data = json.loads(json_str)
            assert data["title"] == "測試故事"
            assert len(data["scenes"]) == 1
            assert data["scenes"][0]["dialogues"][1]["character"] == "小明"

    def test_missing_engine_raises(self, tmp_path, sample_project):
        empty_dir = tmp_path / "empty_engine"
        empty_dir.mkdir()
        output = tmp_path / "output.zip"
        with patch("src.core.exporter.ENGINE_DIR", empty_dir):
            with pytest.raises(FileNotFoundError, match="缺少引擎檔案"):
                export_zip(sample_project, output)

    def test_handles_missing_assets_gracefully(
        self, tmp_path, sample_project, fake_engine
    ):
        """素材檔案不存在時不阻斷導出（只是 ZIP 內沒有該素材）。"""
        sample_project.project_path = tmp_path / "no_assets" / "test.vnsproj"
        output = tmp_path / "output.zip"
        with patch("src.core.exporter.ENGINE_DIR", fake_engine):
            export_zip(sample_project, output)
        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
            assert "assets/bg_forest.png" not in names  # 不存在但不報錯
            assert "index.html" in names  # 其他檔案正常

    def test_chinese_content_not_escaped(self, tmp_path, sample_project, fake_engine):
        output = tmp_path / "output.zip"
        with patch("src.core.exporter.ENGINE_DIR", fake_engine):
            export_zip(sample_project, output)
        with zipfile.ZipFile(output, "r") as zf:
            data_js = zf.read("data.js").decode("utf-8")
            assert "測試故事" in data_js  # 不應是 \u escape
