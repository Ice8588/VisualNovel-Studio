"""POC 用假資料：20 列對話 + 預設 stage/effect segments。"""

from .models import Dialogue, EffectSegment, EffectTrack, Scene, StageSegment


def build_mock_scene() -> Scene:
    dialogues = [
        Dialogue("「嗨，你來了。」", "dialogue", "小明", []),
        Dialogue("「今天怎麼這麼晚？」", "dialogue", "小明", []),
        Dialogue("「抱歉，公車誤點了。」", "dialogue", "小華", ["italic"]),
        Dialogue("（兩人在咖啡廳門口相視而笑。）", "narration", None, []),
        Dialogue("「我點杯拿鐵，你要什麼？」", "dialogue", "小華", []),
        Dialogue("「一樣就好，謝謝。」", "dialogue", "小明", []),
        Dialogue("（外頭開始下起小雨。）", "narration", None, []),
        Dialogue("「欸，下雨了。」", "dialogue", "小華", ["bold"]),
        Dialogue("「還好我們在裡面。」", "dialogue", "小明", []),
        Dialogue("「歡迎光臨！」", "dialogue", "店員", []),
        Dialogue("「兩杯拿鐵，謝謝。」", "dialogue", "小華", []),
        Dialogue("（店員點點頭，轉身準備。）", "narration", None, []),
        Dialogue("「最近工作怎麼樣？」", "dialogue", "小明", []),
        Dialogue("「別提了，一團亂。」", "dialogue", "小華", ["shake"]),
        Dialogue("「怎麼了？」", "dialogue", "小明", []),
        Dialogue("「老闆一直改規格。」", "dialogue", "小華", []),
        Dialogue("（他嘆了一口氣。）", "narration", None, []),
        Dialogue("「忍耐一下吧。」", "dialogue", "小明", []),
        Dialogue("「你的拿鐵好了！」", "dialogue", "店員", []),
        Dialogue("「謝謝。」", "dialogue", "小華", []),
    ]

    scene = Scene(
        dialogues=dialogues,
        stage_left=[
            StageSegment(0, 8, "小明", "便服", "微笑"),
            StageSegment(12, 17, "小明", "便服", "微笑"),
        ],
        stage_center=[
            StageSegment(9, 11, "店員", "制服", "微笑"),
            StageSegment(18, 18, "店員", "制服", "微笑"),
        ],
        stage_right=[
            StageSegment(2, 8, "小華", "便服", "微笑"),
            StageSegment(10, 17, "小華", "便服", "疲憊"),
            StageSegment(19, 19, "小華", "便服", "微笑"),
        ],
        effect_tracks=[
            EffectTrack(
                "環境",
                [EffectSegment(6, 19, "rain", {"intensity": 0.3})],
            ),
            EffectTrack(
                "畫面",
                [
                    EffectSegment(13, 13, "shake-screen", {}),
                    EffectSegment(16, 17, "crt", {}),
                ],
            ),
        ],
    )
    return scene
