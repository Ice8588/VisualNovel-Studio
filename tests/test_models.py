"""測試 models.py：序列化往返、邊緣案例。"""

from pathlib import Path

from src.core.models import Character, Costume, Dialogue, GameSettings, Project, Scene, SpriteVariant
from src.core.models import Episode


class TestDialogue:
    def test_dialogue_to_dict(self):
        d = Dialogue(type="dialogue", text="你好", character="小明")
        result = d.to_dict()
        assert result == {
            "type": "dialogue",
            "text": "你好",
            "character": "小明",
        }

    def test_dialogue_to_dict_omits_empty_text_effects(self):
        d = Dialogue(type="dialogue", text="hi", character="A")
        assert "text_effects" not in d.to_dict()

    def test_dialogue_to_dict_includes_text_effects(self):
        d = Dialogue(type="dialogue", text="hi", character="A", text_effects=["bold", "italic"])
        assert d.to_dict()["text_effects"] == ["bold", "italic"]

    def test_narration_to_dict_null_character(self):
        d = Dialogue(type="narration", text="他走了。")
        result = d.to_dict()
        assert result["character"] is None

    def test_dialogue_to_dict_no_legacy_fields(self):
        """Phase 1：sprite / costume / stage 已從 Dialogue 移除，序列化不應輸出。"""
        d = Dialogue(type="dialogue", text="hi", character="A")
        out = d.to_dict()
        assert "sprite" not in out
        assert "costume" not in out
        assert "stage" not in out
        assert "effects" not in out  # 改名為 text_effects

    def test_dialogue_roundtrip(self):
        original = Dialogue(type="dialogue", text="測試", character="角色A", text_effects=["shake"])
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
            episodes=[Episode(name="影片1", scenes=[
                Scene(
                    id="scene_001",
                    background="bg_forest.png",
                    bgm="bgm_peaceful.mp3",
                    dialogues=[
                        Dialogue(type="narration", text="他站在窗邊。"),
                        Dialogue(type="dialogue", text="你真的要走嗎？", character="小花"),
                    ],
                ),
            ])],
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
            episodes=[Episode(name="影片1", scenes=[
                Scene(id="scene_001", dialogues=[
                    Dialogue(type="dialogue", text="哈囉", character="A"),
                ]),
            ])],
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
        p = Project(episodes=[Episode(name="影片1", scenes=[
            Scene(id="場景1"),
            Scene(id="場景3"),
        ])])
        assert p.next_scene_id() == "場景4"

    def test_next_scene_id_legacy_compat(self):
        p = Project(episodes=[Episode(name="影片1", scenes=[
            Scene(id="scene_001"),
            Scene(id="scene_003"),
        ])])
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
        """字體大小超出 [14,28] 時自動夾住。"""
        gs = GameSettings.from_dict({"dialogue_font_size": 10, "name_font_size": 48})
        assert gs.dialogue_font_size == 14
        assert gs.name_font_size == 28

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
        assert char.costumes[0].name == "服裝1"
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


class TestEpisodes:
    def test_default_project_has_one_episode(self):
        p = Project()
        assert len(p.episodes) == 1
        assert p.episodes[0].name == "影片1"
        # scenes property 是 active episode 的 live reference
        assert p.scenes is p.episodes[0].scenes

    def test_scenes_property_follows_active_episode(self):
        e1 = Episode(name="第一集", scenes=[Scene(id="A")])
        e2 = Episode(name="第二集", scenes=[Scene(id="B")])
        p = Project(episodes=[e1, e2])
        assert [s.id for s in p.scenes] == ["A"]
        p.active_episode_index = 1
        assert [s.id for s in p.scenes] == ["B"]

    def test_scenes_setter_writes_into_active_episode(self):
        # left_panel 場景拖曳排序會做 project.scenes = new_order，必須寫進 active episode
        p = Project()
        p.scenes = [Scene(id="X")]
        assert [s.id for s in p.episodes[0].scenes] == ["X"]

    def test_to_dict_writes_v2(self):
        p = Project(title="作品", episodes=[
            Episode(name="第一集", scenes=[Scene(id="A")]),
            Episode(name="第二集"),
        ])
        p.active_episode_index = 1
        data = p.to_dict()
        assert data["version"] == 2
        assert "scenes" not in data  # 頂層不再有 scenes
        restored = Project.from_dict(data)
        assert [e.name for e in restored.episodes] == ["第一集", "第二集"]
        assert restored.active_episode_index == 1
        assert restored.episodes[0].scenes[0].id == "A"

    def test_from_dict_migrates_v1_file(self):
        old = {
            "title": "舊專案",
            "scenes": [{"id": "場景1", "dialogues": []}],
            "characters": [],
        }
        p = Project.from_dict(old)
        assert len(p.episodes) == 1
        assert p.episodes[0].name == "影片1"
        assert p.scenes[0].id == "場景1"

    def test_to_script_json_exports_active_episode_only(self):
        e1 = Episode(name="一", scenes=[Scene(id="A", dialogues=[Dialogue(type="narration", text="hi")])])
        e2 = Episode(name="二", scenes=[Scene(id="B", dialogues=[Dialogue(type="narration", text="yo")])])
        p = Project(episodes=[e1, e2])
        assert [s["id"] for s in p.to_script_json()["scenes"]] == ["A"]
        p.active_episode_index = 1
        assert [s["id"] for s in p.to_script_json()["scenes"]] == ["B"]

    def test_next_episode_name(self):
        p = Project()
        assert p.next_episode_name() == "影片2"
        p.episodes.append(Episode(name="自訂名"))
        assert p.next_episode_name() == "影片2"
        p.episodes.append(Episode(name="影片7"))
        assert p.next_episode_name() == "影片8"

