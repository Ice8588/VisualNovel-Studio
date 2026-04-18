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

## Hotfix 紀錄（2026-04-19 c）

### 字框規格反轉：改回視覺小說標準（固定全寬、文字靠左）
- **背景**：使用者更正需求——**希望**字框「每次大小和位置都長一樣，不隨文字變動，文字靠左對齊，像視覺小說那樣」。先前 Phase E 做的 auto-width 是誤解；這是回退變更。
- **修正**：
  - `style.css` `#dialogue-box`：改回 `left: 0; right: 0`（全寬橫條）、`padding: 18px 32px`、`min-height: 150px`（3 行以上空間）、移除所有 `width / max-width / transform` 動態屬性。
  - `#dialogue-text`：`text-align: left`、`min-height: 3.2em`（兩行預留）。
  - `engine.js` 移除 `sizeDialogueBox()` 函式、量測 span、所有呼叫點（typeText/skipTypewriter/showDialogue/applyGameSettings/resize listener）。
- **驗證**：`pytest tests/` → 120 passed。目視煙測：短台詞、長台詞、typewriter 過程中字框尺寸與位置完全不變，文字從左側逐字顯現。
- **給 CODEX 的備忘**：
  - 此回退涵蓋 Phase E 的 E1（auto-width）、以及三次 Hotfix（`fix/dialogue-box-grow` / JS 量測 / CSS fit-content 嘗試）。
  - MP4 匯出（CAPTURE_MODE）亦同樣使用固定字框（CSS 一致），與 Preview 一致。
  - `#name-plate` 仍維持 `inline-block + 半透明 name_color` 設計（B7）。

---

## Hotfix 紀錄（2026-04-19 b）

### 匯入按鈕裁切 + 字框仍不動態
- **症狀**：
  - 左側 Inspector 的「匯入」按鈕（背景/BGM 列）在 28px 字體下被裁切成「匯)」。原因：`setFixedWidth(50)` 鎖死寬度，字體放大後容不下「匯入」二字。
  - 字框 `width: fit-content` 在 QtWebEngine typewriter innerHTML 逐字更新時不會逐步重新 layout（WebEngine 的 reflow cache），使用者看到字框大小、位置永遠相同。
- **修正**：
  - 左側 Inspector「匯入」按鈕：移除 `setFixedWidth(50)`（背景 / BGM 兩處），讓 sizeHint 決定寬度。
  - 搜尋箭頭按鈕（`btn_search_prev/next`）：`setFixedWidth(30)` → `setMinimumWidth(40)`。
  - 舞台槽按鈕（`_StageCellWidget`）：移除 `setFixedHeight(24)`。
  - **字框動態寬度改由 JS 顯式量測**：
    - `style.css` 拿掉 `#dialogue-box` 的 `width: fit-content / min-width / max-content` 規則，改由 JS 控制。
    - `engine.js` 新增 `sizeDialogueBox()`：建立隱藏 `<span>` 複製 `#dialogue-text` 字型，設 `white-space: nowrap` 量測文字「若不換行」的真實像素寬，加 padding 44，夾在 [80, container-48]，寫回 `#dialogue-box.style.width`。
    - 呼叫點：`typeText` 每次 innerHTML 更新、`skipTypewriter`、`showDialogue` 的 Capture/Skip 分支、`applyGameSettings` 變更字體後、`window.resize`。
    - CSS 新增 `transition: width 0.08s ease-out;` 讓寬度變化平滑（不會閃爍）。
- **驗證**：
  - `pytest tests/` → 120 passed。
  - 目視煙測（使用者端）：
    1. 短台詞「好。」→ 字框約 120-160px（貼合文字 + min 80 floor）。
    2. 中台詞「這真的是我想做的事嗎？」→ 字框明顯加寬。
    3. 長台詞（100+ 字）→ 字框達 max-width，文字內部換行、box 高度增加、寬度停在 container-48。
    4. typewriter 過程字框每字都加寬一點點（transition 平滑）。
- **給 CODEX 的備忘**：
  - 量測 span 附加到 `document.body`，僅建立一次（lazy singleton）；不需清理。
  - 量測用 `innerHTML`（含 `<strong>/<em>` 等 mdToHtml 產物），確保粗體／斜體樣式的寬度差被涵蓋。
  - 若以後要把字框貼齊左 / 右（非置中），修改 CSS `left` 與 `transform` 即可，JS 量測不受影響。

---

## Hotfix 紀錄（2026-04-19）

### 預覽工具列裁切 + 所有文字框留白
- **症狀**：
  - 預覽工具列 `重新整理` 按鈕與 SpinBox 在 UI 字體放大後被裁切為「更斯登中」「1·」「0·」。
  - UI 字體大小變更後工具列沒有跟著放大（fixed* 硬編尺寸蓋過）。
  - 使用者要求所有字體上限改 28px（30/32 不需要）、所有文字框要有足夠留白。
- **修正**：
  - 工具列：移除 `setFixedWidth` / `setFixedHeight`，改 `setMinimumWidth(110 / 110 / 100)` + `layout.setSpacing(10)`，控件依 sizeHint 自動伸縮。
  - 字體上限 32 → 28 統一於：
    - `main_window.py` UI 字體選單（`[14,16,18,20,22,24,26,28]`）
    - `theme.py::load_preference` 讀取後夾 [14, 28]
    - `models.py::GameSettings.from_dict` 夾 [14, 28]
    - `engine.js::applyGameSettings` 夾 [14, 28]
    - `center_panel.py` 對話/名稱字體 SpinBox range `setRange(14, 28)`
    - `tests/test_models.py::test_from_dict_clamps_out_of_range` 期望值同步
  - QSS 留白擴充（`theme.py` 深 / 淺兩套）：
    - `QPushButton`: `5px 12px` → `7px 16px`
    - `QComboBox`: `4px 8px` → `6px 28px 6px 12px`（右側留給 dropdown 箭頭）
    - `QComboBox QAbstractItemView::item`: 新增 `padding 6px 10px; min-height 20px`
    - `QLineEdit`: `4px` → `7px 10px`
    - `QSpinBox / QDoubleSpinBox`: `3px` → `6px 24px 6px 10px` + `min-height 22px` + 明確 `up-button / down-button width 18px`
    - `QPlainTextEdit / QTextEdit`: `4px` → `8px 10px`
    - `QMenuBar::item` 新增 `padding 6px 14px`、`QMenu::item` `padding 6px 22px 6px 18px`
    - `QHeaderView::section`: `4px` → `6px 10px`
    - `QComboBox#tableCombo`（表格內嵌）: `1px 4px` → `4px 8px`
  - 對話表格列高：40 → 56（內嵌 ComboBox padding 變大需要更高列高才不擠壓）。

### 驗證
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/` → 120 passed。
- Headless smoke（28px）sizeHint 量測：
  - `btn_refresh` 138×54 ✓
  - `spin_dlg_font` 163×59（min 110×36）✓
  - `spin_opacity` 146×59 ✓
- Headless smoke（18px）：btn 98×40、spin 128×45。皆不再裁切。

### 給 CODEX 的備忘
- 若使用者之前已存 font_size > 28 的偏好，`load_preference` 已自動夾回 28，不需手動清除 QSettings。
- 對話表格列高變大後，若使用者覺得條目間距過大，可調整 `setDefaultSectionSize(56)` 或改用 `resizeRowsToContents()` 依實際內容高度。

---

## Hotfix 紀錄（2026-04-18）

### 字框 auto-width 逐字展開修正
- **症狀**：Phase E 交付後使用者回報「字框被壓縮／文字比框還大被切割」、「字框大小固定，不隨 typewriter 展開」。
- **診斷**：
  - `width: max-content` 在 QtWebEngine 的 typewriter innerHTML 連續更新下，box 不一定每幀 reflow，視覺上像「固定」。
  - `#name-plate` 設 `max-width: 100%` 與 `#dialogue-box` 的 `width: max-content` 形成循環約束（parent 等 child 算寬、child 又綁 parent 寬），行為不穩定。
  - `#dialogue-text` 的 `min-height: 60px` + `#dialogue-box` 的 `min-height: 100px` 讓初始空框很高，加深「固定大小」錯覺。
- **修正**：
  - 改 `#dialogue-box`：`width: fit-content`、`min-width: 160px`、`max-width: calc(100% - 48px)`、移除 `min-height`，改 `padding: 14px 22px`。
  - 改 `#dialogue-text`：`min-height: 1.6em`（一行保留）、`word-break: break-word`、明確 `white-space: normal`。
  - 改 `#name-plate`：移除 `max-width: 100%` 與 `overflow/text-overflow` 規則，避免與父層循環依賴。
- **驗證**：`QT_QPA_PLATFORM=offscreen pytest tests/` → 120 passed；視覺煙測需使用者確認字框逐字展開、長台詞不再切字。

---

## Phase E 紀錄（2026-04-18）

### 成果
- **E1 字框 auto-width**：`style.css` 將 `#dialogue-box` 改為 `width: max-content; max-width: calc(100% - 64px); min-width: 240px; left: 50%; transform: translateX(-50%); padding: 16px 24px; border-radius: 4px`。短台詞變浮動貼合、長台詞觸發 max-width 自動換行，不超出預覽容器。
- **E2 字體 14-32 夾住**：
  - `GameSettings.from_dict` 把 `dialogue_font_size` / `name_font_size` 夾至 [14, 32]；舊檔不合法值自動修正。
  - engine.js `applyGameSettings` 同樣 clamp（雙保險，資料 / 呈現都不會爆）。
  - 新增 3 個測試（`TestGameSettings`）：預設值、out-of-range 夾住、in-range 不變。
- **既有 UI 字體 14-32** 選單（Phase A verify pass 已記錄）預設 18 不變。

### 驗證
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/` → 120 passed（新增 3 個 GameSettings）。
- 目視需確認（CODEX）：
  - 極短台詞（例：「好。」）字框寬度貼合。
  - 極長台詞（100+ 字）字框觸發換行但不超過畫面 96% 寬。
  - 影片導出（CAPTURE_MODE）的 MP4 每張截幀字框位置與預覽一致（字框 `translateX(-50%)` 居中在 CAPTURE_MODE 下動畫被抑制，不會有位移瑕疵）。

### 給 CODEX 的備忘
- 字框改為 auto-width 會顯著影響 MP4 視覺佈局：舊專案（字框原本填滿寬度）轉新版後，短台詞會看起來「窗格漂浮」。若需回退，修改 `style.css::#dialogue-box` 把 `width` 拿掉、改回 `left:0; right:0` 即可。
- E1 未新增 `game_settings.dialogue_box_width_mode` 欄位（使用者無此要求；若之後要「滿寬 vs 貼合」雙模，可之後再擴充）。

---

## Phase D 紀錄（2026-04-18）

### 成果（D1 / D2 / D3 / D4 / D5；漸變刪除、D6 跳過）
- **D1 文字效果多選**：
  - 新增 [`src/core/effects.py`](../src/core/effects.py) 作為 Python / JS 雙端共同的 `TEXT_EFFECTS` 定義單一來源（bold / italic / underline / strikethrough / shake / blink）。
  - engine.js 端新增 `TEXT_EFFECTS` 常量 + `applyTextEffects(list)` 為 `#dialogue-text` 加 `fx-{key}` class；`style.css` 加對應規則與 `@keyframes vn-shake`、`vn-blink`。
  - `center_panel.py` 新增 `_EffectsMenuButton`：PushButton 觸發 QMenu 可勾選項目，`effects_changed` signal 通知 row 寫回 `dlg.effects`。
  - 新增 [`tests/test_effects_sync.py`](../tests/test_effects_sync.py) 以 regex 抽 engine.js 的 key 清單，斷言與 Python 端集合相同。
  - **漸變（gradient）依使用者指示從選項中刪除**（語意分歧且 CSS `background-clip: text` 跨瀏覽器行為不一致）。
- **D2 說話 vs 畫面分離（UI 文案）**：對話表格欄位 header 加 tooltip 明示「角色 = 說話（名牌）」、「舞台 = 畫面（三槽）」；實際資料模型早已分離，只是 UI 缺引導。
- **D3 舞台欄三槽子 cell**：新增 `_StageCellWidget`（L / C / R 三按鈕），取代原本單一 `L● C○ R○` 指示；每按鈕點擊透過 `_open_stage_picker` 觸發 `StageSlotPickerDialog`。舞台欄寬 120 → 170。
- **D4 角色色背景**：以 `_hex_to_qcolor(name_color, alpha=56)` + `_contrast_text_qcolor()`（YIQ 公式）為 `# 索引` 與「文字」兩欄上色，形成行色帶；其他 cellWidget 欄（角色 / 服裝 / 差分 / 效果 / 舞台）刻意不染色以避免與既有 QSS 衝突。
- **D5 拖曳放置線**：`_DraggableTable` 新增自訂 `dragMoveEvent`/`paintEvent`，以 3px `#46B4DC` 線繪於插入位置（取代 Qt 預設指標）。

### 驗證
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/` → 117 passed（新增 1 個 sync 測試）。
- Headless smoke：`from src.ui.main_window import MainWindow; MainWindow().show()` 不崩潰（WebEngine 回退 software rendering 為 Linux/headless 正常行為）。

### 跳過 / 刪除項目
- **D6 POC spike**：依使用者決定跳過；現有 `QTableWidget` + delegate 組合已承載 D1~D5 全部功能。
- **漸變文字效果**：依使用者決定刪除；Python / JS 端同步不再宣告 `gradient` key。

### 給 CODEX 的備忘
- 之後若要加新效果：(1) 於 `effects.py::TEXT_EFFECTS` 增筆；(2) engine.js 同名 TEXT_EFFECTS 加同 key；(3) style.css 加 `#dialogue-text.fx-{key}` 規則（及 `@keyframes` 若為動畫）；(4) `test_effects_sync.py` 自動守護；(5) CAPTURE_MODE 已透過 `* { animation: none }` 統一抑制動畫，影片導出無需額外處理。
- D4 若要擴展到全欄上色，需解決 cellWidget 的 QSS 層級問題（可考慮 proxy style 或 custom viewport paint），Phase E 之後可視需求再加。

---

## Phase C 紀錄（2026-04-18）

### 成果
- **C2 dropzone**：`CharacterEditorDialog` 整個對話框接受圖片拖曳（`dragEnterEvent`/`dropEvent`），PNG / JPG 自動 `import_asset` 成立繪並更新預覽縮圖。多檔拖入時只取第一張（這個對話框只管單一預設立繪，多差分改用 `CostumeEditorDialog`）。
- **C3 雙擊重命名差分**：`CostumeEditorDialog._expr_list` 設 `DoubleClicked | EditKeyPressed` 觸發、`ItemIsEditable` flag，`_on_expr_label_changed` 把新 `label` 寫回 `SpriteVariant`；空字串還原避免誤改。
- **C6 角色卡跨專案共享**：
  - 新增 [`src/core/character_library.py`](../src/core/character_library.py)：
    - `get_library_dir()` → `~/.vnstudio/character_cards/`（跨平台）。
    - `save_card(character, assets_dir)` 打包為 `.vncard` zip（含 `character.json` + `assets/`），檔名衝突加數字後綴。
    - `list_cards()`、`load_card(card, target_assets_dir)`（衝突檔名自動 rename，更新 SpriteVariant.filename）、`delete_card()`。
  - `CharacterEditorDialog` 新增「儲存為角色卡…／從角色卡匯入…」按鈕；匯入後若卡內含多差分，`get_character()` 保留完整 costumes（`_loaded_from_card` flag）。
  - 測試：[`tests/test_character_library.py`](../tests/test_character_library.py) 10 個案例涵蓋 save/list/load 迴圈、檔名衝突、不合法檔、unicode 與特殊字元角色名。

### 驗證
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/` → 116 passed（新增 10 個）。
- 手動煙測：在 A 專案儲卡 → 開 B 專案『從角色卡匯入』→ 檢查立繪複製至 B 的 `assets/`。

### 已完成（計畫書以為要做但實際已在的項目）
- C1 新增角色只加一張預設立繪：`CharacterEditorDialog` 本來就設計為單張。
- C4 屬性面板不回跳場景：`left_panel.refresh_characters(keep_tab=True)` 已在 `main_window._on_edit_character` 與 `_on_character_property_changed` 呼叫。
- C5 預設色盤：`_PRESET_COLORS` 8 色已實作。

### 給 CODEX 的備忘
- 角色卡儲存路徑固定於 `~/.vnstudio/character_cards/`（開放問題 #1 預設決策）。
- 匯入角色卡時立繪檔名衝突會自動 rename 為 `{name}_1.{ext}`，SpriteVariant.filename 同步更新；既有檔案不被覆寫（安全優先）。
- `.vncard` 格式：zip + `character.json` + `assets/*`，對應於 CLAUDE.md 的「專案檔案格式」章節（如果文件需要同步，請於 Phase D/E 結束後補）。

---

## Phase B 紀錄（2026-04-18）

### 成果（B4/B5/B6/B7；B1/B2/B3 先前已完成）
- **B4 淺色預覽**：
  - `PreviewWidget` 新增 `_theme_name` 與 `set_theme(theme)`；`reload_preview` 將 `<body>` 注入 `preview-dark` / `preview-light` class。
  - `MainWindow._apply_theme_immediate` 呼叫 `preview.set_theme()`；啟動時 `_setup_ui` 也同步初始主題。
  - `style.css` 末段新增 `body.preview-light ...` 規則：容器背景 `#f5f5f7`、字框 `rgba(255,255,255,0.9)`、深色字、Quick Menu / History 面板、槽位按鈕均做對應。
- **B5 預覽/文字列表 50/50**：`center_panel.py` splitter `setStretchFactor(1,1)` + `setSizes([400,400])`。
- **B6 槽位按鈕垂直置中、▼ 常駐**：`.slot-control` 改 `top:50%; transform: translate(-50%,-50%)`；`.slot-control.filled .btn-swap` 無 hover 也顯示，`.btn-clear` 維持 hover 才出現。
- **B7 名牌貼合文字 + 半透明名色**：`#name-plate` 改 `display:inline-block`，CSS 內建 fallback `rgba(70,130,180,0.6)`；engine.js 新增 `hexToRgba(hex, alpha)` helper，`showDialogue` 動態塞 `rgba(name_color, 0.6)` 到 `background`。

### 驗證
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/` → 106 passed。
- 目視需確認：
  - 切換深 / 淺主題後預覽跟著變（B4）。
  - 長短角色名字的名牌寬度貼合（B7）。
  - 舞台上有 / 無角色皆能看到槽位控件（B6）。

### 已完成（計畫書以為要做但實際已在的項目）
- B1 工具列「設定」項已不存在。
- B2 快捷鍵已改用 `setShortcut()` 與 action text 分離。
- B3 預覽上方即時控件（字體 / 名牌 / 透明度）已存在，MainWindow `_on_game_setting_changed` 即時同步 `game_settings` 並 `reload_preview`。

### 給 CODEX 的備忘
- B4 僅作用於 Preview 模式（`<body class="preview-light/dark">`）；MP4 匯出時 `webengine_capture.py` 走獨立路徑、`<body>` 不帶此 class → 截幀不會被淺色覆蓋（這是刻意行為）。
- B7 `hexToRgba` 對非合法 hex 回傳預設藍色半透明，避免非預期的角色色崩壞版面。

---

## Phase F 紀錄（2026-04-18）

### 成果
- **F1 場景背景不顯示於預覽**：engine.js 背景 CSS `url(...)` 未引號化，檔名含空白（常見 Windows `D:\VisualNovel Studio\assets\my bg.png`）時 CSS 解析失敗。修正為 `url("...")` 並 escape 內嵌雙引號 → `engine.js:195-196`。
- **F2 LOG 基礎建設**：新增 `_LoggingPage(QWebEnginePage)` 捕捉 JS `console.log` / `warning` / `error`，輸出到 Python `stderr`；任何後續 Phase 的 JS bug 都可透過終端觀察。

### 驗證
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/` → 106 passed。
- 手動煙測：啟 `python main.py`，匯入含空白路徑的背景圖，確認終端出現 `[WebEngine INFO/WARN/ERROR]` 字樣且預覽背景正常呈現（CODEX 需於 Windows 環境目視驗證）。

### 給 CODEX / 下一位的備忘
- 若 engine 新增其他 CSS `url(...)` 引用（例如 effects.js 可能在 overlay 元素塞圖），同樣要用雙引號包裹。
- sprite `<img src>` 與 BGM `new Audio(src)` 不受此 bug 影響（屬性值會自動處理）。

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
