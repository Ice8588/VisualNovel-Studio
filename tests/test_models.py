"""測試 models.py：序列化往返、邊緣案例。"""

from pathlib import Path

from src.core.models import Dialogue, Project, Scene


class TestDialogue:
    def test_dialogue_to_dict(self):
        d = Dialogue(type="dialogue", text="你好", character="小明", sprite="char_xm.png")
        result = d.to_dict()
        assert result == {
            "type": "dialogue",
            "text": "你好",
            "character": "小明",
            "sprite": "char_xm.png",
        }

    def test_narration_to_dict_null_fields(self):
        d = Dialogue(type="narration", text="他走了。")
        result = d.to_dict()
        assert result["character"] is None
        assert result["sprite"] is None

    def test_dialogue_roundtrip(self):
        original = Dialogue(type="dialogue", text="測試", character="角色A", sprite="s.png")
        restored = Dialogue.from_dict(original.to_dict())
        assert restored == original

    def test_narration_roundtrip(self):
        original = Dialogue(type="narration", text="旁白文字")
        restored = Dialogue.from_dict(original.to_dict())
        assert restored == original


class TestScene:
    def test_scene_to_dict(self):
        scene = Scene(
            id="scene_001",
            background="bg.png",
            bgm="bgm.mp3",
            dialogues=[
                Dialogue(type="narration", text="開場"),
                Dialogue(type="dialogue", text="你好", character="小明"),
            ],
        )
        result = scene.to_dict()
        assert result["id"] == "scene_001"
        assert result["background"] == "bg.png"
        assert len(result["dialogues"]) == 2

    def test_scene_roundtrip(self):
        original = Scene(
            id="scene_002",
            background="bg2.png",
            dialogues=[Dialogue(type="dialogue", text="台詞", character="A")],
        )
        restored = Scene.from_dict(original.to_dict())
        assert restored == original

    def test_scene_empty_dialogues(self):
        scene = Scene(id="scene_001")
        restored = Scene.from_dict(scene.to_dict())
        assert restored.dialogues == []
        assert restored.background is None
        assert restored.bgm is None


class TestProject:
    def test_project_roundtrip(self):
        original = Project(
            title="我的故事",
            scenes=[
                Scene(
                    id="scene_001",
                    background="bg_forest.png",
                    bgm="bgm_peaceful.mp3",
                    dialogues=[
                        Dialogue(type="narration", text="他站在窗邊。"),
                        Dialogue(type="dialogue", text="你真的要走嗎？", character="小花"),
                    ],
                ),
            ],
            assets={
                "backgrounds": ["bg_forest.png"],
                "sprites": [],
                "music": ["bgm_peaceful.mp3"],
            },
        )
        restored = Project.from_dict(original.to_dict())
        assert restored.title == original.title
        assert len(restored.scenes) == 1
        assert restored.scenes[0] == original.scenes[0]
        assert restored.assets == original.assets

    def test_project_default_values(self):
        p = Project()
        assert p.title == "Untitled"
        assert p.scenes == []
        assert p.assets == {"backgrounds": [], "sprites": [], "music": []}
        assert p.project_path is None

    def test_project_path_serialization(self):
        p = Project(project_path=Path("D:/test/my_project.vnsproj"))
        data = p.to_dict()
        assert data["project_path"] == "D:\\test\\my_project.vnsproj"
        restored = Project.from_dict(data)
        assert restored.project_path == Path("D:/test/my_project.vnsproj")

    def test_project_path_none(self):
        p = Project()
        data = p.to_dict()
        assert data["project_path"] is None
        restored = Project.from_dict(data)
        assert restored.project_path is None

    def test_to_script_json(self):
        p = Project(
            title="測試",
            scenes=[
                Scene(id="scene_001", dialogues=[
                    Dialogue(type="dialogue", text="哈囉", character="A"),
                ]),
            ],
        )
        result = p.to_script_json()
        assert result["title"] == "測試"
        assert len(result["scenes"]) == 1
        # script.json 不應包含 assets 和 project_path
        assert "assets" not in result
        assert "project_path" not in result

    def test_next_scene_id_empty(self):
        p = Project()
        assert p.next_scene_id() == "scene_001"

    def test_next_scene_id_sequential(self):
        p = Project(scenes=[
            Scene(id="scene_001"),
            Scene(id="scene_003"),
        ])
        assert p.next_scene_id() == "scene_004"

    def test_from_dict_missing_asset_categories(self):
        """缺少部分素材分類時應自動補齊。"""
        data = {
            "title": "test",
            "scenes": [],
            "assets": {"backgrounds": ["bg.png"]},
        }
        p = Project.from_dict(data)
        assert p.assets["backgrounds"] == ["bg.png"]
        assert p.assets["sprites"] == []
        assert p.assets["music"] == []
