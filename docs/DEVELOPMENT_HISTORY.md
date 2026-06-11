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

## UX 走查修復紀錄（2026-06-11，fix/ux-audit）

以 QTest 驅動腳本模擬真實使用者全功能走查（框架與逐步紀錄在 `build/uxtest/`，
完整問題清單見 `build/uxtest/UX_REPORT.md`），證實 3 個 S0 + 3 個 S1 bug 並修復：

- **編輯角色丟服裝/差分（資料遺失）**：`CharacterEditorDialog.get_character()` 原本一律重建
  `[服裝1(單立繪)]`，編輯任何多服裝角色按 OK 即靜默毀資料；「儲存為角色卡」同路徑連帶只剩服裝1。
  改三情境分支：編輯既有角色以 `deepcopy(_original.costumes)` 為基礎，只覆寫名稱/名牌色/預設立繪；
  按「清除」立繪刻意不刪資料（寧可忽略清除也不無聲毀損）。
- **MP4 被短 BGM 截斷（核心功能）**：`-shortest` + 單一 BGM 直接回傳原檔（不裁不補），
  2 秒 BGM 會把 14.7 秒影片截成 2 秒且顯示「導出成功」。改為移除 `-shortest`、
  一律 `-t {sum(concat durations)}` 控長（**BGM 不足補靜音、超長截斷、刻意不循環**）；
  順帶修掉無 BGM 時末幀重複造成的 +2.3 秒尾巴，以及單 BGM `start>0`（首場景無 BGM）提早播放的偏移。
  ffmpeg 指令組裝抽成 `_build_encode_cmd` 方法供單元測試。
- **點角色欄拋 AttributeError**：qfluentwidgets 的 `ComboBox` 不是 QComboBox，沒有 `showPopup()`；
  正確 API 是 `_showComboMenu()`（**1.11.2 內部 API**，已 hasattr 防衛，升級 qfluentwidgets 時留意）。
- **開檔後屬性面板顯示 (無)**：`_rebuild_ui` 先選場景後才填 combo 選項，`findText` 落空。
  改先 `_sync_asset_lists()` 再 `set_project()`；`set_asset_lists` 改 model-driven 回填防呆。
- **影片解析度被 Windows DPI 放大**：125% 縮放下 `view.grab()` 回傳 1.25× 實體像素
  （選 720p 輸出 1600×900）。`_grab_frame` 後接 `_normalize_frame` 正規化到精確目標尺寸。
- **對話列補齊刪改功能**（原教學宣稱 Delete / Ctrl+C/V 但全不存在；`_on_paste_text` 是死碼）：
  Delete 刪句、雙擊台詞 inline 編輯（依「」規則自動重判 dialogue/narration）、右鍵插入/刪除、
  Ctrl+C 複製、「貼上文字」接回檔案選單（Ctrl+Shift+V），教學文字同步。
  **鐵則照舊：所有列表變更必經 `Scene.insert_dialogue/remove_dialogue`**（segment 自動 shift，有測試守護）。
  inline editor 的提交旗標必須 per-editor（曾因掛在 instance 上造成 stale closure 誤寫，`bc26f89`）。

**誤報澄清**：走查時「淺色主題開檔後左側面板變深」實為截圖假象——背景 transparent 的 widget
單獨 `grab()` 會把透明處渲染成黑；單獨截子面板驗證主題時務必抓整窗對照。

驗證：每項修復先有失敗回歸測試再修（offscreen 全綠 259 passed + 1 skipped）；
另以 `build/uxtest/probe_verify_s0.py` / `probe_verify_s1.py` 在真實 GUI + 真實 MP4 導出端對端複驗。

---

## 程式碼健檢紀錄（2026-06-10，fix/audit-2026-06）

全庫審查後的一次性修正，無新功能：

- **Auto duration 公式跨端對齊（跨端同步）**：engine.js `getAutoDuration` 補上 8 秒上限
  （先前僅 Python 端有 cap，>47 字台詞 Preview 與 MP4 停留時間不一致）。
  Python 端兩份重複公式（exporter_video / webengine_capture）收斂為
  `exporter_video.calc_auto_duration` 單一來源；新增 `tests/test_duration_sync.py`
  以 regex 抽 JS 常數自動守護（仿 test_effects_sync.py 模式）。
- **engine.js hex→rgba 收斂**：刪除 `_hexToRgba`，統一用穩健版 `hexToRgba(hex, alpha, fallbackHex)`；
  對話框 fallback `#141428`、名牌 fallback 鋼藍語意不變。
- **Image.open 全面改 context manager**（exporter_video / image_normalize / image_optimizer）：
  避免異常路徑洩漏檔案 handle（Windows 上會卡住檔案刪除/搬移）。
- **去重**：`_get_assets_source` / `_get_assets_dir` 收斂為 `asset_manager.get_project_assets_dir`；
  兩份 `PRESET_COLORS` 收斂為 `palette.PRESET_NAME_COLORS`。
- **清理**：requirements.txt 移除未使用的 pygame；`tests/assets/`（手動測試產物）加入 .gitignore。
- **test_capture_multi_sprite skip 閘門修正**：原本「Windows 一律跑」沒考慮
  `QT_QPA_PLATFORM=offscreen` 下 QtWebEngine GPU context lost 截出白幀；
  改為 offscreen 一律 skip（除非 VNSTUDIO_E2E=1）。有顯示環境下測試照常執行且通過。
- **刻意不改**：src/ui 各處 `QPushButton` 看似違反「優先用 qfluentwidgets」規範，
  但實際全部依賴 theme.py 的自訂 QSS（`dashedButton` / `hoverDeleteButton` / 色塊按鈕）；
  換成 fluent `PushButton` 會與其內建樣式打架，維持現狀。

驗證：`QT_QPA_PLATFORM=offscreen pytest tests/` → 215 passed + 1 skipped；
有顯示環境下 `pytest tests/test_capture_multi_sprite.py` → passed（E2E 截幀）。

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

---

## Phase 2 紀錄（2026-04-19）

### 目標
把 `src/ui/center_panel.py` 的 `QTableWidget` 對話編輯器替換成 POC 驗證過的三域分離結構
（左卡片列 + 中舞台三 lane + 右特效 timeline），接上 Phase 1 的新 `Scene` API
（`stage_left/center/right`、`effect_tracks`、`insert/remove/move_dialogue`）。

### 拆掉的東西
- `QTableWidget` 整套：`_DraggableTable`、`_MultilineDelegate`、`_IndexDelegate`、
  `_HoverFilter`、`_StageCellWidget`、`_EffectsMenuButton`、`_BatchToolbar`。
- 7 處欄位寫入點（角色 / 服裝 / 差分 / 效果 / 舞台 / 文字 / 批次）全部移除；
  `_refresh_dialogue_table` → 改名公開 API `CenterPanel.refresh()`，MainWindow 四處呼叫同步改。
- 搜尋 / 高亮 / Ctrl+C/V 批次（Phase 5 重新設計）。
- `left_panel.combo_effect` + 對應的 `_on_effect_changed` + `scene.effect` 讀寫
  （場景層級 scene-wide 特效改以 EffectTimeline 拖一條 full-length segment 取代，消除兩個 source of truth）。
- `dialogs.py`：`StageSlotPickerDialog`、`StageBatchDialog`、`BatchAssignDialog` 三 class 刪除；
  對應的 Qt import 一併清理。

### 新結構
```
CenterPanel (QSplitter Vertical)
├─ PreviewWidget (上；既有)
└─ Bottom (QSplitter Vertical)
    ├─ Workspace (QScrollArea + QSplitter Horizontal)
    │    ├─ DialogueColumn   左，拉伸
    │    ├─ StagePanel       中，3 * LANE_WIDTH
    │    └─ EffectTimelineWidget 右，N * LANE_WIDTH
    └─ SegmentEditor（底，固定 ~160px）
```

三域 widget（`src/ui/dialogue_list.py` / `stage_panel.py` / `effect_timeline.py`）
與共用常數（`src/ui/_timeline_shared.py`）由 `experimental/timeline_poc/` 原樣移植，
import 改寫後接 `src/core/models.py` 的正式 dataclass。

`SegmentEditor`（`src/ui/segment_editor.py`）為 inline panel：
- StageSegment 模式：Character / Costume / Sprite 三級聯 ComboBox，
  改 character 會把 costume/sprite cascade reset（POC 沒做這部分）。
- EffectSegment 模式：effect_type ComboBox + params JSON (`QPlainTextEdit`)，
  blur 時嘗試 `json.loads` 寫回，解析失敗保留原值不 emit。

### 跨 domain 同步
- `DialogueColumn.dialogue_moved` → `Scene.move_dialogue(src, dst)` →
  segments 端點自動依 POC 驗證的 pop+insert 語意 shift（Phase 1 已實作）。
- 三 widget 共享游標：`cursor_changed` 互相轉發 + preview goto。
- `segment_changed`：stage / effect 任何 segment 動了 → 重繪三 widget + 預覽 reload + `project_changed`。

### 驗收
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v` → 179 passed（151 Phase 1 + 28 Phase 2）。
- `python main.py` 可開、可拖卡片、可拖 segment、可改 segment payload。

### 給 CODEX / 下一位的備忘
- **MP4 匯出仍壞**：此階段 engine.js 尚讀舊欄位 → fallback 為 null；影片會是空白舞台、
  無特效。Phase 3 的工作是把 `src/engine/engine.js` 與 `src/ui/webengine_capture.py` 全部改用
  `Scene.state_at(dlg_idx)` 查當下狀態。
- `Project.to_script_json()` 目前仍輸出 Phase 1 前的 `characters[].position`（legacy），以及
  `Scene.to_dict()` 輸出新 schema；engine 未消費新欄位 → 預覽呈現不符合預期（已知）。
- `src/ui/webengine_capture.py` 的 `has_effect` 改為 `any(t.segments for t in scene.effect_tracks)`
  以避開 `scene.effect` 屬性（已刪），但語意不精確，Phase 3 隨 engine.js 重寫。
- `Preview.bridge.stage_slot_clicked` signal 保留但無 listener（engine.js 端 hook 未動；
  Phase 3 決定要不要整個拔掉）。
- `tests/conftest.py` 已加全域 session-scoped `qapp` fixture，
  處理 QtWebEngine + qfluentwidgets 的 global singleton 生命週期耦合——
  後續新 Qt widget 測試一律用這個 fixture，不要自己建 QApplication。

### 風險（已驗證 mitigation）
- POC 固定列高 52px：視覺已跑 main.py 確認無擠壓。
- center_panel 重寫 regression：Step 3 單元測試 + 端對端 `MainWindow()` 建構測試護守。
- SegmentEditor cascade race：character 改動時同步 reset costume/sprite，
  `test_changing_stage_character_emits_signal_and_resets_costume` 守護。

---

## Phase 3 紀錄（2026-04-19）

### 目標
讓 `src/engine/engine.js` / `exporter_video.py` / `exporter_html.py` / `webengine_capture.py`
適配 Phase 1 新資料模型（`StageSegment` / `EffectSegment` / `EffectTrack`）；
ADR-003 守護 CAPTURE_MODE 下多立繪渲染；MP4 端到端 live 驗收後可 merge phase-1+2+3。

### 關鍵決策：Python 端預先計算 state（ADR-004）
engine.js 不實作 JS 版 `stateAt`。改為 `Project.to_script_json` 呼叫 `src/core/scene_state.state_at`
把每筆 dialogue 的 `stage{left,center,right}` 與 `active_effects` 攤平後寫入 data.js。

**理由**：
1. 單一 source of truth（Python `state_at`）——不需要 JS/Python parity test。
2. engine.js 邏輯簡化為純讀取，diff 最小化。
3. data.js 略大 ~10-20%，但語義清晰、debug 容易。

輸出 shape（to_script_json 後每筆 dialogue）：
```json
{
  "type": "dialogue", "text": "...", "character": "A", "text_effects": ["bold"],
  "stage": {"left": {"character":"A","costume":"便服","sprite":"微笑"}, "center": null, "right": null},
  "active_effects": [{"effect_type":"rain","params":{"intensity":0.7}}]
}
```

### engine.js 改動
- 刪：`resolveSpriteFile` / `renderLegacySprite` / `setSpritePosition` 三個 legacy 函式
- 刪：`<img id="sprite">` legacy DOM 元素（index.html）
- 刪：`els.sprite` 快取與所有引用
- 改：`showDialogue` 讀 `d.text_effects`（原 d.effects）、`d.stage`（永遠存在，無 hasStage 分支）、`d.active_effects`
- 改：`enterScene` 移除 `VNEffects.setEffect(scene.effect)`；特效切換改由 showDialogue 觸發
- 保留：`refreshStageOverlayButtons(d)` 邏輯不動（d.stage shape 不變）

### effects.js 改動
- 新增 `VNEffects.setActive(activeList)`：分流 canvas 型（rain/snow/crt：互斥）、
  body-class/filter 型（pixel_dark、screen_shake：可疊加）
- `setEffect(name)` 改為 thin wrapper，向下相容但建議不再使用
- 未知 effect_type 僅 `console.warn`，不崩

### style.css 改動
- 新增 `@keyframes vn-screen-shake` + `body.fx-screen_shake #game-container { animation: ... }`
- CAPTURE_MODE 下由既有 `* { animation: none !important }` 抑制（不晃但 class 仍在）
- `pixel_dark` 仍透過 `container.style.filter` 套 brightness（非動畫、capture 下仍生效）

### exporter_video.py (v1 Pillow) 改動
- import `state_at` + `StageSegment`
- `_generate_frames` 對每列呼叫 `state_at(scene, idx)` 取 stage
- 新增 `_lookup_sprite_filename(StageSegment)`：character → costume → expression → filename
- sprite 挑選順序：speaker 對應的 stage 槽 > center > left > right > None（ADR-003 規定 v1 只渲染單張）
- 刪除 Phase 1 留下的 `sprite_path = None` stub

### exporter_html.py 改動
- 移除 lines 170-173 對 `dlg.get("sprite")` 的殘餘讀取（Phase 1 已無此欄位）
- 立繪檔名 → data URI 替換完全由 `characters[].sprites` dict 負責（engine.js 用 label 查）

### webengine_capture.py
- `has_effect` 判定改為 `any(t.segments for t in scene.effect_tracks)`（Phase 2 已改，Phase 3 無需動）
- Preview / Capture 皆透過新 `to_script_json` 消化，engine.js 只讀預計算欄位

### 新測試
- `tests/test_to_script_json_phase3.py`（6 tests）：stage / active_effects 預計算輸出守護
- `tests/test_exporter_video_phase3.py`（5 tests）：`_lookup_sprite_filename` 與 state_at 整合
- `tests/test_capture_multi_sprite.py`：ADR-003 守護，左紅/右藍立繪同幀渲染，
  以 PIL pixel 斷言。預設 skip（`VNSTUDIO_E2E=1` 啟用）；
  MP4 端到端最終由 user 手動跑播放器驗收。

### 驗收
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q` → 195 passed + 1 skipped。
- `VNSTUDIO_E2E=1 ...` → 196 passed（本機驗證 capture 端到端。）
- MP4 live 播放驗收由 user 執行（兩立繪 + rain + screen_shake）——通過後解封 main merge。

### 給 CODEX / 下一位的備忘
- 測試套件預設 skip `test_capture_multi_sprite.py`；設 `VNSTUDIO_E2E=1` 才跑。
  此環境下 capture 路徑以紅/藍色塊驗證左右立繪同時渲染，等同 ADR-003 自動守護。
- 合 main 之前 user 必須跑一次完整 MP4 導出：含多立繪 + rain + screen_shake。
  本 Phase 已確保 Python 端資料攤平與 engine.js / Pillow 端讀取一致，但 MP4 視覺最終責任在人。
- Phase 4+：自訂 effect kinds / 軌道 rename+delete / 同軌多特效疊加 / 焦點保護。

---

## Phase 4-6 Closeout 紀錄（2026-04-19）

重構主線到此完成。task.md / 重構 plan 中原 Phase 4-6 的剩餘工作一次掃乾淨；
本 closeout 無新大型 feature，後續新 feature 可直接從 `main` 開新分支。

### 完成清單

| # | 項目 | 交付 |
|---|---|---|
| 4.1 | 軌道 rename / delete | `feat/effect-track-rename-delete` 已 merge（closeout 前） |
| 4.2 | EffectTrack 顏色 per-track override | 本分支 commit 1 |
| 5.1 | reload_preview 後跳回原 dlg 位置（焦點保護） | 本分支 commit 2 |
| 6.1 | 頭像上 40% × 中 40% 裁切 | `left_panel.py:541-556` 已實作（closeout 前） |
| 6.2 | qfluentwidgets 樣式 review pass | 本分支 Step 3，純 review（見下） |
| 6.3 | 本紀錄 | 本分支 commit 3 |

### Step 1 重點：4.2 EffectTrack 顏色覆寫

- `EffectTrack` 加 `color: str | None`；`to_dict` 僅在有值時輸出、`from_dict` 容忍缺欄
- `_paint_segment` 優先取 `self.track.color`，fallback 到 effect_type 預設
- `_TrackLabel` 新增 `color_requested` signal + 右鍵「設定顏色…」項 +
  `set_accent_color` 在 label 左側畫 4px 豎條反映目前色
- `EffectTimelineHeader` 新 `track_color_changed(name, hex)` + `_on_color_requested`（開 `QColorDialog`）
- `EffectTimelineWidget.set_track_color(name, color|None) -> bool`；no-op / 不存在皆回 False
- `CenterPanel._on_effect_track_color_changed` 串起 widget + label 同步 + 標 dirty

**設計權衡（ADR 補充）：** 角色色（`Character.name_color`）與軌道色（`EffectTrack.color`）同時存在時，
**舞台 segment 仍只用角色色**、**特效 lane 才吃 `track.color`**——避免兩套顏色制度在同一條 lane 打架。

### Step 2 重點：5.1 preview 位置保護

- `CenterPanel._last_preview_pos: tuple[int, int]` 追蹤目前停留位置
- 三處更新點：`_on_cursor_from_widget` / `_on_preview_dialogue_advanced` / `set_current_scene`
- 新 helper `_reload_preview_keep_position`：`reload_preview(project)` 後 `QTimer.singleShot(500ms)` 跳回
- `_on_segment_committed` / `_on_segment_edited` 改走 helper；外部 API
  `CenterPanel.reload_preview(project)` 維持原行為（全新 project 不 keep）

**已知限制：** 500ms 在某些慢機仍可能看到短暫跳首，屬計畫書已文件化的風險條 1。
自動化測試因 webengine timing 難寫，採手動驗收：「拖 segment 端點 → release 後預覽仍停原處」。

### Step 3 重點：6.2 qfluentwidgets 樣式 review pass（純 review，0 改動）

**Review 方法：** 靜態掃所有 `src/ui/*.py` 的 hardcoded hex 顏色；
分類「dark 專用硬編」vs「強調色 light/dark 皆可」；
計畫書 3.4 指明「保守 = 只記錄不修，避免變大重構」，本 phase 不改碼。

**已知 follow-up（light 主題下不一致）：**

| 位置 | 硬編色 | light 主題風險 |
|---|---|---|
| `src/ui/segment_editor.py:56` | popup `#2D2D30` + `#3D8AC4` 邊 | 深底突兀 |
| `src/ui/segment_editor.py:106-121` | ToolButton / placeholder `#9AA0A6` | 灰字對比低 |
| `src/ui/effect_timeline.py:421` | `_TrackLabel` bg `#252526` | 深色列頭 |
| `src/ui/effect_timeline.py:455` | 新增軌道 `+` btn `#3D3D40` | 同上 |
| `src/ui/center_panel.py:211` | 對話 header `#252526` | 深底 |
| `src/ui/stage_panel.py:437` | 舞台 header `#252526` | 深底 |
| `src/ui/dialogue_list.py:106` | 卡片底 `#2D2D30` / `#2E3440` | 深底 |
| `src/ui/_timeline_shared.py` | `BG_DARK` / `BG_PANEL` / `GRID_LINE` | 時間軸 canvas 深底 |

**不算破綻（light/dark 皆可辨識）：** `CURSOR_LINE #FFB300`、`DROP_INDICATOR #00B7C3`、
segment 上白字 `#FFFFFF`、`character_color` / `effect_color` 使用者強調色。

**建議未來補做：** 在 `_timeline_shared.py` 加 `set_theme_mode(mode)` + 兩組色（dark/light），
各 widget 從 shared 讀而非硬編；約 1-2 工作天。本 phase 刻意不做，以免變大重構。

### 排除（明確 future work，非 bug）

- EffectSegment payload editor 改 known-kinds form（目前 JSON 夠用、engine.js 未消化大部分 params）
- RemovalReport pattern（UI 無「刪除單一對話」入口，無從觸發）
- Multi-effect 同 lane 疊加（設計決定互斥；要疊加就開多條軌道）
- UI 全面 light/dark theme-aware（Step 3 列表的 follow-up）

### 測試結果

- Step 1 後 `QT_QPA_PLATFORM=offscreen pytest tests/ -q` → 210 passed + 1 skipped（+7 新測試）
- Step 2 後同指令 → 210 passed + 1 skipped（無新自動測試，手動驗收）
- 完整 closeout 後 → 210 passed + 1 skipped

### 給下一位的備忘

- 重構主線到此告一段落。後續新 feature 直接在 `main` 開新分支（`feat/xxx`）。
- `experimental/timeline_poc/` / `experimental/phase3_mp4_verify/` 是歷史 fixture，
  動 `engine.js` / `exporter_video.py` / `webengine_capture.py` 時建議手動跑一次做目視驗收。
- Step 3 列的 light-mode follow-up 若使用者要求淺色主題完整支援，優先從 `_timeline_shared.py`
  抽 theme 常數開始；否則保持現狀，屬深色主題下的實用工具。

---

## feature/episodes-and-character-reuse：作品/影片兩層結構與跨作品角色復用（2026-06）

### 背景與決策（ADR）

- 需求根源：系列創作者每支影片重設角色/素材。原候選方案「角色卡庫管理器」
  （見已取代的 plans/2026-06-11-character-card-ux.md）被否決——卡片只解決角色、
  且庫會堆積舊版本。
- 決策 1：一個專案 = 一個作品；Project 與 Scene 之間插入 Episode（影片）層，
  角色/素材/設定屬作品層全影片共用，每支影片獨立導出 MP4。層級固定兩層；
  不預留分組欄位——from_dict 忽略未知 key，未來要加時一行即可、舊檔免遷移（YAGNI）。
- 決策 2：`Project.scenes` 改為 property 指向 active episode 的場景
  （getter + setter；setter 支援場景拖曳排序的整列賦值）。center_panel /
  exporter_video / webengine_capture / to_script_json 等所有舊取用點因此零修改，
  engine.js 完全不動。
- 決策 3：跨作品復用 =「從其他作品匯入角色」（直接唯讀對方 .vnsproj + 複製立繪，
  內容相同去重、同名檔加後綴、同名角色詢問取代/略過）。使用者語彙不出現「卡」。
  character_library.py（.vncard）保留為休眠分享格式後端，UI 入口已移除，測試照跑。

### 存檔格式 v2

- 頂層 `version: 2` + `episodes: [{name, scenes}]` + `active_episode_index`，
  不再有頂層 `scenes`。v1 舊檔由 `Project.from_dict` 自動包成單影片作品，
  存檔即升級 v2（不可逆，UI 暫無降版需求）。

### UI 漸進揭露

- 單支影片時介面與改版前完全相同；「檔案 > 新增影片」為常駐入口。
- 第二支影片出現後，左側場景頁頂部顯示影片切換列（ComboBox + ＋ + ⋯選單）。
- 刪除影片有確認（列出場景/對話數，註明角色素材不受影響）；最後一支不可刪。

### 一併修復（2026-06-11 新手走查陷阱）

- 服裝編輯器零服裝時按「新增差分」/拖圖自動建「服裝1」（原本靜默無反應）。
- 移除含差分的服裝先確認。
- 編輯多服裝角色時對話框顯示「N 套服裝、M 張差分」摘要（原本其餘資料隱形）。
- CharacterEditorDialog 的「從角色卡匯入/儲存為角色卡」按鈕與流程移除。

### 給接手者的備忘

- 新功能取場景一律走 `project.scenes`（active episode）；要跨影片枚舉時
  明確寫 `for ep in project.episodes: ep.scenes`，不要假設單影片。
- 所有導出（MP4 / ZIP / HTML）與預覽皆為「目前影片」範圍，不是全作品（刻意，與 WYSIWYG 一致）。
- `_update_status` 的統計目前是「目前影片」的數字，不是全作品總和（刻意）。
- `copy_file_dedup` 以整檔 bytes 相等判定重用；立繪經 normalize 後為
  1080×1440 PNG，比較成本可接受。

