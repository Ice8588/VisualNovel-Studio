"""資料模型：Project, Scene, Dialogue, Character dataclass，含 JSON 序列化。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SpriteVariant:
    """一個角色的表情差分（如微笑、生氣等）。"""

    label: str      # 表情名稱，如 "微笑"
    filename: str   # 素材檔名，如 "char_xm_smile.png"

    def to_dict(self) -> dict:
        return {"label": self.label, "filename": self.filename}

    @classmethod
    def from_dict(cls, data: dict) -> SpriteVariant:
        return cls(label=data["label"], filename=data["filename"])


@dataclass
class Character:
    """角色資料：名稱、名牌顏色、螢幕位置、表情差分列表。"""

    name: str
    name_color: str = "#4682B4"
    position: str = "center"  # "left" / "center" / "right"
    sprites: list[SpriteVariant] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "name_color": self.name_color,
            "position": self.position,
            "sprites": [s.to_dict() for s in self.sprites],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Character:
        return cls(
            name=data["name"],
            name_color=data.get("name_color", "#4682B4"),
            position=data.get("position", "center"),
            sprites=[SpriteVariant.from_dict(s) for s in data.get("sprites", [])],
        )


@dataclass
class Dialogue:
    """一條對話或旁白。"""

    type: str  # "dialogue" 或 "narration"
    text: str
    character: str | None = None
    sprite: str | None = None  # 表情標籤（對應 SpriteVariant.label），fallback 當檔名
    effects: list[str] = field(default_factory=list)  # 文字效果，如 ["bold", "italic"]

    def to_dict(self) -> dict:
        d: dict = {
            "type": self.type,
            "text": self.text,
            "character": self.character,
            "sprite": self.sprite,
        }
        if self.effects:
            d["effects"] = self.effects
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Dialogue:
        return cls(
            type=data["type"],
            text=data["text"],
            character=data.get("character"),
            sprite=data.get("sprite"),
            effects=data.get("effects", []),
        )


@dataclass
class Scene:
    """一個場景，包含背景、音樂、特效和對話列表。"""

    id: str
    background: str | None = None
    bgm: str | None = None
    effect: str | None = None  # "rain" / "snow" / "crt" / "pixel_dark" / None
    dialogues: list[Dialogue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "background": self.background,
            "bgm": self.bgm,
            "effect": self.effect,
            "dialogues": [d.to_dict() for d in self.dialogues],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Scene:
        return cls(
            id=data["id"],
            background=data.get("background"),
            bgm=data.get("bgm"),
            effect=data.get("effect"),
            dialogues=[Dialogue.from_dict(d) for d in data.get("dialogues", [])],
        )


@dataclass
class GameSettings:
    """遊戲畫面顯示設定（影響預覽與影片導出）。"""

    dialogue_font_size: int = 18
    name_font_size: int = 16
    dialogue_box_opacity: float = 0.85

    def to_dict(self) -> dict:
        return {
            "dialogue_font_size": self.dialogue_font_size,
            "name_font_size": self.name_font_size,
            "dialogue_box_opacity": self.dialogue_box_opacity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GameSettings:
        return cls(
            dialogue_font_size=int(data.get("dialogue_font_size", 18)),
            name_font_size=int(data.get("name_font_size", 16)),
            dialogue_box_opacity=float(data.get("dialogue_box_opacity", 0.85)),
        )


@dataclass
class Project:
    """專案根物件，包含標題、場景列表和素材清單。"""

    title: str = "Untitled"
    scenes: list[Scene] = field(default_factory=list)
    characters: list[Character] = field(default_factory=list)
    assets: dict[str, list[str]] = field(
        default_factory=lambda: {
            "backgrounds": [],
            "sprites": [],
            "music": [],
        }
    )
    project_path: Path | None = None
    game_settings: GameSettings = field(default_factory=GameSettings)

    def to_script_json(self) -> dict:
        """轉換為 engine.js 使用的 script.json 格式。"""
        return {
            "title": self.title,
            "scenes": [s.to_dict() for s in self.scenes],
            "characters": {
                c.name: {
                    "name_color": c.name_color,
                    "position": c.position,
                    "sprites": {s.label: s.filename for s in c.sprites},
                }
                for c in self.characters
            },
            "game_settings": self.game_settings.to_dict(),
        }

    def to_dict(self) -> dict:
        """完整序列化（含素材路徑），用於 .vnsproj 儲存。"""
        return {
            "title": self.title,
            "scenes": [s.to_dict() for s in self.scenes],
            "characters": [c.to_dict() for c in self.characters],
            "assets": self.assets,
            "project_path": str(self.project_path) if self.project_path else None,
            "game_settings": self.game_settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        default_assets = {"backgrounds": [], "sprites": [], "music": []}
        assets = data.get("assets", default_assets)
        # 確保所有分類都存在
        for key in default_assets:
            if key not in assets:
                assets[key] = []

        path_str = data.get("project_path")
        gs_data = data.get("game_settings", {})
        return cls(
            title=data.get("title", "Untitled"),
            scenes=[Scene.from_dict(s) for s in data.get("scenes", [])],
            characters=[Character.from_dict(c) for c in data.get("characters", [])],
            assets=assets,
            project_path=Path(path_str) if path_str else None,
            game_settings=GameSettings.from_dict(gs_data),
        )

    def next_scene_id(self) -> str:
        """產生下一個場景 ID，如 'scene_001'、'scene_002'。"""
        if not self.scenes:
            return "scene_001"
        max_num = 0
        for scene in self.scenes:
            # 從 scene_XXX 格式中提取數字
            parts = scene.id.split("_")
            if len(parts) == 2 and parts[1].isdigit():
                max_num = max(max_num, int(parts[1]))
        return f"scene_{max_num + 1:03d}"
