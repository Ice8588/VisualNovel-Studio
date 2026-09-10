"""Phase 3：exporter_video.py 改用 state_at + _lookup_sprite_filename 的驗證。"""

from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.core.exporter_video import VideoExporter
from src.core.models import (
    Character,
    Costume,
    Dialogue,
    Project,
    Scene,
    SpriteVariant,
    StageSegment,
)


def _make_project_with_stage(tmp_path: Path) -> Project:
    # 建立一張測試 sprite
    sprite_path = tmp_path / "assets" / "xm_smile.png"
    sprite_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (64, 128), (255, 0, 0, 255)).save(sprite_path)

    proj = Project(
        title="T",
        characters=[
            Character(
                name="小明",
                name_color="#4682B4",
                costumes=[Costume(
                    name="便服",
                    expressions=[SpriteVariant(label="微笑", filename="xm_smile.png")],
                )],
            )
        ],
    )
    scene = Scene(
        id="s1",
        background=None,
        dialogues=[Dialogue(type="dialogue", text="hi", character="小明")],
    )
    scene.stage_center.append(StageSegment(0, 0, "小明", costume="便服", sprite="微笑"))
    proj.scenes.append(scene)
    proj.project_path = tmp_path / "proj.vnsproj"
    return proj


def test_lookup_sprite_filename_hits_expression(tmp_path):
    proj = _make_project_with_stage(tmp_path)
    with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
        exporter = VideoExporter(proj, tmp_path / "out.mp4", resolution=(640, 360))
    seg = proj.scenes[0].stage_center[0]
    assert exporter._lookup_sprite_filename(seg) == "xm_smile.png"


def test_lookup_sprite_filename_unknown_character_returns_none(tmp_path):
    proj = _make_project_with_stage(tmp_path)
    with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
        exporter = VideoExporter(proj, tmp_path / "out.mp4", resolution=(640, 360))
    seg = StageSegment(0, 0, "不存在的角色")
    assert exporter._lookup_sprite_filename(seg) is None


def test_lookup_sprite_filename_missing_sprite_label_returns_none(tmp_path):
    proj = _make_project_with_stage(tmp_path)
    with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
        exporter = VideoExporter(proj, tmp_path / "out.mp4", resolution=(640, 360))
    seg = StageSegment(0, 0, "小明", costume="便服", sprite="不存在的差分")
    assert exporter._lookup_sprite_filename(seg) is None


def test_lookup_sprite_filename_without_costume_picks_first(tmp_path):
    proj = _make_project_with_stage(tmp_path)
    with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
        exporter = VideoExporter(proj, tmp_path / "out.mp4", resolution=(640, 360))
    seg = StageSegment(0, 0, "小明")  # 無 costume / sprite
    assert exporter._lookup_sprite_filename(seg) == "xm_smile.png"


def test_state_at_used_for_sprite_path(tmp_path, monkeypatch):
    """確認 _generate_frames 從 state_at 抓 stage segment 後解析成 sprite_path。"""
    proj = _make_project_with_stage(tmp_path)
    with patch("src.core.exporter_video.find_ffmpeg", return_value=Path("ffmpeg")):
        exporter = VideoExporter(proj, tmp_path / "out.mp4", resolution=(320, 180))

    # 攔截 render_frame 看它收到的 sprite_path 與 position
    captured: dict = {}

    original_render = exporter._renderer.render_frame

    def spy_render(bg_path, sprite_path, character, text, dlg_type,
                   name_color=None, position="center"):
        captured["sprite_path"] = sprite_path
        captured["position"] = position
        captured["character"] = character
        return original_render(
            bg_path, sprite_path, character, text, dlg_type,
            name_color=name_color, position=position,
        )

    exporter._renderer.render_frame = spy_render  # type: ignore

    # 直接跑 _generate_frames（不經 ffmpeg 編碼）
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        exporter._generate_frames(Path(td), None, total_dialogues=1)

    assert captured["sprite_path"] is not None
    assert captured["sprite_path"].name == "xm_smile.png"
    assert captured["position"] == "center"
    assert captured["character"] == "小明"
