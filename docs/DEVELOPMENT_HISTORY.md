# VisualNovel Studio 開發歷程

## 專案定位與原則

見 [CLAUDE.md](../CLAUDE.md)。核心優先級：**MP4 影片 > ZIP 網頁 > 單一 HTML > 一鍵發布**。

---

## 架構決策記錄（ADR）

### ADR-001: 三層架構（PyQt6 GUI / HTML5 Engine / Python Core）
- **背景**：需同時支援桌面編輯與網頁播放。
- **決策**：GUI (`src/ui/`) / Engine (`src/engine/`) / Core (`src/core/`) 嚴格分層。
- **代價**：跨端公式需手動同步（Auto 延遲、特效鍵名、Markdown 規則）。

### ADR-002: `data.js` 取代 `script.json` 解 CORS
- **背景**：`file://` 下 `fetch("script.json")` 受瀏覽器 CORS 拒絕。
- **決策**：改注入全域變數 `var SCRIPT_DATA = {...};`，預覽注入 `<head>`、匯出輸出 `data.js`。
- **代價**：`.vnsproj`（專案存檔）與 `data.js`/`script.json`（engine 資料）格式不同，勿混淆。

### ADR-003: QtWebEngine 截幀導出取代 Pillow
- **背景**：Pillow 方案無法渲染 Canvas 特效、Markdown 樣式。
- **決策**：v2 主執行緒 headless QtWebEngine + `VNCaptureAPI` 逐句截幀 + FFmpeg 編碼。
- **代價**：Stage 立繪必須在 `CAPTURE_MODE` 下照常渲染（MP4 要看到多人物）。

### ADR-004: `Character.position` 降為 legacy 欄位
- **背景**：新路徑用 `Dialogue.stage`（三槽 left/center/right）取代單一 position。
- **決策**：Phase A 起 `Character.to_dict()` 不再寫出 `position`；`from_dict` 仍讀以相容舊檔；`to_script_json()` 仍輸出 `position` 供 engine legacy 路徑使用。
- **代價**：舊專案開啟後儲存會丟失 position 欄位，但 engine 的 legacy fallback 會以 Character.position default `"center"` 填回；視覺無異。

### ADR-005: 解析器輸出的 dialogue 角色為 `None`（UI 顯示「(未選取)」）
- **背景**：計畫書初稿要求 `character="(未選取)"` 字面值。
- **決策**：保留 `character=None` 為「未指派」的資料模型表示，UI 層（`center_panel.py`）透過 `UNASSIGNED_LABEL` 顯示為「(未選取)」。語意不變、資料面更乾淨。
- **代價**：需在 UI 層處理 dialogue + None 的顯示 fallback（已在 `_on_char_combo_changed` 實作）。

---

## 策略筆記

- 每個 Phase 開 `feature/task-*` 分支，`pytest tests/` 全綠才合併回 `main`。
- 修改任一端（JS / Python）公式時，`grep` 另一端對齊。
- UI 新元件一律優先用 `qfluentwidgets`（`ComboBox`、`LineEdit`、`PushButton`）。
- 路徑處理一律 `pathlib.Path`，不用字串拼接。
- 跑測試需 `QT_QPA_PLATFORM=offscreen python -m pytest tests/`（無顯示環境時）。

---

## 里程碑紀錄

| 日期 | Phase | 成果 | 遺留 |
|---|---|---|---|
| 2026-04-18 | - | `task.md` 計畫書產出 | 漸變效果定義、D6 spike 決議 |
| 2026-04-18 | A | 表情→差分、台詞欄→文字欄、解析規則測試補強、`position` 降級為 legacy、既有測試補全 | 服裝/場景雙擊重命名延後 |

---

## 已知問題 / 踩過的雷

- **Windows 路徑空白 %20**（Phase F1 處理中）：`QUrl.fromLocalFile()` 編碼空白成 `%20`，若 assets 目錄含空白會導致 engine 找不到背景。
- **跨端公式**：`getAutoDuration`（JS）與 `_calc_duration`（Python）手動同步。
- **pygame 列於 requirements 但未用到**：可清理。
- **`Dialogue.stage` vs `Character.position`**：新檔路徑用 stage；engine legacy fallback 仍用 position（`to_script_json` 維持輸出）。

---

## Phase A 紀錄（2026-04-18）

### 成果
- A1 字串「表情」→「差分」全庫替換（保留內部變數 `expressions` 不改）。
- A4 對話表格 header「台詞」→「文字」、相關 delegate 註解同步。
- A5 解析器測試補 `test_parsed_dialogue_character_is_none`，驗證 dialogue 行 character 為 None 的契約。
- A6 `Character.to_dict()` 移除 `position` 欄位輸出；`from_dict` 保留 legacy 相容；`to_script_json` 維持輸出（engine 需要）。
- **Drive-by 修復**：
  - 建立先前遺失的 `tests/samples/sample_basic.txt`、`sample_edge.txt`（test_parse_basic_txt / test_parse_edge_txt 此前 FileNotFoundError）。
  - 修正 `test_project_path_serialization` 改用 `str(path)` 而非硬編 Windows 反斜線（此前 Linux CI 會 fail）。

### 驗證
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/` → 106 passed。

### 已完成（計畫書以為要做但實際已在的項目）
- A3 場景預設名：`Project.next_scene_id()` 已產「場景N」。
- A3 服裝預設名：`CostumeEditorDialog._on_add_costume` 已用 `f"服裝{len(...)+1}"` 預填。
- A7 UI 字體選單：`main_window.py` 已有 `[14,16,…,32]`、`theme.py::load_preference` default 18。
- A2 字體：`style.css:17` 與 `theme.py` `QFont.setFamilies` 均已為 `Microsoft JhengHei`。

### 給 Phase B 的備忘
- `CenterPanel` 的 `preview_toolbar` 已有 `btn_refresh_preview` / `spin_dlg_font` / `spin_name_font` / `spin_opacity` SpinBox，MainWindow 有 `_on_game_setting_changed` 即時連接；B3 主要只需評估是否把 SpinBox 改用 qfluentwidgets ComboBox/Slider。
- 主視窗已無「設定」menu，B1 視為已完成。
