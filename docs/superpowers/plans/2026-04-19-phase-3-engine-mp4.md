# Phase 3 — engine.js / MP4 export 適配（★ Merge to main 閘門）

> **給驗證 AI（codex）：** 本文件為 Phase 3 的完整 spec，可獨立讀懂。
> 上游：`feature/phase-2-ui` (commit `5c4f9e9`)。
> 本 Phase 分支：`feature/phase-3-engine-mp4`，從 `feature/phase-2-ui` branch off。
> **★ 完成後 main 解封**：phase-1+2+3 一起 merge to main。
> **MP4 是核心優先級**（CLAUDE.md），必須端到端實跑驗證才能 merge——pytest 全綠不夠。

---

## Goal（一句話）

讓 `src/engine/engine.js` / `src/core/exporter_video.py` / `src/core/exporter_html.py` / `src/ui/webengine_capture.py` 都能消化 Phase 1 的新資料模型（`StageSegment` / `EffectSegment` / `EffectTrack`），並 ADR-003 守護 CAPTURE_MODE 下多立繪渲染。

## 上下文（執行前必讀）

**Phase 1 改了**：`Dialogue` 瘦身只剩 `text/type/character/text_effects`；`Scene` 加 `stage_left/center/right: list[StageSegment]` + `effect_tracks: list[EffectTrack]`；移除 `Scene.effect`。新模組 `src/core/scene_state.py::state_at(scene, dlg_idx)` 回傳 `{speaker, text, type, text_effects, stage:{left,center,right}, effects:[...]}`。

**Phase 2 改了**：UI 完全重建為三域分離（卡片列 + 舞台三 lane + 特效 timeline）；`exporter_video.py::sprite_path = None` 是 Phase 1 留的 stub；`webengine_capture.py::has_effect = any(t.segments for t in scene.effect_tracks)` 已 Phase 2 補正。

**Phase 3 要修**：engine.js 仍讀 `d.sprite` / `d.effects` / `d.stage` / `scene.effect`（這些欄位都已不存在或改名）→ MP4 完全壞。Phase 3 把 engine 與 export pipeline 接上新模型，讓預覽 / ZIP / HTML / MP4 都能 work。

---

## 關鍵設計決定：Python 端預先計算 state（取代 JS stateAt 重寫）

**原方案**（草稿）：engine.js 內實作 `stateAt(scene, dlgIdx)` 並用 parity test 守護兩端對齊。

**改採方案**：在 `Project.to_script_json` 內呼叫 Python `state_at` 預先攤平每個 dialogue 的舞台/特效狀態，輸出到 `data.js` 的每筆 dialogue 物件。engine.js **只讀已 resolved 的欄位**，邏輯維持簡單。

**理由**：
1. 單一 source of truth（Python `state_at`）；engine.js 不再需要重新實作排序/區間搜尋
2. 不需要 JS↔Python parity test（一份 code）
3. data.js 略大（~10-20%）但語義清晰，debug 容易
4. engine.js diff 最小化（renamed fields + 移除 legacy `resolveSpriteFile`）

**輸出 shape**（`Project.to_script_json` 後）：

```json
{
  "scenes": [{
    "id": "...", "background": "...", "bgm": "...",
    "dialogues": [{
      "type": "dialogue", "text": "...", "character": "小明",
      "text_effects": ["bold"],
      "stage": {                                         // ★ 預計算
        "left":   {"character":"小明","costume":"便服","sprite":"微笑"},
        "center": null,
        "right":  null
      },
      "active_effects": [                                // ★ 預計算
        {"effect_type":"rain","params":{}}
      ]
    }]
  }],
  "characters": { ... },
  "game_settings": { ... }
}
```

`stage` 與 `active_effects` 由 `state_at(scene, idx)` 提取後寫入；engine.js 只是 `d.stage.left.character` 之類的簡單讀取。

---

## 不在 Phase 3 範圍（明確排除）

| 項目 | 為何排除 | Phase |
|---|---|---|
| 真正的 JS `stateAt(scene, idx)` 函式 | Python 端預計算後，引擎不需要 | — |
| 完整的 `screen_shake` 動畫實作 | 樣式可加，但完整 effect kind 編輯器是 Phase 4 | 4 |
| 多 effect_track 同時 active 的疊加渲染（非 z-index 互斥） | 設計細節留 Phase 4 | 4 |
| 自訂 effect kinds（使用者 free-form key） | UI 端 Phase 4 處理 | 4 |
| Undo / Redo | 後續 | — |
| `tests/01.vnsproj` 老格式 fixture migration | 無使用者，丟棄 | — |

---

## 假設（Assumptions — 請 codex 確認；user 可推翻）

1. **Python 端 pre-compute**：`Project.to_script_json` 呼叫 `state_at` 把每筆 dialogue 的 `stage` 與 `active_effects` 攤平。engine.js **不**實作 stateAt JS 版。
2. **v1 Pillow exporter（exporter_video.py）只渲染單張立繪**（speaker 的 stage segment 若有；否則 center > left > right 順序 fallback）。多立繪只在 v2 (webengine_capture) 保證——符合 ADR-003 規定的「主路徑 = QtWebEngine」。
3. **`screen_shake` 與 `pixel_dark` 等新 effect_type**：Phase 3 加 CSS 規則（即使空殼），engine.js 用對應 class 名套；實際動畫 Phase 4 再進階。Phase 3 至少 `rain` / `snow` / `crt` 沿用既有實作；新加的 fallback 顯示 chip 即可。
4. **`exporter_html.py` 若有 sprite 讀取殘餘**（survey 提到 lines 170-173），Phase 3 一併修。
5. **無破壞 preview signal**：`PreviewBridge.dialogue_advanced` / `stage_slot_clicked` API shape 不動。
6. **舊 `Character.position` legacy 欄位**：to_script_json 仍輸出（engine.js 部分 fallback 仍需）；Phase 3 不清這個。
7. **CAPTURE_MODE 抑制清單不擴大**：保留現有「skip typewriter / 背景轉場 / BGM / overlay」；新增的舞台 segment 渲染**不**抑制。

---

## 前置狀態檢查

- [ ] **0.1** 在 Phase 2 完成的分支上

```bash
git checkout feature/phase-2-ui
git log --oneline -1   # Expected: 5c4f9e9 phase 2: UI 重建 ...
git status             # Expected: working tree clean
```

- [ ] **0.2** Phase 2 測試全綠

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

Expected: 全綠（≈184 passed）。

- [ ] **0.3** 開 Phase 3 分支

```bash
git checkout -b feature/phase-3-engine-mp4
```

---

## Step 1 — `Project.to_script_json` 預計算 state

**檔案**：[src/core/models.py](src/core/models.py)

- [ ] **1.1** 改寫 `Project.to_script_json` 為以下實作（注意 `state_at` 改用 method 內 lazy import 規避循環）：

```python
def to_script_json(self) -> dict:
    """供 engine.js 消化的格式：每個 dialogue 的 stage / active_effects 已預計算。"""
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
            } for c in self.characters
        },
        "game_settings": self.game_settings.to_dict(),
    }
```

- [ ] **1.2** 新增 `tests/test_to_script_json_phase3.py`：
  - 用一個含 `stage_left` segment + 一條 `effect_tracks` 的 mock scene
  - `to_script_json()` 後斷言每個 dialogue 都有 `stage`（含 left/center/right keys，含 None 槽）與 `active_effects`（list）
  - 對 segment 範圍內外的 dialogue 分別斷言 active 狀態正確
  - 確認 `text_effects` 維持 list（不被預計算覆蓋）

**Verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_to_script_json_phase3.py -v
```

Expected: 全綠。

---

## Step 2 — `engine.js` 改用 pre-resolved 欄位

**檔案**：[src/engine/engine.js](src/engine/engine.js)

> ⚠️ Phase 3 最大改動。建議拆 2-3 commit：renamed reads → 移除 legacy → effect 接線。

- [ ] **2.1** `applyTextEffects` 改 input：showDialogue 內的 `applyTextEffects(d.effects || [])` 改 `applyTextEffects(d.text_effects || [])`。grep `d.effects` 確認沒漏。

- [ ] **2.2** 立繪渲染：`showDialogue` 內 `d.stage` 永遠存在（Step 1 已預計算）。三槽分別跑 `renderStageSlot('left'/'center'/'right', d.stage[pos])`。slotData=null 時隱藏該槽。**移除** `if (!d.stage) renderLegacySprite(d, charInfo)` 之類 fallback。

- [ ] **2.3** **刪除 legacy 函式**：
  - `resolveSpriteFile(dialogue, charInfo)` (engine.js lines 356-363)
  - `renderLegacySprite(d, charInfo)` (lines 420-439)
  - `setSpritePosition(...)` 若僅被 legacy 用
  - `<img id="sprite">` legacy DOM 元素（[src/engine/index.html](src/engine/index.html)）；若還在則改用三槽 `<img id="sprite-left/center/right">`（若已是這結構則不動）

- [ ] **2.4** **特效改用 active_effects**：
  - 原本 `enterScene()` 呼叫 `VNEffects.setEffect(scene.effect || null)` (line 247-248)
  - 改用：在 `showDialogue(d, ...)` 內呼叫 `VNEffects.setActive(d.active_effects)`，接受 `[{effect_type, params}, ...]`
  - 多 effect 同時 active：依 `effect_type` 套對應 `.fx-{kind}` class 到 `body` 或專用 effect 容器
  - `enterScene` 內移除 `setEffect(scene.effect)`（scene.effect 已不存在）；場景切換時的 effect cleanup 由 `setActive` 自己處理（比對前後差集 start/stop）

- [ ] **2.5** `refreshStageOverlayButtons(d)` (lines 520-540)：原本讀 d.stage 動態顯示按鈕。Phase 3 內 d.stage 仍存在（同 shape，只是 Python 預計算），**邏輯不需動**。

- [ ] **2.6** **CAPTURE_MODE ADR-003 守護**：在 `showDialogue` 內，stage 三槽渲染**不被 CAPTURE_MODE 抑制**。typewriter / 背景轉場 / BGM / overlay 按鈕的 skip 邏輯維持。

**Verification**

```bash
# 不再有舊欄位讀取
grep -n "d\.effects\b\|d\.sprite\b\|scene\.effect\b" src/engine/engine.js
# Expected: 空（d.text_effects、scene.effect_tracks 不算）

# legacy 函式已刪
grep -n "resolveSpriteFile\|renderLegacySprite" src/engine/engine.js
# Expected: 空
```
- [ ] preview 載入既有專案不報 JS console error（手動跑 `python main.py` 驗）

---

## Step 3 — `effects.js` / `style.css` 多特效堆疊規則

**檔案**：[src/engine/effects.js](src/engine/effects.js) [src/engine/style.css](src/engine/style.css)

- [ ] **3.1** `effects.js` 新增 `VNEffects.setActive(activeList)`：
  - 維護當前 active set；新進的 effect_type call 對應的 start handler；移除的 call stop
  - 既有 `setEffect(name)` 改為 thin wrapper：`setActive([{effect_type: name, params: {}}])` 或保留向後相容
  - 已知 effect_type：`rain` / `snow` / `crt` / `pixel_dark` / `screen_shake`（後二為新增）
  - 未知 effect_type：log warning，不崩
- [ ] **3.2** `style.css` 加：
  - `body.fx-screen_shake` → `animation: vn-screen-shake 0.3s infinite` (新 keyframes)
  - `body.fx-pixel_dark` → `filter: brightness(0.6) contrast(0.8)` (簡化版)
  - 多特效堆疊時 z-index：rain/snow > crt overlay > screen_shake (作用於 body 不衝突)
- [ ] **3.3** Capture Mode 動畫抑制檢查：`* { animation: none !important }` 之類規則需確認 `screen_shake` 在 capture 下停動但仍套 brightness 等靜態效果

**Verification**

- [ ] preview 對含 `screen_shake` segment 的 dialogue 不崩
- [ ] CAPTURE_MODE 下不晃動但其他靜態 filter 仍套用

---

## Step 4 — `exporter_video.py` (v1 Pillow) 接 state_at

**檔案**：[src/core/exporter_video.py](src/core/exporter_video.py)

> ⚠️ ADR-003 規定**主路徑是 v2 webengine_capture**。v1 是 fallback，可降級。

- [ ] **4.1** import `state_at`（檔案頂部）
- [ ] **4.2** `_generate_frames` 內：

```python
from src.core.scene_state import state_at  # 在檔案頂部

# 取代 sprite_path = None 那行
for idx, dlg in enumerate(scene.dialogues):
    st = state_at(scene, idx)
    # 取 sprite：speaker 對應的 stage 槽優先 → center > left > right > None
    sprite_seg = None
    if dlg.character:
        for pos in ("left", "center", "right"):
            s = st["stage"][pos]
            if s and s.character == dlg.character:
                sprite_seg = s
                break
    if sprite_seg is None:
        for pos in ("center", "left", "right"):
            if st["stage"][pos]:
                sprite_seg = st["stage"][pos]
                break

    sprite_path = None
    if sprite_seg:
        sprite_filename = self._lookup_sprite_filename(sprite_seg)
        sprite_path = self._resolve_asset(sprite_filename) if sprite_filename else None
    # ... 其餘 render_frame 呼叫照舊
```

- [ ] **4.3** 新 helper `_lookup_sprite_filename(stage_seg)`：從 `self._project.characters` 找對應 character → costumes → expressions 取 filename。fallback None。
- [ ] **4.4** 把 Phase 1 留下的 `sprite_path = None  # Phase 3:` stub 註解清掉

**Verification**

- [ ] 既有 `tests/test_exporter_video.py` 全綠（test 用 mock 路徑直接傳，不影響）
- [ ] 對含 stage segments 的 mock scene 跑 export，斷言 sprite_path 從 state_at 取出

---

## Step 5 — `exporter_html.py` 殘餘 sprite 讀取清理

**檔案**：[src/core/exporter_html.py](src/core/exporter_html.py)

- [ ] **5.1** Survey 指出 lines 170-173 還讀 `dlg.get("sprite")`。確認 + 改為從新 dialogue dict 的 `stage.{left,center,right}.sprite` 提取（若需收集 asset 列表）
- [ ] **5.2** `to_script_json` 預計算後，這個 export 直接消化新格式即可；asset 收集改為遍歷 stage 三槽

**Verification**

```bash
grep -rn "dlg\.get('sprite')\|dialogue\.get('sprite')" src/core/
# Expected: 無遺留
```
- [ ] 既有 `tests/test_exporter_html.py`（若有）綠

---

## Step 6 — ADR-003 多立繪守護測試

**檔案**：[src/ui/webengine_capture.py](src/ui/webengine_capture.py)

- [ ] **6.1** 確認 `has_effect = any(t.segments for t in scene.effect_tracks)` 仍正確（Phase 2 已改），不需動
- [ ] **6.2** **新增 [tests/test_capture_multi_sprite.py](tests/test_capture_multi_sprite.py)**：
  - 建一個 mock Project：1 scene、1 dialogue、stage_left + stage_right 都覆蓋此 dialogue（不同角色）+ assets dir 含兩張 PNG (左 100% red、右 100% blue)
  - 跑 `WebEngineVideoExporter.export(...)` 輸出單幀
  - 用 PIL 讀取輸出 PNG，sample 兩個位置（左 1/4、右 3/4 的 y=middle）
  - 斷言左側區域含 red pixel、右側含 blue pixel
  - 若 QtWebEngine 在 CI 不可用：用 `pytest.mark.skipif` 跳過，但 user 手動實跑驗收

**Verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_capture_multi_sprite.py -v
# Expected: 通過 OR skipif 標明
```

---

## Step 7 — `docs/DEVELOPMENT_HISTORY.md` Phase 3 摘要

- [ ] **7.1** 加 30-50 行 Phase 3 紀錄：
  - to_script_json 預計算策略決定（取代 JS stateAt）
  - engine.js 拔掉的 legacy 函式
  - ADR-003 守護的測試 + MP4 端到端驗收
  - 新 ADR：`Project.to_script_json` 為「engine 消化的 view」，per-dialogue 預計算

**Verification**

`git diff docs/DEVELOPMENT_HISTORY.md` 顯示新增的 Phase 3 區塊。

---

## 完成判定（codex 跑這份檢核）

```bash
# 1) 完整測試
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v

# 2) engine.js 不再讀舊欄位
grep -n 'd\.effects\b\|d\.sprite\b\|scene\.effect\b' src/engine/engine.js
# Expected: 空

# 3) legacy 函式已刪
grep -n 'resolveSpriteFile\|renderLegacySprite' src/engine/engine.js
# Expected: 空

# 4) to_script_json 輸出 stage / active_effects
QT_QPA_PLATFORM=offscreen python -c "
from src.core.models import Project, Scene, Dialogue, StageSegment, EffectTrack, EffectSegment
p = Project(scenes=[Scene(id='s1',
    dialogues=[Dialogue(type='dialogue', text='hi', character='A')],
    stage_left=[StageSegment(0,0,'A')],
    effect_tracks=[EffectTrack('env', [EffectSegment(0,0,'rain')])])])
out = p.to_script_json()
d = out['scenes'][0]['dialogues'][0]
assert 'stage' in d and 'active_effects' in d
assert d['stage']['left']['character'] == 'A'
assert d['active_effects'] == [{'effect_type':'rain','params':{}}]
print('SCRIPT_JSON OK')
"

# 5) ADR-003 守護
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_capture_multi_sprite.py -v

# 6) ★ MP4 端到端實跑（user 手動驗收，不靠 codex）
#   - 建專案：A 角色 left lane (0,4)、B 角色 right lane (0,4)、env rain (0,4)、screen_shake (2,2)
#   - 5 句對話
#   - 匯出 MP4
#   - 用播放器確認：兩個立繪同畫面、雨效、第 3 句畫面震動
```

**MP4 端到端是 merge to main 的最終閘門**——pytest 全綠不夠。Codex 把 1-5 跑綠後，回報 user 接手 (6)。

---

## 風險與已知地雷

1. **`state_at` 與 `to_script_json` 的循環 import**：`scene_state` import models；models 想 import scene_state。改用 method 內 `from src.core.scene_state import state_at`（lazy import）規避。
2. **engine.js diff 量**：估計 ~150-200 行刪改。建議拆 commit：(a) renamed fields + applyTextEffects (b) legacy sprite 函式刪除 (c) VNEffects.setActive 接線。
3. **效能**：`to_script_json` 對長場景每個 dialogue 都呼叫 `state_at`，目前實作每次 O(N segments)。N 通常 <50，K 約幾百，總計 <50K ops；可接受。若實測慢再加 cache。
4. **multi-sprite 截圖測試環境**：QtWebEngine + offscreen + GPU 合成可能 flaky。Step 6.2 加 skipif 容錯。MP4 端到端最後 user 手動實跑驗收。
5. **舊 .vnsproj 仍會炸**：無使用者，不處理；測試 fixture `tests/01.vnsproj` 不被任何 test 載入，留著無妨（或順手刪）。
6. **Bug 1 (assets 搬移) + Bug 3 (stage 去重) 已在 main**：Phase 1/2/3 都從 main fork，自然 inherit，不需重做。

---

## 工作量估計

3-5 天。engine.js step 是最大塊（1-2 天）；test_capture_multi_sprite 含 PIL pixel 抓取 + skipif 環境處理約半天；其餘 Step 各小於半天。

## Phase 3 完成後狀態

- ✅ pytest 全綠
- ✅ Preview 正確顯示 stage / text_effects / active_effects
- ✅ MP4 端到端實跑通過（多立繪 + 特效）
- ✅ ZIP / HTML 匯出可離線播放
- ★ **可 merge phase-1 + phase-2 + phase-3 to main**

下一步（Phase 4+）：自訂 effect kinds / 軌道 rename + delete / 焦點保護 / 邊界防呆 / 頭像裁切 polish。
