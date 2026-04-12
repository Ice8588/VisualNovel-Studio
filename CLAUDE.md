# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Run the app
python main.py

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_text_parser.py

# Run a single test function
pytest tests/test_text_parser.py::test_dialogue_detection -v

# Install dependencies
pip install -r requirements.txt

# Build Windows executable
pip install pyinstaller
python -m PyInstaller vnstudio.spec --noconfirm
# Output: dist/VisualNovel Studio/VisualNovel Studio.exe
```

---

## 專案定位

給台灣文字創作者的桌面工具。匯入文字 + 圖片 → 一鍵導出 MP4 影片，零學習門檻。

**核心優先級：MP4 影片 > ZIP 網頁 > 單一 HTML > 一鍵發布**

影片導出是最重要的功能。所有影響視覺呈現的改動，都要考慮影片導出是否需要同步更新。

---

## 分支工作流

新功能一律開新分支（`feature/xxx`），跑 `pytest tests/` 全過後才合併到 `main`。

---

## 架構概覽

三層架構：

| 層 | 技術 | 位置 |
|---|---|---|
| **桌面 GUI** | Python + PyQt6 | `src/ui/` |
| **播放引擎** | HTML5 + Vanilla JS（無框架） | `src/engine/` |
| **核心邏輯** | Python dataclasses + Pillow + FFmpeg | `src/core/` |

**資料流：**
1. 使用者匯入 `.txt`/`.docx` → `text_parser.py` 逐行分類台詞/旁白
2. UI 顯示場景/對話，使用者指定角色與素材
3. `preview_widget.py` 將引擎檔案複製到 temp 目錄，注入 `<script>var SCRIPT_DATA = {...}</script>` 到 HTML，透過 `QUrl.fromLocalFile()` 載入
4. 導出：ZIP（data.js + engine）、單一 HTML（Base64）、MP4（QtWebEngine 截幀 + FFmpeg）

**CORS 解法：** `file://` 下無法 `fetch("script.json")`，改用 `data.js`（`var SCRIPT_DATA = {...};`）全域變數注入。預覽用同樣手法但注入到 `<head>`。

---

## 資料模型（`src/core/models.py`）

```
Project
├── characters: list[Character]
│   └── Character(name, name_color, position, costumes)
│       └── Costume(name, expressions)
│           └── SpriteVariant(label, filename)
├── scenes: list[Scene]
│   └── Scene(id, background, bgm, effect, dialogues)
│       └── Dialogue(type, text, character, sprite, costume, effects, stage)
├── assets: dict          # {"sprites": [...], "backgrounds": [...], ...}
└── game_settings: GameSettings(dialogue_font_size, name_font_size, dialogue_box_opacity)
```

**Stage 槽位（`Dialogue.stage`）：** 三個固定槽位 `{"left", "center", "right"}`，各自為 `None` 或 `{"character": str, "sprite": str|None, "costume": str|None}`。說話者（`Dialogue.character`）只決定名牌；畫面上顯示哪些立繪由 `stage` 決定。無 `stage` 的舊檔自動退回 legacy 單立繪（向下相容）。

**`Character.position`：** legacy 欄位，新路徑（有 stage）不使用，但為向下相容請保留。

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

修改任一端時**必須同步更新另一端**。同理適用於：特效名稱（rain/snow/crt/pixel_dark）、Markdown 渲染規則。

---

## 文字解析規則

| 條件 | 結果 |
|------|------|
| 該行**僅包含**以「」包圍的文字（「」為行首與行尾） | 台詞（dialogue） |
| 其他所有情況 | 旁白（narration） |

每行獨立判斷，不跨行合併。空行作為段落分隔，不產生條目。

---

## script.json 格式

```json
{
  "title": "故事標題",
  "characters": {
    "小明": {
      "name_color": "#4682B4",
      "position": "left",
      "sprites": { "普通": "char_xiaoming_normal.png" }
    }
  },
  "scenes": [
    {
      "id": "scene_001",
      "background": "bg_forest.png",
      "bgm": "bgm_peaceful.mp3",
      "effect": "rain",
      "dialogues": [
        {
          "type": "dialogue", "character": "小明", "sprite": "普通", "text": "台詞內容。",
          "stage": {
            "left":   {"character": "小明", "sprite": "普通", "costume": null},
            "center": null,
            "right":  null
          }
        },
        { "type": "narration", "character": null, "sprite": null, "text": "旁白文字。" }
      ]
    }
  ]
}
```

- `type`：解析器自動填入（`"dialogue"` 或 `"narration"`）
- `effect`：`"rain"` / `"snow"` / `"crt"` / `"pixel_dark"` / `null`
- `stage`：三槽皆 null 時省略（舊檔相容）；engine.js 無此欄時走 legacy 單立繪

---

## engine.js 雙模式

| 模式 | 觸發條件 | 暴露 API |
|------|----------|----------|
| **Preview** | QWebChannel 可用（PyQt6 預覽） | `window.VNPreviewAPI`（`goToScene`/`goToDialogue`）、`window._bridge`（QWebChannel） |
| **Capture** | `window.VN_CAPTURE_MODE = true` | `window.VNCaptureAPI`（`goToScene`/`goToDialogue`/`getInfo`） |

**Capture Mode 行為：** 跳過打字機、背景轉場、BGM；`body.capture-mode` class 隱藏所有 overlay 元素。Stage 立繪在 Capture 模式下**照常渲染**（MP4 要看到多人物）。

**Preview Bridge（`src/ui/preview_widget.py`）：** `PreviewBridge` 透過 QWebChannel 接收兩種 JS 事件：
- `on_dialogue_shown(scene_idx, dlg_idx)` → `dialogue_advanced` signal（同步表格高亮）
- `on_stage_slot_clicked(scene_idx, dlg_idx, position, action)` → `stage_slot_clicked` signal（開 picker）

**Stage Overlay：** Preview 模式下 engine.js 在 DOM 內建立 `+`/`✕`/`▼` 按鈕（`#stage-overlay`），匯出時由 JS（`if(!CAPTURE_MODE)`）與 CSS（`body.capture-mode #stage-overlay { display:none!important }`）雙重隱藏。

---

## 影片導出架構

**v2（目前）：headless QtWebEngine 截幀** — WYSIWYG，復用前端引擎，支援 Canvas 特效、Markdown 樣式。主執行緒運行，透過 `VNCaptureAPI` 驅動 engine.js 逐句截幀。

**v1（fallback）：Pillow 方案** — 穩定但無法渲染特效。程式碼保留，未從 UI 呼叫。

相關模組：`src/ui/webengine_capture.py`（v2 截幀導出）、`src/core/exporter_video.py`（v1 Pillow）、`src/core/ffmpeg_manager.py`（偵測/下載 FFmpeg）。

---

## 開發原則

1. **路徑處理全部用 `pathlib.Path`**，不用字串拼接。
2. **不用裸 `except:`**，錯誤處理要明確。
3. **優先使用標準庫**，非必要不引入第三方套件。
4. **UI 和邏輯分離**：PyQt6 只管介面（`src/ui/`），資料處理放 `src/core/`。
5. **每段程式碼要能用一句話說明它在做什麼。**

---

*VisualNovel Studio · 個人開發計畫 · 2026*
