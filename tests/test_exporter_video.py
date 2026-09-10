"""測試 exporter_video.py：幀合成、文字換行、轉場、ffmpeg 管線。"""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw

from src.core.exporter_video import (
    FrameRenderer,
    VideoExporter,
    _wrap_text,
    find_ffmpeg,
    render_transition_frame,
)
from src.core.models import Dialogue, Project, Scene


@pytest.fixture
def renderer():
    return FrameRenderer(resolution=(640, 360))


@pytest.fixture
def test_bg(tmp_path):
    """建立測試用背景圖。"""
    img = Image.new("RGB", (640, 360), (100, 150, 200))
    path = tmp_path / "bg.png"
    img.save(path)
    return path


@pytest.fixture
def test_sprite(tmp_path):
    """建立測試用立繪（含透明通道）。"""
    img = Image.new("RGBA", (200, 400), (255, 0, 0, 200))
    path = tmp_path / "sprite.png"
    img.save(path)
    return path


class TestFrameRenderer:
    def test_output_dimensions(self, renderer):
        frame = renderer.render_frame(None, None, None, "測試", "narration")
        assert frame.size == (640, 360)

    def test_output_is_rgb(self, renderer):
        frame = renderer.render_frame(None, None, None, "測試", "narration")
        assert frame.mode == "RGB"

    def test_null_background_produces_dark_frame(self, renderer):
        frame = renderer.render_frame(None, None, None, "測試", "narration")
        # 左上角應該是深靛色背景（42, 42, 62）
        pixel = frame.getpixel((10, 10))
        assert pixel == (42, 42, 62)

    def test_with_background(self, renderer, test_bg):
        frame = renderer.render_frame(test_bg, None, None, "測試", "narration")
        # 左上角應該是背景色（100, 150, 200）
        pixel = frame.getpixel((10, 10))
        assert pixel == (100, 150, 200)

    def test_null_sprite_still_renders(self, renderer, test_bg):
        frame = renderer.render_frame(test_bg, None, "角色", "台詞", "dialogue")
        assert frame.size == (640, 360)

    def test_with_sprite(self, renderer, test_bg, test_sprite):
        frame = renderer.render_frame(test_bg, test_sprite, "角色", "台詞", "dialogue")
        assert frame.size == (640, 360)

    def test_narration_no_nameplate(self, renderer):
        """旁白模式不繪製名稱牌。"""
        frame_narration = renderer.render_frame(None, None, None, "旁白", "narration")
        frame_dialogue = renderer.render_frame(None, None, "角色", "台詞", "dialogue")
        # 兩幀在名稱牌區域應該不同
        assert frame_narration != frame_dialogue

    def test_background_cache(self, renderer, test_bg):
        """相同背景不重複載入。"""
        renderer.render_frame(test_bg, None, None, "第一次", "narration")
        assert str(test_bg) in renderer._bg_cache
        renderer.render_frame(test_bg, None, None, "第二次", "narration")
        # 仍然只有一個快取條目
        assert len(renderer._bg_cache) == 1

    def test_nonexistent_background(self, renderer):
        """背景檔案不存在時使用預設深靛色背景。"""
        frame = renderer.render_frame(
            Path("nonexistent.png"), None, None, "測試", "narration"
        )
        pixel = frame.getpixel((10, 10))
        assert pixel == (42, 42, 62)

    def test_nonexistent_sprite(self, renderer, test_bg):
        """立繪檔案不存在時跳過。"""
        frame = renderer.render_frame(
            test_bg, Path("nonexistent.png"), "角色", "台詞", "dialogue"
        )
        assert frame.size == (640, 360)


class TestWrapText:
    def test_short_text(self):
        img = Image.new("RGB", (640, 360))
        draw = ImageDraw.Draw(img)
        font = renderer_font()
        lines = _wrap_text(draw, "短", font, 500)
        assert len(lines) == 1
        assert lines[0] == "短"

    def test_long_text_wraps(self):
        img = Image.new("RGB", (640, 360))
        draw = ImageDraw.Draw(img)
        font = renderer_font()
        long_text = "這是一段很長的文字" * 10
        lines = _wrap_text(draw, long_text, font, 200)
        assert len(lines) > 1

    def test_empty_text(self):
        img = Image.new("RGB", (640, 360))
        draw = ImageDraw.Draw(img)
        font = renderer_font()
        lines = _wrap_text(draw, "", font, 500)
        assert lines == []


def renderer_font():
    """取得測試用字體。"""
    r = FrameRenderer(resolution=(640, 360))
    return r._text_font


class TestTransitionFrame:
    def test_alpha_zero_returns_frame1(self):
        f1 = Image.new("RGB", (100, 100), (255, 0, 0))
        f2 = Image.new("RGB", (100, 100), (0, 0, 255))
        result = render_transition_frame(f1, f2, 0.0)
        assert result.getpixel((50, 50)) == (255, 0, 0)

    def test_alpha_one_returns_frame2(self):
        f1 = Image.new("RGB", (100, 100), (255, 0, 0))
        f2 = Image.new("RGB", (100, 100), (0, 0, 255))
        result = render_transition_frame(f1, f2, 1.0)
        assert result.getpixel((50, 50)) == (0, 0, 255)

    def test_alpha_half_blends(self):
        f1 = Image.new("RGB", (100, 100), (200, 0, 0))
        f2 = Image.new("RGB", (100, 100), (0, 200, 0))
        result = render_transition_frame(f1, f2, 0.5)
        pixel = result.getpixel((50, 50))
        assert 90 <= pixel[0] <= 110  # ~100
        assert 90 <= pixel[1] <= 110  # ~100


class TestFindFfmpeg:
    def test_raises_when_not_found(self):
        with patch("src.core.exporter_video.shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(FileNotFoundError, match="找不到 ffmpeg"):
                    find_ffmpeg()


class TestVideoExporter:
    @pytest.fixture
    def sample_project(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        assets_dir = project_dir / "assets"
        assets_dir.mkdir()
        # 建立假素材
        bg = Image.new("RGB", (100, 100), (50, 100, 150))
        bg.save(assets_dir / "bg.png")

        p = Project(
            title="測試",
            scenes=[
                Scene(
                    id="scene_001",
                    background="bg.png",
                    dialogues=[
                        Dialogue(type="narration", text="旁白"),
                        Dialogue(type="dialogue", text="台詞", character="角色A"),
                    ],
                ),
            ],
            assets={"backgrounds": ["bg.png"], "sprites": [], "music": []},
            project_path=project_dir / "test.vnsproj",
        )
        return p

    def test_export_calls_ffmpeg(self, tmp_path, sample_project):
        output = tmp_path / "test.mp4"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                exporter = VideoExporter(
                    sample_project, output, resolution=(320, 180), fps=1
                )
                exporter.export()
                assert mock_run.called

    def test_export_empty_project_raises(self, tmp_path):
        p = Project(title="空")
        output = tmp_path / "test.mp4"
        with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
            exporter = VideoExporter(p, output)
            with pytest.raises(ValueError, match="沒有場景"):
                exporter.export()

    def test_export_no_dialogues_raises(self, tmp_path):
        p = Project(title="空場景", scenes=[Scene(id="s1")])
        output = tmp_path / "test.mp4"
        with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
            exporter = VideoExporter(p, output)
            with pytest.raises(ValueError, match="沒有對話"):
                exporter.export()

    def test_progress_callback(self, tmp_path, sample_project):
        output = tmp_path / "test.mp4"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        progress_calls = []

        with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
            with patch("subprocess.run", return_value=mock_result):
                exporter = VideoExporter(
                    sample_project, output, resolution=(320, 180), fps=1
                )
                exporter.export(progress_callback=lambda c, t: progress_calls.append((c, t)))
                assert len(progress_calls) == 2  # 2 段對話
                assert progress_calls[-1] == (2, 2)

    def test_concat_file_format(self, tmp_path, sample_project):
        """驗證 concat 文件格式正確。"""
        output = tmp_path / "test.mp4"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
            with patch("subprocess.run", return_value=mock_result):
                exporter = VideoExporter(
                    sample_project, output, resolution=(320, 180), fps=1,
                )
                # 手動執行幀生成來檢查 concat
                temp_dir = Path(tmp_path / "frames")
                temp_dir.mkdir()
                concat_entries, _ = exporter._generate_frames(temp_dir, None, 2)

                concat_path = temp_dir / "concat.txt"
                exporter._write_concat_file(concat_path, concat_entries)

                content = concat_path.read_text(encoding="utf-8")
                assert "file 'frame_00000.png'" in content
                # 停留時間由字數決定（不再是固定值）
                assert "duration" in content
