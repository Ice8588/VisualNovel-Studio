"""POC 本地資料模型。簡化版，對應正式版 src/core/models.py 的新結構。"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Dialogue:
    text: str
    type: str = "dialogue"  # "dialogue" | "narration"
    character: str | None = None
    text_effects: list[str] = field(default_factory=list)


@dataclass
class StageSegment:
    start: int
    end: int
    character: str
    costume: str | None = None
    sprite: str | None = None


@dataclass
class EffectSegment:
    start: int
    end: int
    effect_type: str
    params: dict = field(default_factory=dict)


@dataclass
class EffectTrack:
    name: str
    segments: list[EffectSegment] = field(default_factory=list)


@dataclass
class Scene:
    dialogues: list[Dialogue] = field(default_factory=list)
    stage_left: list[StageSegment] = field(default_factory=list)
    stage_center: list[StageSegment] = field(default_factory=list)
    stage_right: list[StageSegment] = field(default_factory=list)
    effect_tracks: list[EffectTrack] = field(default_factory=list)

    def all_stage_lanes(self) -> dict[str, list[StageSegment]]:
        return {"left": self.stage_left, "center": self.stage_center, "right": self.stage_right}

    # --- 跨 domain 同步：插入 / 刪除 / 重排 ---

    def insert_dialogue(self, idx: int, dlg: Dialogue) -> None:
        idx = max(0, min(idx, len(self.dialogues)))
        self.dialogues.insert(idx, dlg)
        self._shift_segments_after_insert(idx)

    def remove_dialogue(self, idx: int) -> None:
        if not (0 <= idx < len(self.dialogues)):
            return
        del self.dialogues[idx]
        self._shift_segments_after_remove(idx)

    def move_dialogue(self, src: int, dst: int) -> None:
        """把 dialogues[src] 搬到位置 dst（dst 為移動後的目標索引）。

        語意：等價於 remove + insert。被搬的對話脫離原本所在的 segment，
        segment 與其他周邊對話綁定（拖曳時的直覺）。
        """
        if src == dst or not (0 <= src < len(self.dialogues)):
            return
        dst = max(0, min(dst, len(self.dialogues) - 1))
        item = self.dialogues.pop(src)
        self._shift_segments_after_remove(src)
        self.dialogues.insert(dst, item)
        self._shift_segments_after_insert(dst)

    # --- 內部 segment index 調整 ---

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

    def _all_segments(self):
        yield from self.stage_left
        yield from self.stage_center
        yield from self.stage_right
        for t in self.effect_tracks:
            yield from t.segments

    def _all_segments_with_owner(self):
        for seg in self.stage_left:
            yield seg, self.stage_left
        for seg in self.stage_center:
            yield seg, self.stage_center
        for seg in self.stage_right:
            yield seg, self.stage_right
        for t in self.effect_tracks:
            for seg in t.segments:
                yield seg, t.segments


def state_at(scene: Scene, dlg_idx: int) -> dict:
    """回傳當前 dlg_idx 下所有 domain 的 active 狀態。engine.js / 匯出會用。"""
    if not (0 <= dlg_idx < len(scene.dialogues)):
        return {}
    dlg = scene.dialogues[dlg_idx]

    def _active_one(lane: list[StageSegment]) -> StageSegment | None:
        for s in lane:
            if s.start <= dlg_idx <= s.end:
                return s
        return None

    return {
        "speaker": dlg.character,
        "text": dlg.text,
        "type": dlg.type,
        "text_effects": list(dlg.text_effects),
        "stage": {
            "left": _active_one(scene.stage_left),
            "center": _active_one(scene.stage_center),
            "right": _active_one(scene.stage_right),
        },
        "effects": [
            s
            for t in scene.effect_tracks
            for s in t.segments
            if s.start <= dlg_idx <= s.end
        ],
    }
