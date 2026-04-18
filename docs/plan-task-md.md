# VisualNovel Studio · task.md 實作計畫書

> 交付對象：其他 AI 實施、CODEX 驗證
> 產出日期：2026-04-18
> 主分支：`main` · 每個 Phase 開一支 `feature/xxx` 分支，PR 前先跑 `pytest tests/`
> 配套文件：[DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md)（開發歷程，每 Phase 結束需追加）

---

## Context（為什麼要做這些改動）

[task.md](../task.md) 集結了近期使用者在 UI / 角色管理 / 對話表格 / 預覽介面上累積的痛點。核心問題有三類：

1. **UI 呈現不夠專業**：字框寬度溢出、工具列按鈕與快捷鍵重疊、淺色模式預覽仍為深色、介面字體固定、標點與字體沒完全在地化。
2. **編輯動線阻力高**：新增角色被強迫處理差分、服裝無預設名、編完角色面板自動跳走、名色選擇器過度複雜、舞台欄資訊密度低、拖曳位置難判斷。
3. **缺少跨專案資產復用**：角色卡無法跨專案共享，每個新專案都要重建。

預期成果：讓創作者能像編輯 Word 一樣直覺地匯入文字、選角、上舞台、即時預覽，並保留下來的角色資產能跨作品復用。

---

## 實作總覽（6 個 Phase）

| Phase | 主題 | 風險 | 預計分支 |
|---|---|---|---|
| A | 基礎修正（重命名、預設值、文字解析） | 低 | `feature/task-a-basics` |
| B | 工具列與預覽介面重構 | 中 | `feature/task-b-toolbar-preview` |
| C | 角色管理重構 + 角色卡 | 中 | `feature/task-c-character-mgmt` |
| D | 對話欄位升級（效果、舞台、拖曳） | 高 | `feature/task-d-dialogue` |
| E | 字框自動寬度 + 字體大小 | 中 | `feature/task-e-dialogue-box` |
| F | 場景背景修復 + LOG 除錯 | 低 | `feature/task-f-polish` |

---

## Phase A｜基礎修正

### A1. 全專案把「表情」改名為「差分」
- **檔案**：[src/ui/dialogs.py](../src/ui/dialogs.py)、[src/ui/center_panel.py](../src/ui/center_panel.py)、[src/ui/left_panel.py](../src/ui/left_panel.py)、[src/core/models.py](../src/core/models.py)（註解）
- **動作**：字串全域替換 `表情` → `差分`。資料欄位名保留 `expressions`（內部變數不改）。
- **驗證**：`pytest tests/`；目視確認 3 個 dialog 與主視窗無殘留。

### A2. 語系與字體統一
- **檔案**：[src/engine/style.css:17](../src/engine/style.css#L17)（已使用 Microsoft JhengHei，確認 fallback 順序）；[src/ui/theme.py](../src/ui/theme.py)（PyQt 端補 `font-family: "Microsoft JhengHei"`）
- **動作**：確保 Engine CSS 與 PyQt QSS 主字體皆為「Microsoft JhengHei」；所有 UI 文字改用全形標點（`:` → `：`、`,` → `，`）。
- **驗證**：啟動 `python main.py`，擷圖主視窗 + 預覽，確認字體一致；用 Grep 列出 `src/ui/*.py` 中仍存在的半形標點。

### A3. 場景／服裝預設名稱
- **檔案**：[src/ui/left_panel.py:464-471](../src/ui/left_panel.py#L464-L471)（新場景）、[src/ui/dialogs.py:701-706](../src/ui/dialogs.py#L701-L706)（新服裝）
- **動作**：
  - 新增場景時 `scene.name = f"場景{len(project.scenes)+1}"`（若模型無 name 欄則沿用 id → label 顯示）
  - 新增服裝時 `costume.name = f"服裝{len(character.costumes)+1}"`
  - 兩者都允許於屬性面板雙擊重新命名。
- **驗證**：`pytest tests/test_models.py -v`；UI 操作新增 3 次場景 / 服裝，確認自動遞增命名。

### A4. 對話列表 → 文字列表
- **檔案**：[src/ui/center_panel.py:254](../src/ui/center_panel.py#L254)
- **動作**：表格 header 第 2 欄改為「文字」，下方分頁 label 改為「文字列表」。
- **驗證**：UI 擷圖對比前後。

### A5. 文字解析規則調整
- **檔案**：[src/core/text_parser.py:51-53](../src/core/text_parser.py#L51-L53)
- **現行規則**：整行以「開頭、」結尾 → dialogue。
- **新規則**：
  - 整行以「開頭、」結尾 → `type="dialogue"`，`character="(未選取)"`（字串常量定義於 models）
  - 其他 → `type="narration"`，`character=None`
  - 「」內容保留顯示（不剝掉）
- **驗證**：擴充 `tests/test_text_parser.py` 加入 3 個案例（「…」、夾雜、純旁白），全綠。

### A6. 移除「螢幕位置」屬性
- **檔案**：[src/ui/dialogs.py](../src/ui/dialogs.py)（CharacterEditorDialog）、[src/core/models.py](../src/core/models.py)
- **動作**：Editor UI 移除 position 控件；`Character.position` 欄位保留為 legacy（只在 `from_dict` 讀，不寫入 `to_dict` 新專案），engine.js legacy fallback 仍能用。
- **驗證**：存檔 → 重開 → 確認舊檔仍可載入；新建角色 `.vnsproj` 不含 `position` 欄。

### A7. 介面字體大小 14–32px（預設 18）
- **檔案**：[src/ui/main_window.py:110-116](../src/ui/main_window.py#L110-L116)、[src/ui/theme.py](../src/ui/theme.py)
- **動作**：Menu 的選項清單改為 14/16/18/20/22/24/28/32，預設值改 18；`theme.py` QSS 模板的 `{font_size}` 沿用。
- **驗證**：切換每個選項確認生效並能儲存 preference。

---

## Phase B｜工具列與預覽介面重構

### B1. 移除工具列「設定」項
- **檔案**：[src/ui/main_window.py:98-116](../src/ui/main_window.py#L98-L116)（MenuBar 或 ToolBar 處）
- **動作**：刪除「設定」menu/button；其快捷鍵若有則釋放。
- **驗證**：視窗頂部目視確認；搜尋 `"設定"` 剩餘位置。

### B2. 工具列文字與快捷鍵 / 下拉選單重疊修正
- **檔案**：[src/ui/main_window.py](../src/ui/main_window.py) MenuBar 的 QAction（若為 CommandBar 則調整 style）
- **動作**：確認每個 QAction 的 `text()` 與 `shortcut()` 不共用同一標籤；必要時把快捷鍵移入 `setShortcut()` 而非寫進 text。
- **驗證**：每個選單展開擷圖，對齊無重疊。

### B3. 刪除「遊戲設定」按鈕，改成預覽上方即時控件
- **檔案**：[src/ui/center_panel.py:319-327](../src/ui/center_panel.py#L319-L327)（preview_toolbar）、移除 [main_window.py:165](../src/ui/main_window.py#L165) 的 `_on_game_settings` 連接、移除 `dialogs.py::GameSettingsDialog` 的觸發
- **動作**：
  - 工具列改成：`[重新整理]  [字體大小: 18 ▼]  [字框透明度: ■■■□]  [名牌字體: 20 ▼]`（都即時套 game_settings 並 refresh preview）
  - 使用 qfluentwidgets 的 `ComboBox` / `Slider`
- **驗證**：拖動滑桿、切字體 → 預覽立即反映。

### B4. 淺色模式下預覽介面也為淺色
- **檔案**：[src/engine/style.css](../src/engine/style.css)、[src/ui/preview_widget.py](../src/ui/preview_widget.py)
- **動作**：
  - `<body>` 新增 class：`preview-light` / `preview-dark`
  - `preview_widget.py` 依目前 theme 在載入時注入 class（與 `VN_CAPTURE_MODE` 注入同機制）
  - CSS 定義淺色版的 `#game-container` 背景 `#f5f5f7`，字框 `rgba(255,255,255,0.9)` + 深色字
- **驗證**：切換深／淺主題 → 預覽隨動。

### B5. 預覽初始比例：高度 = 可用區域 50%
- **檔案**：[src/ui/center_panel.py](../src/ui/center_panel.py)（splitter 垂直分割處）
- **動作**：中央面板垂直 splitter 預設 `setSizes([50%, 50%])`（上 = 預覽、下 = 文字列表）；LetterboxContainer 已處理 16:9，無需動。
- **驗證**：重開軟體時量測預覽高度 ≈ 視窗高的 50%。

### B6. 選取角色按鈕移至預覽高度 50%、永遠顯示
- **檔案**：[src/engine/engine.js:431-493](../src/engine/engine.js#L431-L493)（setupStageOverlay）、[style.css:98-153](../src/engine/style.css#L98-L153)（.slot-control）
- **動作**：
  - `.slot-control` CSS 改 `top: 50%; transform: translateY(-50%)`
  - 有角色時仍顯示 `▼` 選單按鈕（點擊出現角色列表讓使用者換角色）
  - Preview 模式才顯示（CAPTURE_MODE 保持隱藏）
- **驗證**：預覽介面有角色 / 無角色兩種狀態下皆可見按鈕，點擊彈出 picker。

### B7. 角色名牌：半透明背景 + 長度貼合文字
- **檔案**：[src/engine/style.css:184-195](../src/engine/style.css#L184-L195)
- **動作**：`background: rgba(<name_color>, 0.6)` + `display: inline-block` + `padding: 4px 14px`；engine.js 動態把 name_color 轉 rgba（helper `hexToRgba`）。
- **驗證**：長短名字各測一次，背景寬度貼合。

---

## Phase C｜角色管理重構

### C1. 新增角色只加一張預設立繪（無差分）
- **檔案**：[src/ui/dialogs.py:348-597](../src/ui/dialogs.py#L348-L597) CharacterEditorDialog
- **動作**：
  - 新增模式下移除差分區塊，只留「立繪圖片」dropzone
  - 提交時自動包 `Costume(name="預設", expressions=[SpriteVariant("預設", <file>)])`
  - 編輯模式（改既有角色）保留差分 UI
- **驗證**：新增流程擷圖；確認 `.vnsproj` 中 `costumes[0].expressions` 長度為 1。

### C2. 新增角色 dialog 內能上傳圖片
- **檔案**：[src/ui/dialogs.py](../src/ui/dialogs.py) CharacterEditorDialog
- **動作**：新增 dropzone 接受拖曳 + 點擊上傳；上傳後檔案複製至 project assets，UI 顯示縮圖。沿用 CostumeEditorDialog 既有拖曳實作。
- **驗證**：新增角色 → 上傳 png → 保存 → 重開確認縮圖仍在。

### C3. 圖片與檔名分離（雙擊重新命名）
- **檔案**：[src/core/models.py](../src/core/models.py) SpriteVariant（已分 `label` / `filename`）、[src/ui/dialogs.py](../src/ui/dialogs.py) 立繪列表 QTreeWidget
- **動作**：
  - `SpriteVariant.label` 預設 = 檔名 (stem)
  - QTreeWidget 設 `setEditTriggers(DoubleClicked | EditKeyPressed)`，只允許編輯 label column
  - 編完 emit `dataChanged` → 更新 model
- **驗證**：雙擊標籤 → 輸入 → Enter 儲存；點擊他處 → focus out 儲存。

### C4. 屬性面板不回跳場景
- **檔案**：[src/ui/left_panel.py:306-320](../src/ui/left_panel.py#L306-L320) SegmentedWidget + Inspector QStackedWidget
- **動作**：
  - 追蹤使用者最後選擇的 tab（`self._last_inspector_tab`）
  - 關閉 CharacterEditorDialog 後，不強制切回場景 tab
  - 若目前在角色 tab 且選中的角色被編輯，停留在角色 tab
- **驗證**：編 A 角色 → 關閉對話 → Inspector 仍顯示 A 角色屬性。

### C5. 名字顏色：預設色盤取代自由選色
- **檔案**：[src/ui/dialogs.py](../src/ui/dialogs.py) 名色欄位
- **動作**：
  - 改為 6–8 顆預設色按鈕：`#000000 黑`、`#FFFFFF 白`、`#D32F2F 紅`、`#1976D2 藍`、`#388E3C 綠`、`#F57C00 橘`、`#7B1FA2 紫`、`#FBC02D 黃`
  - 每顆色按鈕外有對比邊框，確保淺／深主題下皆可見
  - 儲存時寫入 `Character.name_color`
- **驗證**：每顆色都能套用；切主題後按鈕仍可辨識。

### C6. 角色卡跨專案共享
- **檔案（新增）**：[src/core/character_library.py](../src/core/character_library.py)
- **動作**：
  - 儲存位置：`Path.home() / ".vnstudio" / "character_cards"`（Windows `%USERPROFILE%\.vnstudio\character_cards`）
  - 每張卡為一個 zip：`{character_name}.vncard` 內含 `character.json` + 立繪圖片
  - UI：CharacterEditorDialog 右上增「儲存為角色卡 / 從角色卡匯入」按鈕
  - API：`save_card(character, assets_dir) -> Path`、`load_card(path) -> tuple[Character, list[Path]]`、`list_cards() -> list[Path]`
- **驗證**：
  - `tests/test_character_library.py` 測 save → list → load 迴圈
  - 手動在 A 專案儲卡 → 開 B 專案匯入 → 確認立繪檔案複製到 B 的 assets。

---

## Phase D｜對話欄位升級

### D1. 效果欄改下拉多選
- **檔案**：[src/ui/center_panel.py:497-529](../src/ui/center_panel.py#L497-L529)、[src/engine/engine.js:250-258](../src/engine/engine.js#L250-L258)
- **選項**：`無`（預設）、`粗體`、`斜體`、`底線`、`刪除線`、`顫抖`、`閃爍`、`漸變`
- **動作**：
  - Python：CheckableComboBox（qfluentwidgets）儲存 `list[str]`（鍵：`bold/italic/underline/strike/shake/blink/gradient`）
  - JS 新增 runtime effect：`shake`（CSS keyframes translate）、`blink`（opacity keyframes）、`gradient`（background-clip: text + linear-gradient）
  - 同步 Python ↔ JS 命名常量（新增 [src/core/effects.py](../src/core/effects.py) + JS 對應 `TEXT_EFFECTS`，雙端各自維護，以註解互相標註）
- **驗證**：
  - `tests/test_effects_sync.py` 斷言兩側常量一致
  - 預覽每種效果肉眼可見

### D2. 說話角色 vs 畫面角色分離（UI 呈現）
- **現狀**：資料模型已分離（`Dialogue.character` + `Dialogue.stage`），但表格中「角色」欄同時是說話者。
- **動作**：
  - 保留「說話角色」欄（決定名牌）
  - 舞台欄改大（D3）負責畫面角色
  - Inspector 文案明確寫「說話角色決定名牌，舞台決定畫面」
- **驗證**：對話列中只選說話角色、舞台留空 → 預覽有名牌無立繪；反之亦然。

### D3. 舞台欄大改：左中右獨立 + 可選服裝
- **檔案**：[src/ui/center_panel.py:501-510](../src/ui/center_panel.py#L501-L510)
- **動作**：
  - 舞台欄拆成三個子 cell（L / C / R），每個 cell 顯示縮圖 + 角色名 + 服裝名
  - 點擊 cell → 彈出 StageSlotPicker dialog：選角色 → 選服裝 → 選差分（皆有預設首項）
  - 空 cell 顯示 ＋ 圖示
- **驗證**：左右各放不同角色 → 預覽三槽正確。

### D4. 欄位背景 = 角色顏色
- **檔案**：[src/ui/center_panel.py](../src/ui/center_panel.py)（QTableWidget item delegate）
- **動作**：
  - 實作 `CharacterColorDelegate`：讀取該 row 說話角色的 `name_color`，繪製半透明背景（alpha 0.25）
  - 文字顏色用 `contrast_text(color)` helper（深色底白字、淺色底黑字，YIQ 公式）
- **驗證**：淺／深主題下皆可閱讀。

### D5. 拖曳放置線視覺
- **檔案**：[src/ui/center_panel.py:135-177](../src/ui/center_panel.py#L135-L177) `_DraggableTable`
- **動作**：
  - 覆寫 `dragMoveEvent` 計算目標列 index，呼叫 `setDropIndicatorShown(True)`
  - 自訂 paintEvent 繪製「上下移開 + 中線」效果（插入點在兩列之間時，把目標列 + 下一列各推開 8px，中線畫 2px 加亮）
  - drop 時送 `row_moved(from, to)` 已有
- **驗證**：拖曳 3 次，放置位置視覺與實際結果一致。

### D6. 更靈活的結構探索（先做研究，產 POC，再決定）
- **動作**：
  - 研究 alternative：
    - `QListView` + custom delegate（每列獨立 widget card）
    - `QTreeView` with flat model（可折疊場景）
    - scroll area + Qt widgets 自製卡片列表
  - 產一個 250 行內的 POC 分支 `spike/dialogue-card-view`，寫短報告放入 `docs/dialogue-view-spike.md`，列優缺點
  - 使用者決定後再合併
- **驗證**：POC 可展示、report 可讀、與使用者對齊後再進入 D3~D5 正式實作（D3~D5 也可以用現有 QTableWidget 先實作）

---

## Phase E｜字框自動寬度與字體大小

### E1. 字框寬度隨文字長度自動調整
- **檔案**：[src/engine/style.css:172-204](../src/engine/style.css#L172-L204)、[src/engine/engine.js](../src/engine/engine.js) renderDialogue
- **動作**：
  - 改 `#dialogue-box` 為 `width: max-content; max-width: calc(100% - 64px); min-width: 240px`
  - 保持水平置中：`left: 50%; transform: translateX(-50%)`
  - 內距 `padding: 16px 24px`
  - 換行啟用 `word-wrap: break-word`
- **驗證**：短台詞（3 字）、長台詞（100 字）各測；不超過容器寬。

### E2. 字體大小 14–32px，預設 18
- **檔案**：[src/engine/engine.js:151-152](../src/engine/engine.js#L151-L152)、工具列控件（B3）
- **動作**：
  - `game_settings.dialogue_font_size` clamp 至 [14, 32]；default 18
  - B3 的工具列下拉選項：14 / 16 / 18 / 20 / 24 / 28 / 32
- **驗證**：調整下拉每檔都可套。

---

## Phase F｜場景背景修復 + LOG 除錯

### F1. 場景背景不顯示於預覽
- **檔案**：[src/engine/engine.js:192-213](../src/engine/engine.js#L192-L213) enterScene、[src/ui/preview_widget.py](../src/ui/preview_widget.py)
- **動作**：
  - Log 當前 `ASSETS_DIR` 與 `scene.background` 的完整 URL
  - 檢查 `QUrl.fromLocalFile()` 是否在 Windows 下編碼空白路徑 `%20` 造成找不到（常見兇手）
  - 若是 → helper `path_to_file_url(p)` 統一轉碼
- **驗證**：`d:\VisualNovel Studio` 路徑有空白，匯入背景後預覽立即顯示。

### F2. LOG 全面檢查
- **動作**：
  - 啟動 `python main.py` 並在終端觀察 stderr
  - 在 QWebEngineView 啟用 DevTools 或 attach `QWebEngineSettings::JavascriptConsoleLogged`
  - 修掉所有出現的 Warning / Error（紀錄至 DEVELOPMENT_HISTORY.md）
- **驗證**：啟動 → 導入範例專案 → 操作每個 Phase 功能 → 觀察 log 清空。

---

## 關鍵檔案索引（待修改）

| 檔案 | 主要 Phase |
|---|---|
| [src/core/models.py](../src/core/models.py) | A, C, D |
| [src/core/text_parser.py](../src/core/text_parser.py) | A |
| [src/core/project_io.py](../src/core/project_io.py) | C |
| [src/core/character_library.py](../src/core/character_library.py)（新） | C |
| [src/core/effects.py](../src/core/effects.py)（新） | D |
| [src/ui/main_window.py](../src/ui/main_window.py) | A, B |
| [src/ui/left_panel.py](../src/ui/left_panel.py) | A, C |
| [src/ui/center_panel.py](../src/ui/center_panel.py) | A, B, D |
| [src/ui/preview_widget.py](../src/ui/preview_widget.py) | B |
| [src/ui/dialogs.py](../src/ui/dialogs.py) | A, C, D |
| [src/ui/theme.py](../src/ui/theme.py) | A, B |
| [src/engine/engine.js](../src/engine/engine.js) | B, D, E, F |
| [src/engine/style.css](../src/engine/style.css) | B, E |
| [src/engine/effects.js](../src/engine/effects.js) | D |

---

## 跨端同步公式表（實施者必讀）

| 主題 | Python 位置 | JS 位置 | 備註 |
|---|---|---|---|
| Auto 延遲 | [exporter_video.py::_calc_duration](../src/core/exporter_video.py) | [engine.js::getAutoDuration](../src/engine/engine.js) | 改一端必改另一端 |
| 文字效果鍵 | `src/core/effects.py::TEXT_EFFECTS`（Phase D 新增） | `src/engine/engine.js::TEXT_EFFECTS` | 字串鍵需字面一致 |
| 場景特效鍵 | Scene.effect | effects.js applyEffect | rain/snow/crt/pixel_dark |

---

## 驗證方式（CODEX 通用清單）

每個 Phase 合併前，CODEX 需執行：

```bash
# 1. 測試全綠
pytest tests/ -v

# 2. 啟動煙霧測試
python main.py  # 確認無 crash

# 3. 核對 DEVELOPMENT_HISTORY.md 已追加本 Phase 區段

# 4. 目視驗收（依該 Phase 驗證小節）
```

**End-to-End 驗收**（整體完成後）：
1. 匯入 `.txt` 小說（含「」對話與旁白）
2. 建 2 位角色（一張預設立繪即可），儲成角色卡
3. 開新專案 → 從角色卡匯入 → 確認立繪跟來
4. 分配舞台（左中右各放角色），加文字效果（粗體 + 顫抖）
5. 切淺色主題 → 預覽跟著變淺色
6. 工具列調字體大小 → 預覽即時變
7. 拖曳一列對話到新位置 → 放置線可見
8. 導出 MP4 → 檢查效果與立繪完整呈現（CAPTURE_MODE 不顯示 overlay）

---

## 開放問題（實施前應先問使用者確認）

1. **角色卡儲存位置**：預設 `~/.vnstudio/character_cards/`，使用者是否要改別處？
2. **「漸變」效果定義**：是指文字顏色漸層（背景漸變 + background-clip: text），還是淡入／淡出？本計畫暫採前者。
3. **Phase D6「更靈活結構」**：先做 spike 再決定要不要全面替換 QTableWidget，使用者是否同意？
4. **工具列控件順序**：B3 建議 `[重新整理] [字體大小] [透明度] [名牌字體]`，是否有偏好？
5. **預設色盤**：C5 列 8 色是否足夠？要不要加灰階？
