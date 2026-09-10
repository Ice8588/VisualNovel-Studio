# CLAUDE.md

給 Claude Code 的專案指引。**只記錄無法從程式碼直接推得的資訊**——gotcha、跨端同步規則、業務決策、非顯然的 workaround。詳細結構讀對應原始碼。

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

# 安裝依賴
pip install -r requirements.txt

# 打包 Windows exe
pip install pyinstaller
python -m PyInstaller vnstudio.spec --noconfirm
# 產物：dist/VisualNovel Studio/VisualNovel Studio.exe
```

---

## 專案定位

給台灣文字創作者的桌面工具。匯入文字 + 圖片 → 一鍵導出 MP4 影片，零學習門檻。

**核心優先級：MP4 影片 > ZIP 網頁 > 單一 HTML > 一鍵發布。** 影片導出最重要；所有影響視覺呈現的改動，都要考慮影片導出是否需要同步更新。

---

## 分支工作流

新功能與修正一律從小寫 `dev` 建立 `feature/xxx` 或 `fix/xxx`，完成後先合回 `dev`。`main` 僅保留正式公開結果，必須按 `CONTRIBUTING.md` 的驗收與 squash 發布流程處理。歷史計畫中的舊分支規則不再適用；以 `AGENTS.md` 與 `CONTRIBUTING.md` 為準。

跨 Phase 的架構決策（ADR）、踩過的雷、給接手者的備忘，集中記錄於 [`docs/DEVELOPMENT_HISTORY.md`](docs/DEVELOPMENT_HISTORY.md)。涉及跨端同步或破壞性變更時，結束前把摘要追加該文件。

---

## 架構速覽

| 層 | 技術 | 位置 |
|---|---|---|
| 桌面 GUI | Python + PyQt6 + qfluentwidgets | `src/ui/` |
| 播放引擎 | HTML5 + Vanilla JS（無框架） | `src/engine/` |
| 核心邏輯 | Python dataclasses + Pillow + FFmpeg | `src/core/` |

- `center_panel.py` 的 timeline 由 `dialogue_list` / `stage_panel` / `effect_timeline` 三個 widget 並列組成，共用 `_timeline_shared.ROW_HEIGHT`。
- UI 元件優先用 `qfluentwidgets`（`ComboBox` / `LineEdit` / `PushButton` 等），不用標準 Qt 同名元件。
- 影片導出 v2（目前）走 headless QtWebEngine 截幀（WYSIWYG，支援特效）；v1 Pillow 方案保留為 fallback，未從 UI 呼叫。

---

## 關鍵同步規則與 gotcha

### CORS workaround：file:// 不能 fetch

`file://` 下無法 `fetch("script.json")`，改用 `data.js`（`var SCRIPT_DATA = {...};`）全域變數注入。預覽用同樣手法但注入到 `<head>`。

### Auto duration 公式：Python ↔ JS 雙端必須一致

```javascript
// engine.js（毫秒）
function getAutoDuration(text) {
  return Math.max(1500, Math.min(1000 + text.length * 150, 8000));
}
```

```python
# exporter_video.py（秒；webengine_capture.py 亦 import 此函式，Python 端僅此一份）
def calc_auto_duration(text):
    return max(1.5, min(1.0 + len(text) * 0.15, 8.0))
```

修改任一端時**必須同步更新另一端**；`tests/test_duration_sync.py` 自動守護。

### TEXT_EFFECTS key 集合 Python ↔ JS 必須對齊

`src/core/effects.py::TEXT_EFFECTS` 與 `src/engine/engine.js::TEXT_EFFECTS` 字面一致；`tests/test_effects_sync.py` 自動守護。新增效果時三處同步：兩個常數 + `style.css` 加 `#dialogue-text.fx-{key}` 規則。

### 畫面特效：Canvas vs body-class 疊加規則

實作於 `src/engine/effects.js`，由 `VNEffects.setActive([...])` 在每次 dialogue 切換時呼叫。

- **Canvas 型**（`rain` / `snow` / `crt`）：同時至多 1 個，取 list 第一個。
- **Body-class / filter 型**（`pixel_dark` / `screen_shake`）：可與 canvas 型疊加。
- 未知 `effect_type` → `console.warn`，不崩。

### state_at 為唯一狀態查詢路徑

`src/core/scene_state.py::state_at(scene, dlg_idx)` 整合所有 lane 的 active segment。**這是 Phase 3 後唯一的查詢入口**——engine.js 不再自行實作 `stateAt`；`Project.to_script_json()` 在匯出時把結果**攤平**寫進每個 dialogue（`stage` / `active_effects` 欄位），前端只負責照搬。新功能要查狀態時不要繞過此函式。

### 改 dialogue 列表必經 Scene 方法

`Scene.insert_dialogue` / `remove_dialogue` / `move_dialogue` 會自動 shift 所有 stage / effect segment 端點，並刪除歸零的 segment。**不要直接動 `scene.dialogues`** 的 `.append` / `.pop` / `del`，否則 segment 索引會錯位。

### 文字解析規則

| 條件 | 結果 |
|------|------|
| 該行**僅包含**以「」包圍的文字（「」為行首與行尾） | 台詞（dialogue） |
| 其他所有情況 | 旁白（narration） |

每行獨立判斷，不跨行合併。空行為段落分隔，不產生條目。

### engine.js 雙模式：Preview / Capture

- Preview 模式：`window.VNPreviewAPI` + QWebChannel；`PreviewBridge` 接收 `on_dialogue_shown` / `on_stage_slot_clicked` 兩種事件。
- Capture 模式（`window.VN_CAPTURE_MODE = true`）：`window.VNCaptureAPI`；跳過打字機 / 背景轉場 / BGM。
- **Stage 立繪在 Capture 模式下照常渲染**（MP4 要看到多人物）。
- **Stage Overlay 雙重隱藏**：Preview 才產 `+` / `✕` / `▼` 按鈕，匯出時由 JS（`if(!CAPTURE_MODE)`）+ CSS（`body.capture-mode #stage-overlay { display:none!important }`）雙重把關。

### .vnsproj vs script.json 不可混淆

- `.vnsproj`（`project_io.py`）：完整保留 lane / segment 結構的存檔。
- `script.json` / `data.js`（`Project.to_script_json()`）：給 engine 消化的攤平結果，**結構不同**。

---

## 開發原則

1. 路徑處理全部用 `pathlib.Path`，不用字串拼接。
2. 不用裸 `except:`，錯誤處理要明確。
3. 優先使用標準庫，非必要不引入第三方套件。
4. UI 和邏輯分離：PyQt6 只管介面（`src/ui/`），資料處理放 `src/core/`。
5. 每段程式碼要能用一句話說明它在做什麼。

---

*VisualNovel Studio · 個人開發計畫 · 2026*
