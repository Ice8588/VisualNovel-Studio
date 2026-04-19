"""產生 Phase 3 MP4 端到端驗收用的 fixture 專案。

跑一次：
    python scripts/build_phase3_mp4_fixture.py

輸出位置：experimental/phase3_mp4_verify/
  ├─ proj.vnsproj
  ├─ assets/
  │   ├─ bg_room.png         (1280×720 暖色房間背景)
  │   ├─ char_a.png          (300×600 紅色角色 A，左槽)
  │   ├─ char_b.png          (300×600 藍色角色 B，右槽)
  └─ README.md               (驗收步驟)

驗收流程：
  1. python main.py
  2. File → Open → 選 experimental/phase3_mp4_verify/proj.vnsproj
  3. 確認預覽：A 在左、B 在右、雨效全程、第 3 句畫面震動
  4. Export → MP4
  5. 用播放器播 MP4，逐項目視確認
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 允許從 repo root 執行
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from src.core.models import (  # noqa: E402
    Character,
    Costume,
    Dialogue,
    EffectSegment,
    EffectTrack,
    Project,
    Scene,
    SpriteVariant,
    StageSegment,
)


OUT_DIR = ROOT / "experimental" / "phase3_mp4_verify"
ASSETS_DIR = OUT_DIR / "assets"


def _font(size: int):
    """中文字體 fallback 鏈（與專案 _load_font 邏輯一致）。"""
    candidates = [
        "msjh.ttc", "msyh.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "DejaVuSans-Bold.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def make_background(path: Path) -> None:
    """1280×720 暖色房間漸層背景 + 簡單地板線。"""
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (60, 50, 80))
    draw = ImageDraw.Draw(img)

    # 上半牆面漸層
    for y in range(0, H * 2 // 3):
        t = y / (H * 2 // 3)
        r = int(80 + (140 - 80) * t)
        g = int(60 + (110 - 60) * t)
        b = int(100 + (140 - 100) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 下半地板較深
    for y in range(H * 2 // 3, H):
        t = (y - H * 2 // 3) / (H // 3)
        r = int(50 + (30 - 50) * t)
        g = int(40 + (25 - 40) * t)
        b = int(60 + (35 - 60) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 標題
    f = _font(32)
    draw.text((W // 2 - 200, 30), "Phase 3 MP4 驗收場景", font=f, fill=(240, 230, 210))

    img.save(path)


def make_sprite(path: Path, label: str, color: tuple[int, int, int]) -> None:
    """300×600 帶透明背景的角色立繪：色塊 + 字母標記。"""
    W, H = 300, 600
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 主體色塊（橢圓 + 矩形身體）
    head_box = (60, 60, 240, 240)  # 頭
    body_box = (40, 240, 260, 580)  # 身
    draw.ellipse(head_box, fill=color + (240,))
    draw.rounded_rectangle(body_box, radius=30, fill=color + (220,))

    # 字母標記在頭部正中
    f = _font(120)
    bbox = draw.textbbox((0, 0), label, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx = (head_box[0] + head_box[2]) // 2
    cy = (head_box[1] + head_box[3]) // 2
    draw.text((cx - tw // 2, cy - th // 2 - 10), label,
              font=f, fill=(255, 255, 255, 255))

    img.save(path)


def build_project() -> Project:
    """組 5 句對話、A 在左 / B 在右全程、rain 全程、第 3 句 screen_shake 的 Project。"""
    proj = Project(title="Phase3 MP4 Verify", project_path=OUT_DIR / "proj.vnsproj")

    # 兩個角色，各一套 costume + 一個 sprite label
    proj.characters = [
        Character(
            name="A", name_color="#E04C4C",
            costumes=[Costume(name="default",
                              expressions=[SpriteVariant(label="n", filename="char_a.png")])],
        ),
        Character(
            name="B", name_color="#4C8AE0",
            costumes=[Costume(name="default",
                              expressions=[SpriteVariant(label="n", filename="char_b.png")])],
        ),
    ]
    proj.assets = {
        "backgrounds": ["bg_room.png"],
        "sprites": ["char_a.png", "char_b.png"],
        "music": [],
    }

    # 5 句對話
    scene = Scene(
        id="場景1",
        background="bg_room.png",
        bgm=None,
        dialogues=[
            Dialogue(type="dialogue", text="A：嗨，我們在左邊。", character="A"),
            Dialogue(type="dialogue", text="B：我在右邊，雨從第 1 句下到結束。", character="B"),
            Dialogue(type="dialogue", text="A：第 3 句畫面會震動！", character="A",
                     text_effects=["bold", "shake"]),
            Dialogue(type="narration", text="（雨繼續下、震動結束。）"),
            Dialogue(type="dialogue", text="B：兩個立繪、雨效、文字效果都通過。", character="B"),
        ],
    )

    # 舞台：A 全程在左、B 全程在右
    scene.stage_left.append(StageSegment(0, 4, "A", costume="default", sprite="n"))
    scene.stage_right.append(StageSegment(0, 4, "B", costume="default", sprite="n"))

    # 特效軌道
    scene.effect_tracks.append(EffectTrack(
        name="env", segments=[EffectSegment(0, 4, "rain", params={"intensity": 0.5})],
    ))
    scene.effect_tracks.append(EffectTrack(
        name="cam", segments=[EffectSegment(2, 2, "screen_shake")],
    ))

    proj.scenes.append(scene)
    return proj


def write_readme() -> None:
    readme = """# Phase 3 MP4 端到端驗收 fixture

## 內容
- `proj.vnsproj`：5 句對話的範例專案
- `assets/bg_room.png`：背景
- `assets/char_a.png`：紅色角色 A 立繪（左槽）
- `assets/char_b.png`：藍色角色 B 立繪（右槽）

## 預期效果

| 對話 | 內容 | 視覺要素 |
|---|---|---|
| ① | A：嗨，我們在左邊。 | A 在左 + B 在右 + rain |
| ② | B：我在右邊… | 同上 |
| ③ | A：第 3 句畫面會震動！ | 同上 + **screen_shake** + 文字 bold + shake |
| ④ | （雨繼續下、震動結束。）旁白 | A + B + rain（無震動） |
| ⑤ | B：兩個立繪、雨效… | 同上 |

## 驗收流程

```bash
# 1) 切到 Phase 3 分支
git checkout feature/phase-3-engine-mp4

# 2) 開 app
python main.py

# 3) File → Open
#    路徑：experimental/phase3_mp4_verify/proj.vnsproj

# 4) Preview 區域目視確認
#    - A 立繪（紅）在畫面左側
#    - B 立繪（藍）在畫面右側
#    - 雨點全程下落
#    - 點對話 ③ 時畫面震動

# 5) File → Export → MP4
#    輸出檔名隨意（例如 ~/phase3_verify.mp4）

# 6) 用播放器（VLC / mpv / Windows Media Player）播 MP4
#    逐項目視確認上表「視覺要素」全部出現
```

## 通過標準（用以解封 main merge）

- [ ] A 在 MP4 左半邊每一幀都出現（而非只在 A 說話時）
- [ ] B 在 MP4 右半邊每一幀都出現
- [ ] 雨效從第 1 秒到結尾都在
- [ ] 第 3 句對話那段畫面有左右震動
- [ ] 文字框無裁切、字體大小正常
- [ ] 對話順序 ①→②→③→④→⑤ 與專案一致
- [ ] 最後黑屏 / fade out 收尾正常

任一項不通過 → 回報症狀；通過 → 即可 merge phase-1 + phase-2 + phase-3 → main。

## 重新生成此 fixture

```bash
python scripts/build_phase3_mp4_fixture.py
```
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"→ 建立背景：{ASSETS_DIR / 'bg_room.png'}")
    make_background(ASSETS_DIR / "bg_room.png")

    print(f"→ 建立 A 立繪：{ASSETS_DIR / 'char_a.png'}")
    make_sprite(ASSETS_DIR / "char_a.png", "A", (224, 76, 76))

    print(f"→ 建立 B 立繪：{ASSETS_DIR / 'char_b.png'}")
    make_sprite(ASSETS_DIR / "char_b.png", "B", (76, 138, 224))

    print(f"→ 建立 .vnsproj：{OUT_DIR / 'proj.vnsproj'}")
    project = build_project()
    (OUT_DIR / "proj.vnsproj").write_text(
        json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"→ 建立 README：{OUT_DIR / 'README.md'}")
    write_readme()

    print()
    print(f"✓ Fixture 已建立於 {OUT_DIR}")
    print("  下一步：python main.py，開 proj.vnsproj，匯出 MP4 驗收。")


if __name__ == "__main__":
    main()
