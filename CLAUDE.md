# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# 虛擬環境（首次；跨平台一律裝在 .venv 內）
python3 -m venv .venv
source .venv/bin/activate                   # Linux / macOS
# .venv\Scripts\Activate.ps1                # Windows PowerShell
pip install -r requirements.txt

# 執行
python main.py

# 全部測試
pytest tests/

# Headless（CI / 無顯示環境）
QT_QPA_PLATFORM=offscreen python -m pytest tests/

# 單一測試檔 / 函式
pytest tests/test_text_parser.py
pytest tests/test_text_parser.py::test_dialogue_detection -v

# 打包 Windows exe
pip install pyinstaller
python -m PyInstaller vnstudio.spec --noconfirm
# 產物：dist/VisualNovel Studio/VisualNovel Studio.exe
```

---

## 專案定位

給台灣文字創作者的桌面工具。匯入文字 + 圖片 → 一鍵導出 MP4 影片，零學習門檻。

**核心優先級：MP4 影片 > ZIP 網頁 > 單一 HTML > 一鍵發布**

影片導出是最重要的功能。所有影響視覺呈現的改動，都要考慮影片導出是否需要同步更新。

---

## 分支工作流

新功能一律開新分支（`feature/xxx`），跑 `pytest tests/` 全過後才合併到 `main`。

跨 Phase 的架構決策（ADR）、踩過的雷、給接手者的備忘，集中記錄於
[`docs/DEVELOPMENT_HISTORY.md`](docs/DEVELOPMENT_HISTORY.md)。新功能若涉及跨端同步或破壞性變更，結束前把摘要追加該文件。

---

## 架構概覽

三層架構：

| 層 | 技術 | 位置 |
|---|---|---|
| **桌面 GUI** | Python + PyQt6 + qfluentwidgets | `src/ui/` |
| **播放引擎** | HTML5 + Vanilla JS（無框架） | `src/engine/` |
| **核心邏輯** | Python dataclasses + Pillow + FFmpeg | `src/core/` |

### UI 面板分工

`MainWindow` 是左右水平 Splitter（左 320px / 右佔滿）：

- **`left_panel.py`**：場景列表、場景屬性、角色列表
- **`center_panel.py`**：上方引擎預覽 + 下方 timeline 編輯器；timeline 由三個獨立 domain widget 並列組成（共用 Y 軸列高 `_timeline_shared.ROW_HEIGHT`）：
  - **`dialogue_list.py` (DialogueColumn)**：對話卡片列；自繪 + 手動拖拉重排
  - **`stage_panel.py` (StagePanel / StageLaneWidget)**：左 / 中 / 右三條互斥 `StageSegment` lane；端點拖拉、跨 lane 平移、雙擊空白新增
  - **`effect_timeline.py` (EffectTimeline)**：多條命名 `EffectTrack`，每軌內 segment 互斥（要疊加就開多條軌道）
- **`segment_editor.py`**：選中 segment 時顯示 inline 編輯器（StageSegment 級聯角色 / 服裝 / 差分；EffectSegment 改 `effect_type` + `params` JSON）
- **`preview_widget.py`**：QtWebEngine 內嵌引擎；`PreviewBridge` 透過 QWebChannel 傳遞 dialogue 高亮 / stage overlay 點擊事件

**qfluentwidgets：** UI 元件庫（`ComboBox`、`LineEdit`、`PushButton` 等）。新增對話框元件時優先用 `qfluentwidgets`，不用標準 Qt 同名元件。

### 資料流

1. 匯入 `.txt` / `.docx` → `text_parser.py` 逐行分類台詞 / 旁白
2. UI 顯示 timeline；使用者拉動 stage / effect segment 指定生效範圍
3. **預覽**：`preview_widget.py` 將 engine 檔案複製到 temp 目錄，把 `Project.to_script_json()` 注入成 `var SCRIPT_DATA = {...}` 全域變數，透過 `QUrl.fromLocalFile()` 載入
4. **導出**：ZIP（data.js + engine 整包）、單一 HTML（資產 Base64 內嵌）、MP4（QtWebEngine headless 截幀 + FFmpeg）

**CORS 解法：** `file://` 下無法 `fetch("script.json")`，改用 `data.js`（`var SCRIPT_DATA = {...};`）全域變數注入。預覽用同樣手法但注入到 `<head>`。

---

## 專案檔案格式

- **`.vnsproj`**：`project_io.py` 存讀的專案存檔（JSON），透過 `Project.to_dict()` / `Project.from_dict()` 序列化。**完整保留 lane / segment 結構**。
- **`script.json` / `data.js`**：engine 執行用的劇本資料，由 `Project.to_script_json()` 產生。**已把 `state_at` 預計算結果攤平到每個 dialogue**（見下節「script.json 格式」），與 `.vnsproj` 結構不同，勿混淆。

---

## 資料模型（`src/core/models.py`）

**Phase 1 後 Dialogue 已瘦身**：sprite / costume / stage / scene-level effect 都搬到 Scene 層級的 lane-based segment。畫面上要顯示什麼立繪、套用什麼特效，由覆蓋當前 `dlg_idx` 的 segment 決定。

```
Project
├── characters: list[Character]
│   └── Character(name, name_color, position, costumes)
│       └── Costume(name, expressions)
│           └── SpriteVariant(label, filename)
├── scenes: list[Scene]
│   ├── id, background, bgm
│   ├── dialogues: list[Dialogue]            # 瘦身：只留 type / text / character / text_effects
│   ├── stage_left:   list[StageSegment]     # 三條互斥 lane
│   ├── stage_center: list[StageSegment]
│   ├── stage_right:  list[StageSegment]
│   └── effect_tracks: list[EffectTrack]     # 多條命名軌道，每軌內互斥
│       └── EffectTrack(name, color, segments)
│           └── EffectSegment(start, end, effect_type, params)
├── assets: dict          # {"sprites": [...], "backgrounds": [...], ...}
└── game_settings: GameSettings(dialogue_font_size, name_font_size, dialogue_box_opacity)
```

### Segment 共通形狀

- `StageSegment(start, end, character, costume, sprite)`：`[start, end]` 範圍內，此槽位顯示該角色的指定立繪
- `EffectSegment(start, end, effect_type, params)`：`[start, end]` 範圍內，觸發此特效
- `start`、`end` 皆為 dialogue index（含端點）；同 lane 內**禁止重疊**

### `Scene` 自動 segment 維護

`Scene.insert_dialogue` / `remove_dialogue` / `move_dialogue` 會自動 shift 所有 segment 端點，並刪除歸零的 segment。**不要直接動 `scene.dialogues`** 的 `.append` / `.pop` / `del`，否則 segment 索引會錯位。

### `Character.position`

Legacy 欄位，新路徑不用。`to_dict()` 不再寫出此欄位；`from_dict()` 仍讀以相容舊檔；`to_script_json()` 仍輸出供 engine 角色卡資訊使用（新檔 default `"center"`）。

### `Dialogue.text_effects`

文字效果 key list（見 `src/core/effects.py::TEXT_EFFECTS`）。可多選，例如 `["bold", "shake"]`。engine.js 端依陣列為 `#dialogue-text` 加 `fx-{key}` class。**注意：欄位名是 `text_effects`，不是 `effects`**（Phase 1 改名）。

---

## state_at：跨欄位狀態的單一查詢入口

`src/core/scene_state.py::state_at(scene, dlg_idx)` 把所有 lane 的 active segment 整合成一個 dict：

```python
{
  "speaker": str | None,
  "text": str,
  "text_effects": list[str],
  "stage": {"left": StageSegment | None, "center": ..., "right": ...},
  "effects": list[EffectSegment],   # 所有 effect_tracks 在此 idx 的 active segment
}
```

**這是 Phase 3 後唯一的狀態查詢路徑。** engine.js 不再自行實作 `stateAt`；`Project.to_script_json()` 在匯出時對每個 dialogue 呼叫 `state_at`，把結果攤平寫進 script.json，前端只負責照搬。

---

## 關鍵同步規則

### 前端 / 後端公式必須一致

Auto 模式延遲計算——兩端使用同一邏輯：

```javascript
// engine.js（毫秒）
function getAutoDuration(text) {
  return Math.max(1500, 1000 + text.length * 150);
}
```

```python
# exporter_video.py（秒）
def _calc_duration(text):
    return max(1.5, min(1.0 + len(text) * 0.15, 8.0))
```

修改任一端時**必須同步更新另一端**。

### 文字效果 key 集合（Python ↔ JS）

`src/core/effects.py::TEXT_EFFECTS` 與 `src/engine/engine.js::TEXT_EFFECTS` 必須字面對齊；`tests/test_effects_sync.py` 會自動守護。新增效果時同步改三處 + `style.css` 加 `#dialogue-text.fx-{key}` 規則。

### 畫面特效（Canvas / body-class）

實作於 `src/engine/effects.js`（Phase 3 從 engine.js 拆出）。`VNEffects.setActive([{effect_type, params}, ...])` 由 engine 在每次 dialogue 切換時呼叫，輸入即 `state_at(...)["effects"]` 的攤平結果。

- **Canvas 型**（`rain` / `snow` / `crt`）：同時至多 1 個，取 list 第一個。
- **Body-class / filter 型**（`pixel_dark` / `screen_shake`）：可與 canvas 型疊加。
- 未知 `effect_type` → `console.warn`，不崩。

新增 effect_type 時同步：`effects.js` 加邏輯 + `style.css` 加 keyframe / class + 文檔列表。

### 角色卡（.vncard）

`src/core/character_library.py` 打包 `Character` + 立繪為 zip（`character.json` + `assets/`），預設存於 `~/.vnstudio/character_cards/`。匯入時立繪檔名衝突會自動 rename 並同步 `SpriteVariant.filename`。

---

## 文字解析規則

| 條件 | 結果 |
|------|------|
| 該行**僅包含**以「」包圍的文字（「」為行首與行尾） | 台詞（dialogue） |
| 其他所有情況 | 旁白（narration） |

每行獨立判斷，不跨行合併。空行作為段落分隔，不產生條目。

---

## script.json 格式（engine 消化）

由 `Project.to_script_json()` 產生。**Stage / active_effects 已攤平至每個 dialogue**，engine 不需要回頭看 lane：

```json
{
  "title": "故事標題",
  "characters": {
    "小明": {
      "name_color": "#4682B4",
      "position": "center",
      "sprites": { "普通": "char_xiaoming_normal.png" }
    }
  },
  "scenes": [
    {
      "id": "scene_001",
      "background": "bg_forest.png",
      "bgm": "bgm_peaceful.mp3",
      "dialogues": [
        {
          "type": "dialogue",
          "character": "小明",
          "text": "台詞內容。",
          "text_effects": ["bold"],
          "stage": {
            "left":   {"character": "小明", "costume": "制服", "sprite": "普通"},
            "center": null,
            "right":  null
          },
          "active_effects": [
            {"effect_type": "rain", "params": {}}
          ]
        }
      ]
    }
  ]
}
```

- `type`：解析器自動填入（`"dialogue"` / `"narration"`）
- `stage`：三槽固定有 key，無立繪則為 `null`
- `active_effects`：list；空 list 代表此 dialogue 無畫面特效

---

## engine.js 雙模式

| 模式 | 觸發條件 | 暴露 API |
|------|----------|----------|
| **Preview** | QWebChannel 可用（PyQt6 預覽） | `window.VNPreviewAPI`（`goToScene` / `goToDialogue`）、`window._bridge`（QWebChannel） |
| **Capture** | `window.VN_CAPTURE_MODE = true` | `window.VNCaptureAPI`（`goToScene` / `goToDialogue` / `getInfo`） |

**Capture 模式行為：** 跳過打字機、背景轉場、BGM；`body.capture-mode` class 隱藏所有 overlay 元素。Stage 立繪在 Capture 模式下**照常渲染**（MP4 要看到多人物）。

**Preview Bridge（`src/ui/preview_widget.py`）：** `PreviewBridge` 透過 QWebChannel 接收兩種 JS 事件：
- `on_dialogue_shown(scene_idx, dlg_idx)` → `dialogue_advanced` signal（同步表格高亮）
- `on_stage_slot_clicked(scene_idx, dlg_idx, position, action)` → `stage_slot_clicked` signal（開 picker）

**Stage Overlay：** Preview 模式下 engine.js 在 DOM 內建立 `+` / `✕` / `▼` 按鈕（`#stage-overlay`），匯出時由 JS（`if(!CAPTURE_MODE)`）與 CSS（`body.capture-mode #stage-overlay { display:none!important }`）雙重隱藏。

---

## 影片導出架構

**v2（目前）：headless QtWebEngine 截幀** — WYSIWYG，復用前端引擎，支援 Canvas 特效、Markdown 樣式。主執行緒運行，透過 `VNCaptureAPI` 驅動 engine.js 逐句截幀。

**v1（fallback）：Pillow 方案** — 穩定但無法渲染特效。程式碼保留，未從 UI 呼叫。

相關模組：
- `src/ui/webengine_capture.py`（v2 截幀導出）
- `src/core/exporter_video.py`（v1 Pillow）
- `src/core/ffmpeg_manager.py`（偵測 / 自動下載 FFmpeg；首次導出時觸發）
- `src/core/image_optimizer.py`（縮放至 1080p + 轉 WebP，導出前優化素材）
- `src/core/markdown_helper.py`（粗體 / 斜體 / 刪除線轉 HTML，與 engine.js 端規則對齊）

---

## 開發原則

1. **路徑處理全部用 `pathlib.Path`**，不用字串拼接。
2. **不用裸 `except:`**，錯誤處理要明確。
3. **優先使用標準庫**，非必要不引入第三方套件。
4. **UI 和邏輯分離**：PyQt6 只管介面（`src/ui/`），資料處理放 `src/core/`。
5. **每段程式碼要能用一句話說明它在做什麼。**
6. **改 dialogue 列表用 `Scene.insert/remove/move_dialogue`**，不要直接動 `scene.dialogues`，否則 segment 端點會錯位。

---

*VisualNovel Studio · 個人開發計畫 · 2026*
