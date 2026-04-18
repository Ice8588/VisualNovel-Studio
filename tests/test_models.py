"""測試 models.py：序列化往返、邊緣案例。"""

from pathlib import Path

from src.core.models import Character, Costume, Dialogue, GameSettings, Project, Scene, SpriteVariant


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
        path = Path("D:/test/my_project.vnsproj")
        p = Project(project_path=path)
        data = p.to_dict()
        # 序列化的字串應等於該平台下 str(path)（Windows 為反斜線、POSIX 為斜線）
        assert data["project_path"] == str(path)
        restored = Project.from_dict(data)
        assert restored.project_path == path

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
        assert p.next_scene_id() == "場景1"

    def test_next_scene_id_sequential(self):
        p = Project(scenes=[
            Scene(id="場景1"),
            Scene(id="場景3"),
        ])
        assert p.next_scene_id() == "場景4"

    def test_next_scene_id_legacy_compat(self):
        p = Project(scenes=[
            Scene(id="scene_001"),
            Scene(id="scene_003"),
        ])
        assert p.next_scene_id() == "場景4"

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


class TestGameSettings:
    def test_default_values(self):
        gs = GameSettings()
        assert gs.dialogue_font_size == 18
        assert gs.name_font_size == 16

    def test_from_dict_clamps_out_of_range(self):
        """E2：字體大小超出 [14,32] 時自動夾住。"""
        gs = GameSettings.from_dict({"dialogue_font_size": 10, "name_font_size": 48})
        assert gs.dialogue_font_size == 14
        assert gs.name_font_size == 32

    def test_from_dict_keeps_in_range(self):
        gs = GameSettings.from_dict({"dialogue_font_size": 20, "name_font_size": 18})
        assert gs.dialogue_font_size == 20
        assert gs.name_font_size == 18


class TestCharacterCostume:
    def test_old_format_auto_migrates_to_default_costume(self):
        """舊格式 JSON（flat sprites）→ 自動包進 default costume。"""
        data = {
            "name": "小明",
            "name_color": "#4682B4",
            "position": "left",
            "sprites": [
                {"label": "普通", "filename": "xm_normal.png"},
                {"label": "微笑", "filename": "xm_smile.png"},
            ],
        }
        char = Character.from_dict(data)
        assert len(char.costumes) == 1
        assert char.costumes[0].name == "預設"
        assert len(char.costumes[0].expressions) == 2
        # @property sprites 向下相容
        assert len(char.sprites) == 2
        assert char.sprites[0].label == "普通"

    def test_new_format_costume_roundtrip(self):
        """新格式 JSON（含 costumes）→ 正常讀寫往返。"""
        char = Character(
            name="小花",
            name_color="#ff0000",
            position="right",
            costumes=[
                Costume(name="校服", expressions=[
                    SpriteVariant(label="普通", filename="hana_school.png"),
                    SpriteVariant(label="開心", filename="hana_happy.png"),
                ]),
                Costume(name="便服", expressions=[
                    SpriteVariant(label="普通", filename="hana_casual.png"),
                ]),
            ],
        )
        restored = Character.from_dict(char.to_dict())
        assert restored.name == "小花"
        assert len(restored.costumes) == 2
        assert restored.costumes[0].name == "校服"
        assert len(restored.costumes[0].expressions) == 2
        assert restored.costumes[1].name == "便服"
        # sprites property 展平
        assert len(restored.sprites) == 3

    def test_to_script_json_outputs_flat_sprites(self):
        """to_script_json() 輸出扁平 sprites dict，engine.js 不需改動。"""
        p = Project(
            title="測試",
            characters=[
                Character(
                    name="角色A",
                    costumes=[
                        Costume(name="服裝1", expressions=[
                            SpriteVariant(label="普通", filename="a_normal.png"),
                        ]),
                        Costume(name="服裝2", expressions=[
                            SpriteVariant(label="開心", filename="a_happy.png"),
                        ]),
                    ],
                )
            ],
        )
        result = p.to_script_json()
        sprites = result["characters"]["角色A"]["sprites"]
        assert sprites == {"普通": "a_normal.png", "開心": "a_happy.png"}

    def test_dialogue_costume_field_serialization(self):
        """Dialogue 含 costume 欄位的序列化與反序列化。"""
        dlg = Dialogue(
            type="dialogue",
            text="你好",
            character="小明",
            sprite="普通",
            costume="校服",
        )
        data = dlg.to_dict()
        assert data["costume"] == "校服"
        restored = Dialogue.from_dict(data)
        assert restored.costume == "校服"

        # costume=None 時不應出現在 dict 中
        dlg_no_costume = Dialogue(type="narration", text="旁白")
        assert "costume" not in dlg_no_costume.to_dict()
