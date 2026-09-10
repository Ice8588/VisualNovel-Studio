"""Phase 1：在某個 dialogue index 把所有跨欄位狀態組合起來。

`state_at(scene, dlg_idx)` 是 engine.js 與 MP4 匯出的單一查詢入口；
Phase 3 的 JS `stateAt` 必須與此函式 key/結構字面一致（守護測試會比對）。
"""

from __future__ import annotations

from src.core.models import Scene, StageSegment


def _active(lane: list[StageSegment], dlg_idx: int) -> StageSegment | None:
    """回傳 lane 內覆蓋此 dlg_idx 的 segment（lane 為互斥，至多一個）。"""
    for s in lane:
        if s.start <= dlg_idx <= s.end:
            return s
    return None


def state_at(scene: Scene, dlg_idx: int) -> dict:
    """整合當前 dialogue idx 的所有狀態：說話者、文字效果、三槽舞台、active 特效。

    超出範圍 → 回空 dict（呼叫端可判斷 `if not state`）。
    """
    if not (0 <= dlg_idx < len(scene.dialogues)):
        return {}
    dlg = scene.dialogues[dlg_idx]
    return {
        "speaker": dlg.character,
        "text": dlg.text,
        "type": dlg.type,
        "text_effects": list(dlg.text_effects),
        "stage": {
            "left": _active(scene.stage_left, dlg_idx),
            "center": _active(scene.stage_center, dlg_idx),
            "right": _active(scene.stage_right, dlg_idx),
        },
        "effects": [
            s
            for t in scene.effect_tracks
            for s in t.segments
            if s.start <= dlg_idx <= s.end
        ],
    }
