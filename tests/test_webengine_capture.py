"""測試 webengine_capture.py：截幀導出器。"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.models import Dialogue, Project, Scene


# ── 不需要 Qt 的純邏輯測試 ──

class TestCalcDuration:
    """_calc_duration 與 v1 使用同一公式。"""

    def test_short_text(self):
        from src.ui.webengine_capture import _calc_duration
        assert _calc_duration("短") == 1.5  # 1.0 + 1*0.15 = 1.15 → clamped to 1.5

    def test_medium_text(self):
        from src.ui.webengine_capture import _calc_duration
        d = _calc_duration("十個字的測試文字啊啊")  # 10 chars → 1.0 + 1.5 = 2.5
        assert d == 2.5

    def test_long_text_capped(self):
        from src.ui.webengine_capture import _calc_duration
        d = _calc_duration("字" * 100)  # 1.0 + 15.0 → capped to 8.0
        assert d == 8.0

    def test_empty_text(self):
        from src.ui.webengine_capture import _calc_duration
        assert _calc_duration("") == 1.5


class TestWriteConcatFile:
    def test_basic_format(self, tmp_path):
        from src.ui.webengine_capture import WebEngineVideoExporter

        with patch("src.ui.webengine_capture.WebEngineVideoExporter.__init__",
                   lambda self, *a, **kw: None):
            exporter = WebEngineVideoExporter.__new__(WebEngineVideoExporter)

        path = tmp_path / "concat.txt"
        entries = [("frame_000000.png", 2.5), ("frame_000001.png", 1.5)]
        exporter._write_concat_file(path, entries)

        content = path.read_text(encoding="utf-8")
        assert "file 'frame_000000.png'" in content
        assert "duration 2.5000" in content
        assert "file 'frame_000001.png'" in content
        # 最後一行應該是重複的 file 行（ffmpeg concat 規範）
        lines = content.strip().split("\n")
        assert lines[-1] == "file 'frame_000001.png'"

    def test_empty_entries(self, tmp_path):
        from src.ui.webengine_capture import WebEngineVideoExporter

        with patch("src.ui.webengine_capture.WebEngineVideoExporter.__init__",
                   lambda self, *a, **kw: None):
            exporter = WebEngineVideoExporter.__new__(WebEngineVideoExporter)

        path = tmp_path / "concat.txt"
        exporter._write_concat_file(path, [])
        assert path.read_text(encoding="utf-8") == ""


class TestPrepareEngineFiles:
    """測試引擎檔案準備邏輯（注入 SCRIPT_DATA + VN_CAPTURE_MODE）。"""

    def test_html_injection(self, tmp_path):
        from src.ui.webengine_capture import WebEngineVideoExporter

        project = Project(
            title="測試",
            scenes=[Scene(id="s1", dialogues=[Dialogue(type="narration", text="旁白")])],
        )

        with patch("src.ui.webengine_capture.WebEngineVideoExporter.__init__",
                   lambda self, *a, **kw: None):
            exporter = WebEngineVideoExporter.__new__(WebEngineVideoExporter)
            exporter._project = project
            exporter._resolution = (640, 360)

        exporter._prepare_engine_files(tmp_path)

        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "VN_CAPTURE_MODE = true" in html
        assert "SCRIPT_DATA" in html
        # engine.js 和 effects.js 應該都被複製
        assert (tmp_path / "engine.js").exists()
        assert (tmp_path / "effects.js").exists()
        assert (tmp_path / "style.css").exists()


class TestExportValidation:
    """測試導出前的驗證邏輯。"""

    def test_empty_project_raises(self):
        from src.ui.webengine_capture import WebEngineVideoExporter

        project = Project(title="空")
        with patch("src.core.ffmpeg_manager.ensure_ffmpeg_or_raise",
                   return_value=Path("ffmpeg")):
            exporter = WebEngineVideoExporter(project, Path("out.mp4"))
            with pytest.raises(ValueError, match="沒有場景"):
                exporter.export()

    def test_no_dialogues_raises(self):
        from src.ui.webengine_capture import WebEngineVideoExporter

        project = Project(title="空場景", scenes=[Scene(id="s1")])
        with patch("src.core.ffmpeg_manager.ensure_ffmpeg_or_raise",
                   return_value=Path("ffmpeg")):
            exporter = WebEngineVideoExporter(project, Path("out.mp4"))
            with pytest.raises(ValueError, match="沒有對話"):
                exporter.export()
