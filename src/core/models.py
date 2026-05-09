"""資料模型：Project, Scene, Dialogue, Character, Costume dataclass，含 JSON 序列化。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SpriteVariant:
    """一個角色的立繪差分（如微笑、生氣等）。"""

    label: str      # 差分名稱，如 "微笑"
    filename: str   # 素材檔名，如 "char_xm_smile.png"

    def to_dict(self) -> dict:
        return {"label": self.label, "filename": self.filename}

    @classmethod
    def from_dict(cls, data: dict) -> SpriteVariant:
        return cls(label=data["label"], filename=data["filename"])


@dataclass
class Costume:
    """一套服裝，包含多個立繪差分。"""

    name: str
    expressions: list[SpriteVariant] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "expressions": [e.to_dict() for e in self.expressions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Costume:
        return cls(
            name=data["name"],
            expressions=[SpriteVariant.from_dict(e) for e in data.get("expressions", [])],
        )


@dataclass
class Character:
    """角色資料：名稱、名牌顏色、服裝列表（每套服裝含多個差分）。

    `position` 為 legacy 欄位：新專案已不使用，由 Dialogue.stage 取代，
    但 from_dict 仍接受以相容舊檔；to_dict 不再寫出 position。
    """

    name: str
    name_color: str = "#4682B4"
    position: str = "center"  # legacy：新檔不寫出（stage 取代）
    costumes: list[Costume] = field(default_factory=list)

    @property
    def sprites(self) -> list[SpriteVariant]:
        """向下相容：回傳所有服裝的差分展平列表。"""
        return [e for c in self.costumes for e in c.expressions]

    def to_dict(self) -> dict:
        # position 為 legacy 欄位，不再寫入新專案檔；舊檔透過 from_dict 相容
        return {
            "name": self.name,
            "name_color": self.name_color,
            "costumes": [c.to_dict() for c in self.costumes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Character:
        if "costumes" in data:
            costumes = [Costume.from_dict(c) for c in data["costumes"]]
        else:
            # 自動遷移舊格式（flat sprites）→ 包進單一預設服裝
            old_sprites = [SpriteVariant.from_dict(s) for s in data.get("sprites", [])]
            costumes = [Costume(name="服裝1", expressions=old_sprites)] if old_sprites else []
        return cls(
            name=data["name"],
            name_color=data.get("name_color", "#4682B4"),
            position=data.get("position", "center"),
            costumes=costumes,
        )


@dataclass
class Dialogue:
    """一條對話或旁白。

    Phase 1 瘦身：sprite / costume / stage 已移至 Scene 層級的 StageSegment；
    effects 改名 text_effects 以與畫面特效 EffectSegment 區分。
    """

    type: str  # "dialogue" 或 "narration"
    text: str
    character: str | None = None
    text_effects: list[str] = field(default_factory=list)  # per-row 文字樣式，如 ["bold", "italic"]

    def to_dict(self) -> dict:
        d: dict = {
            "type": self.type,
            "text": self.text,
            "character": self.character,
        }
        if self.text_effects:
            d["text_effects"] = self.text_effects
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Dialogue:
        return cls(
            type=data["type"],
            text=data["text"],
            character=data.get("character"),
            text_effects=data.get("text_effects", []),
        )


@dataclass
class StageSegment:
    """舞台立繪區間：在 dialogue 索引 [start, end] 範圍內，此槽位顯示指定角色的立繪。"""

    start: int  # dialogue index inclusive
    end: int    # dialogue index inclusive
    character: str  # 必填（沒角色即無意義）
    costume: str | None = None
    sprite: str | None = None  # 差分（表情）

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "character": self.character,
            "costume": self.costume,
            "sprite": self.sprite,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StageSegment:
        return cls(
            start=int(data["start"]),
            end=int(data["end"]),
            character=data["character"],
            costume=data.get("costume"),
            sprite=data.get("sprite"),
        )


@dataclass
class EffectSegment:
    """畫面特效區間：在 [start, end] 範圍內觸發 effect_type。"""

    start: int
    end: int
    effect_type: str  # rain / snow / crt / screen_shake / pixel_dark / 自訂
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {
            "start": self.start,
            "end": self.end,
            "effect_type": self.effect_type,
        }
        if self.params:
            d["params"] = self.params
        return d

    @classmethod
    def from_dict(cls, data: dict) -> EffectSegment:
        return cls(
            start=int(data["start"]),
            end=int(data["end"]),
            effect_type=data["effect_type"],
            params=data.get("params", {}),
        )


@dataclass
class EffectTrack:
    """命名特效軌道，內含多個 EffectSegment（同軌內目前以互斥為前提；多特效並存請開多條軌道）。

    Phase 4.2：可選 `color`（hex 字串，如 `"#FF6600"`）覆寫時間軸顯示色；None → 走 `effect_type` 預設色。
    """

    name: str
    segments: list[EffectSegment] = field(default_factory=list)
    color: str | None = None  # Phase 4.2：使用者覆寫時間軸顯示色；None 走 effect_type 預設

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "segments": [s.to_dict() for s in self.segments],
        }
        if self.color:
            d["color"] = self.color
        return d

    @classmethod
    def from_dict(cls, data: dict) -> EffectTrack:
        return cls(
            name=data["name"],
            color=data.get("color"),
            segments=[EffectSegment.from_dict(s) for s in data.get("segments", [])],
        )


@dataclass
class Scene:
    """一個場景，包含背景、音樂、對話列表，以及舞台與特效的 range-based segments。"""

    id: str
    background: str | None = None
    bgm: str | None = None
    dialogues: list[Dialogue] = field(default_factory=list)
    stage_left: list[StageSegment] = field(default_factory=list)
    stage_center: list[StageSegment] = field(default_factory=list)
    stage_right: list[StageSegment] = field(default_factory=list)
    effect_tracks: list[EffectTrack] = field(default_factory=list)

    # ── 跨 domain 同步 API ──

    def all_stage_lanes(self) -> dict[str, list[StageSegment]]:
        """回傳三條舞台 lane 的 dict（live references）。UI 層用來統一枚舉。"""
        return {
            "left": self.stage_left,
            "center": self.stage_center,
            "right": self.stage_right,
        }

    def insert_dialogue(self, index: int, dlg: Dialogue) -> None:
        """在 index 位置插入新對話；start/end >= index 的 segment 端點自動 +1。"""
        index = max(0, min(index, len(self.dialogues)))
        self.dialogues.insert(index, dlg)
        self._shift_segments_after_insert(index)

    def remove_dialogue(self, index: int) -> None:
        """移除第 index 個對話；端點跨越此列的 segment 縮短，長度歸零者被刪除。"""
        if not (0 <= index < len(self.dialogues)):
            return
        del self.dialogues[index]
        self._shift_segments_after_remove(index)

    def move_dialogue(self, src: int, dst: int) -> None:
        """把 dialogues[src] 搬到位置 dst（移動後的目標索引）。

        語意等價於 remove + insert：被搬的對話脫離原本所在的 segment，
        segments 與其他周邊對話綁定（符合拖曳直覺，POC 已驗證）。
        """
        if src == dst or not (0 <= src < len(self.dialogues)):
            return
        dst = max(0, min(dst, len(self.dialogues) - 1))
        item = self.dialogues.pop(src)
        self._shift_segments_after_remove(src)
        self.dialogues.insert(dst, item)
        self._shift_segments_after_insert(dst)

    # ── 內部 segment 端點調整 ──

    def _all_segments_with_owner(self):
        for seg in self.stage_left:
            yield seg, self.stage_left
        for seg in self.stage_center:
            yield seg, self.stage_center
        for seg in self.stage_right:
            yield seg, self.stage_right
        for track in self.effect_tracks:
            for seg in track.segments:
                yield seg, track.segments

    def _all_segments(self):
        for seg, _ in self._all_segments_with_owner():
            yield seg

    def _shift_segments_after_insert(self, idx: int) -> None:
        for seg in self._all_segments():
            if seg.start >= idx:
                seg.start += 1
            if seg.end >= idx:
                seg.end += 1

    def _shift_segments_after_remove(self, idx: int) -> None:
        to_delete: list = []
        for seg, owner in self._all_segments_with_owner():
            if seg.start == seg.end == idx:
                to_delete.append((seg, owner))
                continue
            if seg.start > idx:
                seg.start -= 1
            if seg.end >= idx:
                seg.end -= 1
            if seg.end < seg.start:
                to_delete.append((seg, owner))
        for seg, owner in to_delete:
            if seg in owner:
                owner.remove(seg)

    # ── 序列化 ──

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "background": self.background,
            "bgm": self.bgm,
            "dialogues": [d.to_dict() for d in self.dialogues],
            "stage_left": [s.to_dict() for s in self.stage_left],
            "stage_center": [s.to_dict() for s in self.stage_center],
            "stage_right": [s.to_dict() for s in self.stage_right],
            "effect_tracks": [t.to_dict() for t in self.effect_tracks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Scene:
        return cls(
            id=data["id"],
            background=data.get("background"),
            bgm=data.get("bgm"),
            dialogues=[Dialogue.from_dict(d) for d in data.get("dialogues", [])],
            stage_left=[StageSegment.from_dict(s) for s in data.get("stage_left", [])],
            stage_center=[StageSegment.from_dict(s) for s in data.get("stage_center", [])],
            stage_right=[StageSegment.from_dict(s) for s in data.get("stage_right", [])],
            effect_tracks=[EffectTrack.from_dict(t) for t in data.get("effect_tracks", [])],
        )


@dataclass
class GameSettings:
    """遊戲畫面顯示設定（影響預覽與影片導出）。"""

    dialogue_font_size: int = 18
    name_font_size: int = 16
    dialogue_box_opacity: float = 0.85
    dialogue_box_color: str = "#141428"  # 對話框底色（hex），與 opacity 合成 rgba
    dialogue_text_color: str = "#EEEEEE"  # 對話文字顏色

    def to_dict(self) -> dict:
        return {
            "dialogue_font_size": self.dialogue_font_size,
            "name_font_size": self.name_font_size,
            "dialogue_box_opacity": self.dialogue_box_opacity,
            "dialogue_box_color": self.dialogue_box_color,
            "dialogue_text_color": self.dialogue_text_color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GameSettings:
        # 字體大小夾至 [14, 28]；不合法舊檔自動修正
        dlg = max(14, min(28, int(data.get("dialogue_font_size", 18))))
        name = max(14, min(28, int(data.get("name_font_size", 16))))
        return cls(
            dialogue_font_size=dlg,
            name_font_size=name,
            dialogue_box_opacity=float(data.get("dialogue_box_opacity", 0.85)),
            dialogue_box_color=str(data.get("dialogue_box_color", "#141428")),
            dialogue_text_color=str(data.get("dialogue_text_color", "#EEEEEE")),
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
        """供 engine.js 消化的格式：每個 dialogue 的 stage / active_effects 已預計算。

        Phase 3：engine.js 不再自行實作 stateAt，改讀 Python 端 `state_at` 攤平後的結果。
        """
        from src.core.scene_state import state_at  # lazy import 規避循環

        def _seg_to_dict(seg):
            return None if seg is None else {
                "character": seg.character,
                "costume": seg.costume,
                "sprite": seg.sprite,
            }

        scenes_out = []
        for scene in self.scenes:
            dialogues_out = []
            for idx, dlg in enumerate(scene.dialogues):
                st = state_at(scene, idx)
                dialogues_out.append({
                    "type": dlg.type,
                    "text": dlg.text,
                    "character": dlg.character,
                    "text_effects": list(dlg.text_effects),
                    "stage": {
                        "left":   _seg_to_dict(st["stage"]["left"]),
                        "center": _seg_to_dict(st["stage"]["center"]),
                        "right":  _seg_to_dict(st["stage"]["right"]),
                    },
                    "active_effects": [
                        {"effect_type": e.effect_type, "params": dict(e.params)}
                        for e in st["effects"]
                    ],
                })
            scenes_out.append({
                "id": scene.id,
                "background": scene.background,
                "bgm": scene.bgm,
                "dialogues": dialogues_out,
            })

        return {
            "title": self.title,
            "scenes": scenes_out,
            "characters": {
                c.name: {
                    "name_color": c.name_color,
                    "position": c.position,
                    "sprites": {e.label: e.filename
                                for cos in c.costumes for e in cos.expressions},
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
        """產生下一個場景名稱，如 '場景1'、'場景2'。"""
        if not self.scenes:
            return "場景1"
        max_num = 0
        for scene in self.scenes:
            # 支援「場景N」格式
            if scene.id.startswith("場景") and scene.id[2:].isdigit():
                max_num = max(max_num, int(scene.id[2:]))
            # 相容舊格式 scene_NNN
            else:
                parts = scene.id.split("_")
                if len(parts) == 2 and parts[1].isdigit():
                    max_num = max(max_num, int(parts[1]))
        return f"場景{max_num + 1}"
