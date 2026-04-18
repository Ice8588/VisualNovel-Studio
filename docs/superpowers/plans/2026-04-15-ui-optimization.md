# VisualNovel Studio UI 優化實作計劃

> **給執行 AI：** 建議使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 逐 task 執行。所有步驟使用 checkbox (`- [ ]`) 語法。每個 Phase 對應一個獨立分支，完成後合併到 `main` 前必須跑 `pytest tests/` 全過（專案規則，見 CLAUDE.md）。

**Goal:** 修復 VNStudio UI 的視覺正確性 bug、整理資訊架構、補齊空狀態引導，提升整體使用者體驗。

**Architecture:** 分 5 個獨立 Phase，每個 Phase 一個 feature 分支。Phase 之間無相依性，可平行或依序進行。主要修改集中在 `src/ui/theme.py`、`src/ui/main_window.py`、`src/ui/left_panel.py`、`src/ui/center_panel.py`，不動 `src/core/`、`src/engine/`。

**Tech Stack:** PyQt6、qfluentwidgets、pytest。

---

## 專案背景（執行前必讀）

1. **三層架構：** `src/ui/` = PyQt6 桌面 GUI、`src/engine/` = HTML5 播放引擎、`src/core/` = 核心邏輯。本計劃只動 `src/ui/`。
2. **主題系統：** `src/ui/theme.py` 用 `QSettings` 持久化偏好（深/淺色 × 字體大小）。`apply_theme()` 同時套用 qfluentwidgets 的 Theme 與一套原生 Qt 元件的 stylesheet override。Stylesheet template 用 `.format(font_size=...)` 注入字體大小。
3. **元件庫：** 優先用 `qfluentwidgets`（`ComboBox`、`LineEdit`、`PushButton`、`ListWidget`、`SegmentedWidget`），非 qfluentwidgets 的原生元件靠 `theme.py` 的 stylesheet 補樣式。
4. **分支規則：** 從 `main` 開分支 → 做 Phase → `pytest tests/` 全過 → 合回 `main`。**不可 skip 測試**。
5. **回應語言：** commit message、對話框文字一律**繁體中文**。

## 執行前的狀態檢查

- [ ] **0.1：確認在乾淨的 `main` 分支**

```bash
git status
git branch --show-current
```

Expected: `working tree clean`、`main`。若有 uncommitted changes，先 stash 或 commit 再開始。

- [ ] **0.2：基準線測試通過**

```bash
pytest tests/ -q
```

Expected: 全部 PASS。若有 fail，先排除再開始計劃（與本計劃無關的 flaky test 要記錄下來）。

- [ ] **0.3：手動啟動確認目前 UI 行為**

```bash
python main.py
```

肉眼確認：視窗開啟、可切換深/淺色主題、可新增場景。關閉視窗即可。

---

## Phase 1：視覺正確性修復（P0 bugs）

**分支：** `fix/ui-theme-correctness`
**問題：** 淺色主題下多個 ComboBox 與虛線按鈕仍顯示深色硬編碼值；QFont fallback 鏈失效。
**驗證策略：** `theme.py` 的 QFont 修復可寫 unit test；ComboBox/虛線按鈕是純 UI，以手動切換主題肉眼驗證為主。

### Task 1.0：建立分支

- [ ] **Step 1：開分支**

```bash
git checkout -b fix/ui-theme-correctness
```

### Task 1.1：修正 `QFont` fallback 鏈

**問題：** `src/ui/theme.py:410` 把 `"Microsoft JhengHei, Noto Sans TC, sans-serif"` 整個字串當成單一 family 傳給 `QFont()`。PyQt6 的 `QFont(family: str)` 只接受**一個** family 名稱，逗號不會被解析為 fallback 鏈。正確做法是 `setFamilies(list[str])`。

**Files:**
- Modify: `src/ui/theme.py:410`
- Test: `tests/test_theme.py`（新建）

- [ ] **Step 1：寫 failing test**

建立 `tests/test_theme.py`：

```python
"""theme 模組測試。"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_apply_theme_uses_font_families_fallback(qapp):
    """apply_theme 套用的字體必須有多個 family（fallback 鏈），而不是單一逗號字串。"""
    from src.ui.theme import apply_theme

    apply_theme(qapp, "dark", 14)
    font = qapp.font()
    families = font.families()

    # 必須是列表且至少包含主字體
    assert len(families) >= 2, f"期望有 fallback 字體，實際: {families}"
    assert "Microsoft JhengHei" in families
    assert "Noto Sans TC" in families
    # 不可有逗號混進 family 名稱
    for fam in families:
        assert "," not in fam, f"family 名稱含逗號（fallback 未拆）: {fam!r}"
```

- [ ] **Step 2：跑測試確認失敗**

```bash
pytest tests/test_theme.py -v
```

Expected: FAIL（當前實作 `families()` 會回傳單一含逗號的字串）。

- [ ] **Step 3：修正 `theme.py`**

修改 `src/ui/theme.py` 的 `apply_theme` 函式，找到這段：

```python
    font = QFont("Microsoft JhengHei, Noto Sans TC, sans-serif")
    font.setPixelSize(font_size)
    app.setFont(font)
```

替換為：

```python
    font = QFont()
    font.setFamilies(["Microsoft JhengHei", "Noto Sans TC", "sans-serif"])
    font.setPixelSize(font_size)
    app.setFont(font)
```

- [ ] **Step 4：跑測試確認通過**

```bash
pytest tests/test_theme.py -v
```

Expected: PASS。

- [ ] **Step 5：跑全套測試確認無回歸**

```bash
pytest tests/ -q
```

Expected: 全部 PASS。

- [ ] **Step 6：commit**

```bash
git add tests/test_theme.py src/ui/theme.py
git commit -m "fix(theme): 修正 QFont fallback 鏈無效問題

QFont(str) 只接受單一 family 名稱，逗號不會被解析為
fallback。改用 setFamilies([...]) 才能讓缺字時正確退回
Noto Sans TC / sans-serif。"
```

### Task 1.2：主題感知的表格 ComboBox 樣式

**問題：** `src/ui/center_panel.py:32-39` 的 `_COMBO_STYLE` 使用 `#2a2a2a`、`#1e1e1e`、`#555` 等深色值，切到淺色主題時對話表格的角色/服裝/表情 ComboBox 會在白底上顯示黑色下拉框，視覺斷裂。

**方案：** 把 `_COMBO_STYLE` 從 `center_panel.py` 移除，改為在 `theme.py` 依主題生成對應的 stylesheet，附加到既有 `_DARK_OVERRIDES` / `_LIGHT_OVERRIDES` template 尾端。`center_panel.py` 只給 ComboBox 加一個 `objectName`（或 class property），由 global stylesheet 選取。

**Files:**
- Modify: `src/ui/theme.py`（`_DARK_OVERRIDES`、`_LIGHT_OVERRIDES` 尾端補規則）
- Modify: `src/ui/center_panel.py:32-39, 434, 451, 464`（拿掉 `_COMBO_STYLE`，改 `setObjectName("tableCombo")`）

- [ ] **Step 1：在 `theme.py` 的 `_DARK_OVERRIDES` 字串常量尾端（`"""` 之前）新增規則**

找到 `_DARK_OVERRIDES` 字串的最後一個 `}}` 之後、結尾 `"""` 之前，加入：

```css
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 1px 4px;
    color: #ddd;
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: #2a2a2a;
    border: 1px solid #555;
    border-radius: 3px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #555;
    selection-background-color: #4682B4;
    outline: none;
}}
```

- [ ] **Step 2：在 `theme.py` 的 `_LIGHT_OVERRIDES` 字串常量尾端同位置加入對應淺色版本**

```css
QComboBox#tableCombo {{
    background: transparent;
    border: none;
    padding: 1px 4px;
    color: #333;
}}
QComboBox#tableCombo:hover, QComboBox#tableCombo:focus {{
    background-color: #f0f0f0;
    border: 1px solid #bbb;
    border-radius: 3px;
}}
QComboBox#tableCombo::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#tableCombo QAbstractItemView {{
    background-color: #fff;
    color: #333;
    border: 1px solid #ccc;
    selection-background-color: #4682B4;
    selection-color: #fff;
    outline: none;
}}
```

- [ ] **Step 3：移除 `center_panel.py` 的 `_COMBO_STYLE` 常量**

刪除 `src/ui/center_panel.py:31-39` 這段：

```python
# 半透明 ComboBox：平時低調，hover/focus 顯示邊框
_COMBO_STYLE = (
    "QComboBox{border:none;background:transparent;padding:1px 4px;}"
    "QComboBox:hover,QComboBox:focus{"
    "border:1px solid #555;background:#2a2a2a;border-radius:3px;}"
    "QComboBox::drop-down{border:none;width:14px;}"
    "QComboBox QAbstractItemView{border:1px solid #555;background:#1e1e1e;"
    "selection-background-color:#0057b8;outline:none;}"
)
```

- [ ] **Step 4：把三處 `setStyleSheet(_COMBO_STYLE)` 改為 `setObjectName("tableCombo")`**

在 `center_panel.py` 中，替換以下三處：

`center_panel.py:434` 附近：
```python
char_combo = QComboBox()
char_combo.setStyleSheet(_COMBO_STYLE)
```
改為：
```python
char_combo = QComboBox()
char_combo.setObjectName("tableCombo")
```

`center_panel.py:451` 附近：
```python
costume_combo = QComboBox()
costume_combo.setStyleSheet(_COMBO_STYLE)
```
改為：
```python
costume_combo = QComboBox()
costume_combo.setObjectName("tableCombo")
```

`center_panel.py:464` 附近：
```python
sprite_combo = QComboBox()
sprite_combo.setStyleSheet(_COMBO_STYLE)
```
改為：
```python
sprite_combo = QComboBox()
sprite_combo.setObjectName("tableCombo")
```

- [ ] **Step 5：手動驗證**

```bash
python main.py
```

肉眼檢查清單：
1. 預設深色主題下，開啟/匯入一個有角色的專案（或新增場景 + 角色 + 一條對話），表格中角色/服裝/表情 ComboBox 外觀與修改前一致（透明背景、hover 顯示邊框）。
2. 選單 → 外觀 → 主題 → 淺色，切換後：表格中的 ComboBox **背景不再是深色黑塊**，文字為深色、背景為透明/白色。
3. Hover 狀態在兩種主題下都有可見邊框。

- [ ] **Step 6：跑測試確認無回歸**

```bash
pytest tests/ -q
```

Expected: 全部 PASS。

- [ ] **Step 7：commit**

```bash
git add src/ui/theme.py src/ui/center_panel.py
git commit -m "fix(ui): 對話表格 ComboBox 主題感知

原本 _COMBO_STYLE 寫死深色值，淺色主題下會出現黑色下拉
塊。移到 theme.py 的 overrides 依主題生成，ComboBox 靠
objectName='tableCombo' 被選取。"
```

### Task 1.3：虛線按鈕與 hover 刪除鍵主題化

**問題：** `src/ui/left_panel.py:68-72` 的 `_btn_del` 與 `:99-103` 的 `_DASHED_BTN_STYLE` 寫死灰階顏色（`#888`、`#555`、`#e05555`），淺色主題下虛線框與 × 幾乎看不見。

**方案：** 把兩個 stylesheet 從 `left_panel.py` 移到 `theme.py`，靠 `objectName`（`"dashedButton"`、`"hoverDeleteButton"`）在兩種主題下各給一版。

**Files:**
- Modify: `src/ui/theme.py`（兩個 overrides 字串尾端各加規則）
- Modify: `src/ui/left_panel.py`（拿掉 `_DASHED_BTN_STYLE`、`_btn_del` 的 inline stylesheet，改 `setObjectName`）

- [ ] **Step 1：在 `theme.py` 的 `_DARK_OVERRIDES` 尾端新增**

```css
QPushButton#dashedButton {{
    border: 2px dashed #555;
    border-radius: 4px;
    color: #888;
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: #888;
    color: #bbb;
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: #888;
    background: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: #e05555;
}}
```

- [ ] **Step 2：在 `theme.py` 的 `_LIGHT_OVERRIDES` 尾端新增**

```css
QPushButton#dashedButton {{
    border: 2px dashed #bbb;
    border-radius: 4px;
    color: #888;
    background: transparent;
    padding: 4px;
}}
QPushButton#dashedButton:hover {{
    border-color: #666;
    color: #333;
}}
QPushButton#hoverDeleteButton {{
    border: none;
    color: #999;
    background: transparent;
    font-size: 13px;
    font-weight: bold;
    padding: 0;
}}
QPushButton#hoverDeleteButton:hover {{
    color: #c43434;
}}
```

- [ ] **Step 3：修改 `left_panel.py` 的 `_HoverDeleteItemWidget.__init__`**

找到 `src/ui/left_panel.py:66-74`：

```python
self._btn_del = QPushButton("×")
self._btn_del.setFixedSize(18, 18)
self._btn_del.setStyleSheet(
    "QPushButton{border:none;color:#888;background:transparent;"
    "font-size:13px;font-weight:bold;padding:0;}"
    "QPushButton:hover{color:#e05555;}"
)
self._btn_del.hide()
self._btn_del.clicked.connect(self.delete_clicked)
```

替換為：

```python
self._btn_del = QPushButton("×")
self._btn_del.setObjectName("hoverDeleteButton")
self._btn_del.setFixedSize(18, 18)
self._btn_del.hide()
self._btn_del.clicked.connect(self.delete_clicked)
```

- [ ] **Step 4：拿掉 `_DASHED_BTN_STYLE` 常量並更新所有用到的地方**

刪除 `src/ui/left_panel.py:99-103`：

```python
_DASHED_BTN_STYLE = (
    "QPushButton{border:2px dashed #555;border-radius:4px;color:#888;"
    "background:transparent;padding:4px;}"
    "QPushButton:hover{border-color:#888;color:#bbb;}"
)
```

然後搜尋檔內所有 `setStyleSheet(_DASHED_BTN_STYLE)`（至少三處：新增場景按鈕、新增角色按鈕、編輯服裝按鈕），全部替換為 `setObjectName("dashedButton")`：

例如 `left_panel.py:165` 附近：
```python
self.btn_add_scene = QPushButton("+ 新增場景")
self.btn_add_scene.setStyleSheet(_DASHED_BTN_STYLE)
```
改為：
```python
self.btn_add_scene = QPushButton("+ 新增場景")
self.btn_add_scene.setObjectName("dashedButton")
```

同理改 `btn_add_char`（`left_panel.py:179` 附近）與 `btn_edit_costume`（`left_panel.py:267` 附近）。

- [ ] **Step 5：手動驗證**

```bash
python main.py
```

肉眼檢查：
1. 深色主題：新增場景／新增角色／編輯服裝按鈕有虛線邊框，hover 變亮。
2. 淺色主題：虛線邊框為淺灰 `#bbb`，hover 變深；**不再看不見**。
3. Hover 場景/角色 list item 時 × 出現；深色為灰→hover 紅；淺色為中灰→hover 深紅。

- [ ] **Step 6：跑測試**

```bash
pytest tests/ -q
```

Expected: 全部 PASS。

- [ ] **Step 7：commit**

```bash
git add src/ui/theme.py src/ui/left_panel.py
git commit -m "fix(ui): 虛線按鈕與 hover 刪除鍵主題化

原本 stylesheet 寫在 left_panel.py 並寫死深色灰階，淺色
主題下虛線框與 × 幾乎看不見。移到 theme.py overrides，
以 objectName（dashedButton/hoverDeleteButton）選取，各
主題給不同對比度。"
```

### Task 1.4：合併 Phase 1 到 `main`

- [ ] **Step 1：最終驗證**

```bash
pytest tests/ -q
python main.py  # 手動切兩次主題確認沒 regression
```

- [ ] **Step 2：合併**

```bash
git checkout main
git merge --no-ff fix/ui-theme-correctness -m "Merge fix/ui-theme-correctness"
```

- [ ] **Step 3：清理分支**

```bash
git branch -d fix/ui-theme-correctness
```

---

## Phase 2：選單與工具列整理（P1）

**分支：** `refactor/menu-toolbar`
**問題：**
1. 「預覽」頂層選單只有 1 個項目（重新整理預覽），與中央面板「重新整理」按鈕重複。
2. `main_window.py:133-136` 建立了空的 `QToolBar`，佔空間沒內容。
3. 「重新整理預覽」沒有快捷鍵。

**方案：** 刪除「預覽」選單、把「重新整理預覽 (F5)」合併到「檔案」選單尾端、**直接移除**空的 QToolBar（若日後要放工具列再另行規劃）。

### Task 2.0：建立分支

- [ ] **Step 1：從 main 開分支**

```bash
git checkout main
git checkout -b refactor/menu-toolbar
```

### Task 2.1：移除「預覽」選單、把重新整理合到「檔案」並補 F5 快捷鍵

**Files:**
- Modify: `src/ui/main_window.py:69-131`（`_setup_menu`）

- [ ] **Step 1：修改 `_setup_menu` 的「檔案」選單，在「結束」之前插入「重新整理預覽」**

找到 `src/ui/main_window.py` 中的檔案選單段落（約 `:73-85`）：

```python
file_menu = menu_bar.addMenu("檔案")
act_new = file_menu.addAction("新增專案", self._on_new_project)
act_new.setShortcut(QKeySequence.StandardKey.New)
act_open = file_menu.addAction("開啟專案", self._on_open_project)
act_open.setShortcut(QKeySequence.StandardKey.Open)
file_menu.addSeparator()
act_save = file_menu.addAction("儲存專案", self._on_save_project)
act_save.setShortcut(QKeySequence.StandardKey.Save)
file_menu.addAction("另存專案", self._on_save_project_as)
file_menu.addSeparator()
file_menu.addAction("匯入文字", self._on_import_text)
file_menu.addSeparator()
file_menu.addAction("結束", self.close)
```

在「匯入文字」與最後一個 `addSeparator()` 之間插入重新整理動作：

```python
file_menu = menu_bar.addMenu("檔案")
act_new = file_menu.addAction("新增專案", self._on_new_project)
act_new.setShortcut(QKeySequence.StandardKey.New)
act_open = file_menu.addAction("開啟專案", self._on_open_project)
act_open.setShortcut(QKeySequence.StandardKey.Open)
file_menu.addSeparator()
act_save = file_menu.addAction("儲存專案", self._on_save_project)
act_save.setShortcut(QKeySequence.StandardKey.Save)
file_menu.addAction("另存專案", self._on_save_project_as)
file_menu.addSeparator()
file_menu.addAction("匯入文字", self._on_import_text)
file_menu.addSeparator()
act_refresh = file_menu.addAction("重新整理預覽", self._on_refresh_preview)
act_refresh.setShortcut(QKeySequence("F5"))
file_menu.addSeparator()
file_menu.addAction("結束", self.close)
```

- [ ] **Step 2：刪除原本獨立的「預覽」選單段**

找到並刪除 `main_window.py:87-89`（或附近）：

```python
# 預覽選單
preview_menu = menu_bar.addMenu("預覽")
preview_menu.addAction("重新整理預覽", self._on_refresh_preview)
```

- [ ] **Step 3：手動驗證**

```bash
python main.py
```

肉眼檢查：
1. 選單列只剩 5 個頂層：檔案、導出、外觀、設定、說明（沒有「預覽」）。
2. 檔案選單最下方有「重新整理預覽 F5」。
3. 按 F5 觸發重新整理（引擎會重新載入，可由 console 日誌或畫面短暫閃爍確認）。

- [ ] **Step 4：commit**

```bash
git add src/ui/main_window.py
git commit -m "refactor(menu): 合併預覽選單到檔案選單並補 F5 快捷鍵

原「預覽」頂層選單只有 1 項且與中央面板按鈕重複，合到
檔案選單尾端並加上 F5 快捷鍵。"
```

### Task 2.2：移除空的 QToolBar

**問題：** `main_window.py:133-136` 建立了沒有任何 action 的工具列，佔掉一列高度。

**Files:**
- Modify: `src/ui/main_window.py:42, 133-136`

- [ ] **Step 1：刪除 `_setup_toolbar` 方法**

找到並刪除 `src/ui/main_window.py` 中的這段：

```python
    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("工具列")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
```

- [ ] **Step 2：從 `__init__` 移除 `_setup_toolbar` 呼叫**

找到 `src/ui/main_window.py:42`：

```python
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._connect_signals()
```

刪掉 `self._setup_toolbar()` 那行：

```python
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
```

- [ ] **Step 3：清掉未用的 import**

檢查 `src/ui/main_window.py:8-18`，若 `QToolBar` 已沒人用（只有被刪除的方法用），從 import 列表移除：

```python
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QSplitter,
    QToolBar,   # ← 刪這行
)
```

- [ ] **Step 4：手動驗證**

```bash
python main.py
```

肉眼：主視窗選單列底下**沒有**一列空白工具列，中央 splitter 直接接選單列。

- [ ] **Step 5：跑測試**

```bash
pytest tests/ -q
```

Expected: 全部 PASS。

- [ ] **Step 6：commit**

```bash
git add src/ui/main_window.py
git commit -m "refactor(ui): 移除未使用的空 QToolBar

建立後沒加任何 action，只是占掉一列高度。"
```

### Task 2.3：合併 Phase 2 到 `main`

- [ ] **Step 1：驗證**

```bash
pytest tests/ -q
python main.py
```

- [ ] **Step 2：合併**

```bash
git checkout main
git merge --no-ff refactor/menu-toolbar -m "Merge refactor/menu-toolbar"
git branch -d refactor/menu-toolbar
```

---

## Phase 3：空狀態 Onboarding（P1）

**分支：** `feat/empty-state-onboarding`
**問題：** 首次啟動 `python main.py` 時 `Project()` 是空的，左側場景列表空白、中央預覽黑畫面、屬性面板只寫「選擇場景或角色以查看屬性」。新使用者不知道下一步。

**方案：** 在 `CenterPanel` 的預覽容器內，當 `project.scenes == []` 時覆蓋顯示一個 hero 區塊：標題「開始你的第一個故事」+ 兩個大 CTA 按鈕（「匯入文字檔…」「新增第一個場景」）。`preview_widget` 照常在底下，但被覆蓋。非空時隱藏。

### Task 3.0：建立分支

- [ ] **Step 1：開分支**

```bash
git checkout main
git checkout -b feat/empty-state-onboarding
```

### Task 3.1：新增 `EmptyStateWidget` 元件

**Files:**
- Create: `src/ui/empty_state.py`

- [ ] **Step 1：建立 `src/ui/empty_state.py`**

```python
"""空狀態引導元件：首次啟動或空專案時顯示。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PrimaryPushButton, PushButton


class EmptyStateWidget(QWidget):
    """空專案時在預覽區域顯示的引導畫面。

    提供兩個入口：匯入文字檔、新增第一個場景。
    """

    import_text_clicked = pyqtSignal()
    add_scene_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        title = QLabel("開始你的第一個故事")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("匯入 .txt / .docx 文字檔，或手動新增場景")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)

        layout.addSpacing(8)

        btn_import = PrimaryPushButton("匯入文字檔…")
        btn_import.setFixedWidth(200)
        btn_import.clicked.connect(self.import_text_clicked)
        layout.addWidget(btn_import, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_add = PushButton("新增第一個場景")
        btn_add.setFixedWidth(200)
        btn_add.clicked.connect(self.add_scene_clicked)
        layout.addWidget(btn_add, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
```

- [ ] **Step 2：sanity-check import 可用**

```bash
python -c "from src.ui.empty_state import EmptyStateWidget; print('ok')"
```

Expected: `ok`。

- [ ] **Step 3：commit**

```bash
git add src/ui/empty_state.py
git commit -m "feat(ui): 新增 EmptyStateWidget 空狀態引導元件

提供兩個 CTA：匯入文字檔、新增第一個場景。"
```

### Task 3.2：整合到 `CenterPanel` 的預覽容器

**Files:**
- Modify: `src/ui/center_panel.py`（預覽容器改 `QStackedWidget`，加入 EmptyState，在 `set_project` / `set_current_scene` / `_refresh_dialogue_table` 時切換顯示）
- Modify: `src/ui/main_window.py`（接 EmptyState 的兩個 signal）

- [ ] **Step 1：在 `center_panel.py` import EmptyStateWidget 並新增 signal**

在 `src/ui/center_panel.py` 檔首 import 區：

```python
from src.ui.preview_widget import PreviewWidget
```

下方補一行：

```python
from src.ui.empty_state import EmptyStateWidget
```

在 `CenterPanel` 的 signal 宣告區（約 `center_panel.py:190`）：

```python
class CenterPanel(QWidget):
    """預覽 + 對話表格，支援行內編輯、搜尋、批次操作。"""

    project_changed = pyqtSignal()
```

下方補兩個 signal：

```python
class CenterPanel(QWidget):
    """預覽 + 對話表格，支援行內編輯、搜尋、批次操作。"""

    project_changed = pyqtSignal()
    empty_state_import_text = pyqtSignal()
    empty_state_add_scene = pyqtSignal()
```

- [ ] **Step 2：把預覽容器改成 `QStackedWidget`**

從 Qt 匯入列（`center_panel.py:7-22`）確保 `QStackedWidget` 被 import：

```python
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QSplitter,
    QStackedWidget,
    QStyledItemDelegate,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
```

找到 `_setup_ui` 中建立預覽容器的段落（約 `center_panel.py:318-334`）：

```python
        # 預覽容器：工具列 + 預覽元件
        preview_container = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(2)

        preview_toolbar = QHBoxLayout()
        preview_toolbar.addStretch()
        self.btn_refresh_preview = PushButton("重新整理")
        self.btn_game_settings = PushButton("遊戲設定")
        self.btn_refresh_preview.setFixedHeight(24)
        self.btn_game_settings.setFixedHeight(24)
        preview_toolbar.addWidget(self.btn_refresh_preview)
        preview_toolbar.addWidget(self.btn_game_settings)
        preview_layout.addLayout(preview_toolbar)
        preview_layout.addWidget(self.preview)
        preview_container.setLayout(preview_layout)
```

改為：

```python
        # 預覽容器：工具列 + Stacked（EmptyState / 預覽）
        preview_container = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(2)

        preview_toolbar = QHBoxLayout()
        preview_toolbar.addStretch()
        self.btn_refresh_preview = PushButton("重新整理")
        self.btn_game_settings = PushButton("遊戲設定")
        self.btn_refresh_preview.setFixedHeight(24)
        self.btn_game_settings.setFixedHeight(24)
        preview_toolbar.addWidget(self.btn_refresh_preview)
        preview_toolbar.addWidget(self.btn_game_settings)
        preview_layout.addLayout(preview_toolbar)

        self._preview_stack = QStackedWidget()
        self._empty_state = EmptyStateWidget()
        self._empty_state.import_text_clicked.connect(self.empty_state_import_text)
        self._empty_state.add_scene_clicked.connect(self.empty_state_add_scene)
        self._preview_stack.addWidget(self._empty_state)   # index 0
        self._preview_stack.addWidget(self.preview)         # index 1
        preview_layout.addWidget(self._preview_stack)
        preview_container.setLayout(preview_layout)
```

- [ ] **Step 3：新增 `_update_empty_state` 方法並在三處呼叫**

在 `CenterPanel` 類別內（建議放在 `set_project` 之後）新增：

```python
    def _update_empty_state(self) -> None:
        """根據 project 是否有場景，切換 EmptyState / 預覽。"""
        has_scenes = bool(self._project and self._project.scenes)
        self._preview_stack.setCurrentIndex(1 if has_scenes else 0)
```

修改 `set_project`（約 `center_panel.py:366-370`）：

```python
    def set_project(self, project: Project) -> None:
        """綁定 Project。"""
        self._project = project
        self._current_scene_index = 0 if project.scenes else -1
        self._refresh_dialogue_table()
        self._update_empty_state()
```

修改 `set_current_scene`（約 `center_panel.py:372-375`）：

```python
    def set_current_scene(self, index: int) -> None:
        """外部切換場景時呼叫。"""
        self._current_scene_index = index
        self._refresh_dialogue_table()
        self._update_empty_state()
```

在 `add_dialogues_to_current_scene` 中，於 `self._refresh_dialogue_table()` 與 `self.project_changed.emit()` 之間插入 `self._update_empty_state()`：

```python
            self._refresh_dialogue_table()
            self._update_empty_state()
            self.project_changed.emit()
```

- [ ] **Step 4：在 `main_window.py` 接兩個 signal**

找到 `src/ui/main_window.py` 的 `_connect_signals`（約 `:138-166`），在 `# 中央面板 → 內容變更` 區塊附近加入：

```python
        # 中央面板 → 內容變更
        self.center_panel.project_changed.connect(self._on_project_changed)

        # 空狀態 CTA
        self.center_panel.empty_state_import_text.connect(self._on_import_text)
        self.center_panel.empty_state_add_scene.connect(self._on_empty_add_scene)
```

然後在 `MainWindow` 類別內新增處理方法（建議放在 `_on_scene_selected` 附近）：

```python
    def _on_empty_add_scene(self) -> None:
        """空狀態引導：新增第一個場景。"""
        scene_id = self._project.next_scene_id()
        self._project.scenes.append(Scene(id=scene_id))
        self.left_panel.refresh_scenes()
        self.left_panel.scene_list.setCurrentRow(0)
        self._on_project_changed()
```

- [ ] **Step 5：手動驗證**

```bash
python main.py
```

檢查清單：
1. **首次啟動**：中央預覽區域顯示「開始你的第一個故事」標題與兩個按鈕（無預覽畫面）。
2. 點「匯入文字檔…」→ 開啟文字檔案選擇對話框（等同檔案選單的「匯入文字」）。
3. 點「新增第一個場景」→ 左側場景列表出現 `scene_001`，中央區域切換為預覽畫面，空狀態消失。
4. 匯入一段有對話的文字檔 → 場景建立，中央切換為預覽。
5. 移除所有場景 → 中央重新顯示空狀態。
6. 深色/淺色主題切換正常。

- [ ] **Step 6：跑測試**

```bash
pytest tests/ -q
```

Expected: 全部 PASS。

- [ ] **Step 7：commit**

```bash
git add src/ui/center_panel.py src/ui/main_window.py
git commit -m "feat(ui): 空專案顯示 onboarding hero 引導

原本首次啟動是黑預覽 + 空列表，新使用者無下一步線索。
用 QStackedWidget 切換 EmptyStateWidget 與預覽，CTA 連
到匯入文字 / 新增場景。"
```

### Task 3.3：合併 Phase 3 到 `main`

- [ ] **Step 1：驗證**

```bash
pytest tests/ -q
python main.py
```

- [ ] **Step 2：合併**

```bash
git checkout main
git merge --no-ff feat/empty-state-onboarding -m "Merge feat/empty-state-onboarding"
git branch -d feat/empty-state-onboarding
```

---

## Phase 4：元件一致性與小 UX 細節（P2）

**分支：** `polish/widget-consistency`
**問題：**
1. `Character.position` 欄位在 UI 上仍可編輯，但 CLAUDE.md 明確說它是 legacy 欄位，新路徑（有 stage）不使用。使用者會誤以為調它會影響畫面。
2. 角色屬性面板的色塊 `_lbl_char_color` 不可點，旁邊的「選色」按鈕才是。
3. Splitter handle 預設 4px 太窄，不好抓。
4. 對話表格「舞台」欄只有 90px，顯示 `L● C● R●` 有點擠。

### Task 4.0：建立分支

- [ ] **Step 1：開分支**

```bash
git checkout main
git checkout -b polish/widget-consistency
```

### Task 4.1：為 legacy `Character.position` 欄位加 tooltip 說明

**問題：** 完全隱藏這個欄位會破壞舊專案向下相容性，但保留原樣又會誤導使用者。折衷方案是加 tooltip 註明。

**Files:**
- Modify: `src/ui/left_panel.py`（`_setup_ui` 中角色屬性面板的位置 row）

- [ ] **Step 1：在 `_combo_char_pos` 建立後加 tooltip**

找到 `src/ui/left_panel.py:254-260`：

```python
        # 位置
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("位置:"))
        self._combo_char_pos = ComboBox()
        self._combo_char_pos.addItems(_POS_OPTIONS)
        pos_row.addWidget(self._combo_char_pos, 1)
        char_props_layout.addLayout(pos_row)
```

改為：

```python
        # 位置（legacy：僅在未使用舞台槽位時生效）
        pos_row = QHBoxLayout()
        pos_label = QLabel("位置:")
        pos_label.setToolTip(
            "舊版欄位：僅對未設定「舞台槽位」的對話生效。\n"
            "建議直接在對話列的「舞台」欄指定角色位置。"
        )
        pos_row.addWidget(pos_label)
        self._combo_char_pos = ComboBox()
        self._combo_char_pos.addItems(_POS_OPTIONS)
        self._combo_char_pos.setToolTip(
            "舊版欄位：僅對未設定「舞台槽位」的對話生效。\n"
            "建議直接在對話列的「舞台」欄指定角色位置。"
        )
        pos_row.addWidget(self._combo_char_pos, 1)
        char_props_layout.addLayout(pos_row)
```

- [ ] **Step 2：手動驗證**

```bash
python main.py
```

檢查：選到任一角色，hover「位置:」或下拉框 1 秒 → 出現 tooltip 說明「舊版欄位…」。

- [ ] **Step 3：commit**

```bash
git add src/ui/left_panel.py
git commit -m "polish(ui): 角色位置欄位補 tooltip 說明 legacy 語意

避免使用者誤以為調整此欄會影響新路徑（有 stage）的畫面。"
```

### Task 4.2：色塊可點觸發選色

**Files:**
- Modify: `src/ui/left_panel.py`（`_lbl_char_color` 建立處 + `mousePressEvent` 事件）

- [ ] **Step 1：把 `_lbl_char_color` 從 `QLabel` 改成可點的自訂 widget**

找到 `src/ui/left_panel.py:245-253`：

```python
        # 顏色
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("顏色:"))
        self._lbl_char_color = QLabel()
        self._lbl_char_color.setFixedSize(20, 20)
        self._btn_char_color = PushButton("選色")
        self._btn_char_color.setFixedWidth(50)
        color_row.addWidget(self._lbl_char_color)
        color_row.addWidget(self._btn_char_color)
        color_row.addStretch()
        char_props_layout.addLayout(color_row)
```

改為：

```python
        # 顏色（色塊本身也可點）
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("顏色:"))
        self._lbl_char_color = QLabel()
        self._lbl_char_color.setFixedSize(20, 20)
        self._lbl_char_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lbl_char_color.setToolTip("點擊以修改顏色")
        self._lbl_char_color.mousePressEvent = self._on_color_label_clicked
        self._btn_char_color = PushButton("選色")
        self._btn_char_color.setFixedWidth(50)
        color_row.addWidget(self._lbl_char_color)
        color_row.addWidget(self._btn_char_color)
        color_row.addStretch()
        char_props_layout.addLayout(color_row)
```

- [ ] **Step 2：新增 `_on_color_label_clicked` 方法**

在 `LeftPanel` 類別內，在 `_on_char_color_btn` 附近新增：

```python
    def _on_color_label_clicked(self, event) -> None:
        """色塊點擊：與按鈕行為相同。"""
        self._on_char_color_btn()
```

- [ ] **Step 3：手動驗證**

`python main.py` → 選角色 → 移動到色塊上方應出現「點擊以修改顏色」tooltip 與手指游標 → 點擊開啟 QColorDialog。

- [ ] **Step 4：commit**

```bash
git add src/ui/left_panel.py
git commit -m "polish(ui): 角色顏色色塊可點擊觸發選色"
```

### Task 4.3：Splitter handle 加寬並加 hover 色

**Files:**
- Modify: `src/ui/main_window.py`（中央 splitter）
- Modify: `src/ui/left_panel.py`（左側垂直 splitter）
- Modify: `src/ui/center_panel.py`（中央垂直 splitter）
- Modify: `src/ui/theme.py`（hover 色 via stylesheet）

- [ ] **Step 1：`main_window.py:49` 附近**

找到：
```python
        splitter = QSplitter(Qt.Orientation.Horizontal)
```
下方新增：
```python
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
```

- [ ] **Step 2：`left_panel.py:139` 附近的垂直 splitter 加同樣設定**

```python
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)
```

- [ ] **Step 3：`center_panel.py:206` 附近**

```python
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)
```

- [ ] **Step 4：`theme.py` 的兩個 overrides 補 hover 規則**

在 `_DARK_OVERRIDES` 尾端新增：

```css
QSplitter::handle:hover {{
    background-color: #4682B4;
}}
```

在 `_LIGHT_OVERRIDES` 尾端新增：

```css
QSplitter::handle:hover {{
    background-color: #4682B4;
}}
```

- [ ] **Step 5：手動驗證**

`python main.py`：拖動左右中央分隔條容易抓住（6px），滑鼠移上變藍。

- [ ] **Step 6：commit**

```bash
git add src/ui/main_window.py src/ui/left_panel.py src/ui/center_panel.py src/ui/theme.py
git commit -m "polish(ui): splitter handle 加寬至 6px 並補 hover 色"
```

### Task 4.4：拉寬對話表格「舞台」欄

**Files:**
- Modify: `src/ui/center_panel.py:277`

- [ ] **Step 1：修改欄寬**

找到 `src/ui/center_panel.py:277`：

```python
        self.dialogue_table.setColumnWidth(6, 90)
```

改為：

```python
        self.dialogue_table.setColumnWidth(6, 120)
```

- [ ] **Step 2：手動驗證**

`python main.py` → 匯入文字 → 看舞台欄寬度足夠顯示 `L● C● R●` 不擠。

- [ ] **Step 3：commit**

```bash
git add src/ui/center_panel.py
git commit -m "polish(ui): 對話表格舞台欄拉寬至 120px"
```

### Task 4.5：合併 Phase 4

- [ ] **Step 1：驗證**

```bash
pytest tests/ -q
python main.py
```

- [ ] **Step 2：合併**

```bash
git checkout main
git merge --no-ff polish/widget-consistency -m "Merge polish/widget-consistency"
git branch -d polish/widget-consistency
```

---

## Phase 5：狀態列（P3，可選）

**分支：** `feat/status-bar`
**問題：** 沒有狀態列，使用者無法一眼看到專案統計（場景數、對話數、估計時長、FFmpeg 狀態）。

### Task 5.0：建立分支

- [ ] **Step 1：開分支**

```bash
git checkout main
git checkout -b feat/status-bar
```

### Task 5.1：新增狀態列顯示專案統計

**Files:**
- Modify: `src/ui/main_window.py`（新增 `QStatusBar`，於 `_on_project_changed`、`_rebuild_ui` 更新）

- [ ] **Step 1：import `QStatusBar`**

修改 `src/ui/main_window.py:8-18` 的 import：

```python
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QSplitter,
    QStatusBar,
)
```

- [ ] **Step 2：在 `__init__` 設定狀態列**

在 `MainWindow.__init__` 尾端（`self._connect_signals()` 之後）新增：

```python
        self._setup_status_bar()
        self._update_status()
```

- [ ] **Step 3：新增 `_setup_status_bar` 與 `_update_status` 方法**

在 `MainWindow` 類別內新增（建議放在 `_update_title` 附近）：

```python
    def _setup_status_bar(self) -> None:
        self._status_bar = QStatusBar()
        self._lbl_stats = QLabel("")
        self._status_bar.addWidget(self._lbl_stats)
        self.setStatusBar(self._status_bar)

    def _update_status(self) -> None:
        """更新狀態列統計：場景數、對話數、估計總時長。"""
        if not self._project:
            self._lbl_stats.setText("")
            return
        scene_count = len(self._project.scenes)
        dlg_count = sum(len(s.dialogues) for s in self._project.scenes)
        # 使用與 engine.js / exporter_video.py 一致的估計公式（上限 8 秒）
        total_sec = 0.0
        for s in self._project.scenes:
            for d in s.dialogues:
                total_sec += max(1.5, min(1.0 + len(d.text) * 0.15, 8.0))
        minutes = int(total_sec // 60)
        seconds = int(total_sec % 60)
        self._lbl_stats.setText(
            f"場景 {scene_count} 個  │  對話 {dlg_count} 句  │  "
            f"估計時長 {minutes}:{seconds:02d}"
        )
```

- [ ] **Step 4：在 `_on_project_changed` 與 `_rebuild_ui` 尾端加上 `_update_status()` 呼叫**

找到 `main_window.py` 中的 `_on_project_changed`：

```python
    def _on_project_changed(self) -> None:
        self._dirty = True
        self._update_title()
        self._on_refresh_preview()
```

改為：

```python
    def _on_project_changed(self) -> None:
        self._dirty = True
        self._update_title()
        self._update_status()
        self._on_refresh_preview()
```

找到 `_rebuild_ui`：

```python
    def _rebuild_ui(self) -> None:
        self.left_panel.set_project(self._project)
        self.center_panel.set_project(self._project)
        self._sync_asset_lists()
        self._on_refresh_preview()
        self._update_title()
```

改為：

```python
    def _rebuild_ui(self) -> None:
        self.left_panel.set_project(self._project)
        self.center_panel.set_project(self._project)
        self._sync_asset_lists()
        self._on_refresh_preview()
        self._update_title()
        self._update_status()
```

- [ ] **Step 5：手動驗證**

```bash
python main.py
```

- 首次啟動：視窗底部狀態列顯示「場景 0 個 │ 對話 0 句 │ 估計時長 0:00」。
- 匯入文字後數字更新。
- 新增/刪除場景時立即更新。
- 切換主題不影響狀態列字體。

- [ ] **Step 6：跑測試**

```bash
pytest tests/ -q
```

- [ ] **Step 7：commit**

```bash
git add src/ui/main_window.py
git commit -m "feat(ui): 狀態列顯示場景數、對話數與估計時長

時長公式與 engine.js / exporter_video.py 保持一致
（每句 max(1.5, min(1.0 + len*0.15, 8.0)) 秒）。"
```

### Task 5.2：合併 Phase 5

- [ ] **Step 1：驗證**

```bash
pytest tests/ -q
python main.py
```

- [ ] **Step 2：合併**

```bash
git checkout main
git merge --no-ff feat/status-bar -m "Merge feat/status-bar"
git branch -d feat/status-bar
```

---

## 全計劃完成檢查表

- [ ] `fix/ui-theme-correctness` 已合併
- [ ] `refactor/menu-toolbar` 已合併
- [ ] `feat/empty-state-onboarding` 已合併
- [ ] `polish/widget-consistency` 已合併
- [ ] `feat/status-bar` 已合併（或視需求跳過）
- [ ] `main` 上 `pytest tests/` 全過
- [ ] `main` 上 `python main.py` 可正常啟動，兩種主題切換無視覺問題
- [ ] 空專案顯示 onboarding 引導
- [ ] 狀態列數字正確（若 Phase 5 完成）

---

## 注意事項

1. **同步規則：** Phase 5 的時長公式必須與 `src/engine/engine.js` 的 `getAutoDuration()` 和 `src/core/exporter_video.py` 的 `_calc_duration()` 一致（見 CLAUDE.md「關鍵同步規則」）。若公式調整請同步三處。
2. **qfluentwidgets 元件不受原生 stylesheet 影響**：Phase 1 的 stylesheet 只會作用在原生 Qt 元件（`QPushButton`、`QComboBox`），qfluentwidgets 的 `PushButton`、`ComboBox` 已有自己的主題系統。別把原生 stylesheet 套到 qfluentwidgets 元件上。
3. **commit message 一律繁體中文**（使用者偏好，見 memory）。
4. **每個 Phase 合併前必須 `pytest tests/` 全過**（專案規則，見 CLAUDE.md）。
5. **不要動** `src/core/`、`src/engine/`、`tests/test_exporter*.py`、`tests/test_webengine_capture.py`。本計劃純 UI 層改動。
