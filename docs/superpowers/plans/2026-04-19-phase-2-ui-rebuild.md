# Phase 2 — UI 重建：QTableWidget → 三域分離 (POC port)

> **給驗證 AI（codex）：** 本文件為 Phase 2 的完整 spec，可獨立讀懂。
> 上游：`feature/phase-1-data-model` (commit `d3f03c1`)。
> 本 Phase 分支：`feature/phase-2-ui`，從 `feature/phase-1-data-model` branch off。
> **不 merge to main**——等 Phase 3 一起合（CLAUDE.md：MP4 是核心優先級，Phase 3 才把 engine.js 接回；中途上 main 會壞 MP4 匯出）。

---

## Goal（一句話）

把 `src/ui/center_panel.py` 的 `QTableWidget` 對話編輯器替換成 `experimental/timeline_poc/` 已驗證的三域結構（左卡片列 + 中舞台三 lane + 右特效 timeline），接上 Phase 1 的新 `Scene` API（`stage_left/center/right`、`effect_tracks`、`insert/remove/move_dialogue`），讓 `python main.py` 能跑、能編輯。

## 不在 Phase 2 範圍（明確排除）

| 項目 | 為何排除 | 哪個 Phase |
|---|---|---|
| `src/engine/engine.js` 改寫 | 跨域，獨立成一 Phase | 3 |
| MP4 匯出修復 | 隨 engine.js | 3 |
| `src/core/exporter_video.py` 改用 `state_at` | 隨 engine.js | 3 |
| `Project.to_script_json` 重寫 | 隨 engine.js | 3 |
| 卡片內文字 inline 編輯 | 階段性增加複雜度 | 5 / 6 |
| 焦點保護（preview auto-play 不打斷編輯） | 配合 inline 編輯 | 5 |
| Undo / Redo | 範圍太大 | 後續 |
| 軌道顏色設定 / lane rename / 刪 lane | UI polish | 4 |
| 自訂 effect kinds payload schema | 等使用者試 Phase 2 後再決定要哪些 kind | 4 |
| 批次選取多個 segment | 等基本互動穩定後 | 5 |

## 假設（Assumptions — 請 codex 確認；user 可推翻）

1. **直接 port POC code**。`experimental/timeline_poc/` 的 `dialogue_column.py` / `stage_panel.py` / `effect_timeline.py` 已 user 驗收（commits `79b1855` + `c9e17f6`），Phase 2 直接搬進 `src/ui/`，最小調整接真資料。**不重新設計 widget**。
2. **Segment Payload 編輯器**：CenterPanel 底部 inline panel（與三欄並排，垂直 splitter），不用彈窗。理由：拖端點 + 編輯 payload 是同一手勢流。
3. **卡片暫不可編輯**。Phase 2 卡片是顯示 + 拖曳重排；文字 / 角色 / 效果的編輯延後到 Phase 5/6。理由：簡單先行，先確認三域骨架可用。
4. **Scene-wide effect quick setup 移除**。`left_panel.combo_effect`（rain/snow/crt/pixel_dark 全場景單選）刪除；改為「使用者在特效 timeline 拖一條覆蓋全場景的 segment」。理由：避免兩個 source of truth。
5. **舊批次操作刪除**。`StageSlotPickerDialog` / `StageBatchDialog` / `BatchAssignDialog` 整個從 `dialogs.py` 刪除，搬不回；批次操作的新版做法 Phase 5 重新設計。
6. **POC 的 PreviewPlaceholder 不用**。Phase 2 仍接既有 `src/ui/preview_widget.py` 的真 QtWebEngine 預覽。預覽功能此階段預期壞（engine.js 還沒改），但 UI 編輯仍可進行。

## 前置狀態檢查

- [ ] **0.1 在 Phase 1 完成的分支上**

```bash
git checkout feature/phase-1-data-model
git log --oneline -1   # Expected: d3f03c1 phase 1: 資料模型重構 ...
git status             # Expected: working tree clean
```

- [ ] **0.2 Phase 1 測試全綠**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

Expected: 151 passed.

- [ ] **0.3 開 Phase 2 分支**

```bash
git checkout -b feature/phase-2-ui
```

---

## Step 1 — POC widgets 移植到 `src/ui/`

**動作**

- [ ] **1.1** 複製 `experimental/timeline_poc/shared.py` → `src/ui/_timeline_shared.py`
  - 檔名前綴 `_` 表內部用、不對外 export
  - 內容不變

- [ ] **1.2** 複製 `experimental/timeline_poc/dialogue_column.py` → `src/ui/dialogue_list.py`
  - import 改：`from src.core.models import Scene, Dialogue`（不用 POC 的 local models）
  - import 改：`from src.ui import _timeline_shared as shared`
  - class 名 `DialogueColumn` → 保留（widget 取代名沒意義；只是檔名換成 `dialogue_list`）
  - signal `dialogue_moved(int, int)` 不變
  - `selection_changed(int)` / `cursor_changed(int)` 不變

- [ ] **1.3** 複製 `experimental/timeline_poc/stage_panel.py` → `src/ui/stage_panel.py`
  - 同樣 import 改寫
  - `StageSegment` 改用 `from src.core.models import StageSegment`
  - `Scene.all_stage_lanes()` POC 沒有，要在 `src/core/models.py::Scene` 加一個小 helper：

  ```python
  def all_stage_lanes(self) -> dict[str, list[StageSegment]]:
      return {"left": self.stage_left, "center": self.stage_center, "right": self.stage_right}
  ```
  （或者直接在 stage_panel.py 內 inline `{"left": scene.stage_left, ...}`，避免污染 core；codex 任選。）

- [ ] **1.4** 複製 `experimental/timeline_poc/effect_timeline.py` → `src/ui/effect_timeline.py`
  - 同樣 import 改寫

- [ ] **1.5** 新增 `tests/test_dialogue_list.py` / `tests/test_stage_panel.py` / `tests/test_effect_timeline.py`
  - 每檔最少含：
    - 能 instantiate（給 mock Scene）
    - paintEvent 不崩（需 `QT_QPA_PLATFORM=offscreen`）
    - 主要訊號可發射（manually trigger; 用 `qtbot.waitSignal` 或直接 connect 到 list）

**Verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_dialogue_list.py tests/test_stage_panel.py tests/test_effect_timeline.py -v
```

Expected: 三檔全綠（每檔 ≥ 3 tests）。

---

## Step 2 — `SegmentEditor` inline panel

**動作**

- [ ] **2.1** 新檔 `src/ui/segment_editor.py`：

  ```python
  class SegmentEditor(QWidget):
      """選中 segment 時顯示對應 payload 的 inline 編輯器。"""
      segment_changed = pyqtSignal()  # payload 改動
      
      def __init__(self, project_ref, parent=None): ...
      
      def set_segment(self, seg) -> None:
          """seg 為 StageSegment / EffectSegment / None"""
  ```

  - **StageSegment 模式**：
    - Character ComboBox（從 `self._project.characters` 取）
    - Costume ComboBox（依當前 character.costumes 級聯填）
    - Sprite ComboBox（依當前 costume.expressions 級聯填）
    - 級聯邏輯複用 Phase 1 之前的 `_on_char_combo_changed` 風格
  - **EffectSegment 模式**：
    - effect_type ComboBox（hard-coded list: `["rain", "snow", "crt", "screen_shake", "pixel_dark"]`；用 `_KNOWN_EFFECT_TYPES` 模組常量）
    - Params dict 編輯：用 `QPlainTextEdit` 顯示 JSON、blur 時 `json.loads` 寫回（簡單版，Phase 4 升級）
  - **None 模式**：顯示 placeholder Label「未選取」

- [ ] **2.2** 加 `tests/test_segment_editor.py`：
  - `set_segment(StageSegment(...))` → character ComboBox 顯示正確
  - `set_segment(EffectSegment(...))` → effect_type ComboBox 顯示正確
  - `set_segment(None)` → 切回 placeholder
  - 改 ComboBox → emit `segment_changed`

**Verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_segment_editor.py -v
```

Expected: 全綠。

---

## Step 3 — 重組 `src/ui/center_panel.py`

> ⚠️ **最高 regression 風險的一步**。此檔目前 1300+ 行，Step 3 預期 ≥ 800 行被刪 / 重寫。

**動作**

- [ ] **3.1** 保留 class `CenterPanel(QWidget)` 簽章（`MainWindow` 已 reference），改寫 `__init__`：
  - 刪：`dialogue_table` 整套、`_StageCellWidget`、`_EffectsMenuButton`、`_IndexDelegate`、`_HoverFilter`、`_DraggableTable`、`_MultilineDelegate`
  - 刪：所有 `setCellWidget` / `setSpan` / `_refresh_dialogue_table` / `_on_*_combo_changed` / `_on_dialogue_edited` / `_open_stage_picker` / `_on_stage_slot_clicked` / `_on_batch_assign` / `_on_batch_stage` / `_on_batch_delete_selected` / 搜尋高亮整套（Phase 5 重做）
  - 留：頂部 toolbar（加場景／預覽刷新按鈕等基本動作）

- [ ] **3.2** 新 layout（仿 `experimental/timeline_poc/main.py` 的 `POCMainWindow` 結構）：

  ```
  CenterPanel (QSplitter Vertical)
  ├─ PreviewWidget (頂；既有，不動)
  └─ Bottom (QSplitter Vertical)
      ├─ Workspace (QSplitter Horizontal, 包在 QScrollArea)
      │   ├─ DialogueColumn  (左, 拉伸)
      │   ├─ StagePanel      (中, fixed width 3*LANE_WIDTH)
      │   └─ EffectTimelineWidget (右, fixed width N*LANE_WIDTH)
      └─ SegmentEditor (底, fixed height ~140px)
  ```

  - 每欄包成「header + content」的小 widget（POC 的 `_Column`）

- [ ] **3.3** Signals 連接：

  | Source | Slot | 行為 |
  |---|---|---|
  | `dialogue_list.dialogue_moved(src, dst)` | `_on_dialogue_moved` | `scene.move_dialogue(src, dst)` + refresh + `project_changed` |
  | `dialogue_list.cursor_changed(idx)` | `_on_cursor` | 同步三 widget cursor + preview goto |
  | `stage_panel.cursor_changed(idx)` | 同上 | |
  | `effect_timeline.cursor_changed(idx)` | 同上 | |
  | `dialogue_list.selection_changed(idx)` | `_on_cursor` | |
  | `stage_panel.segment_changed` | `_refresh_segments_only` + preview refresh | |
  | `effect_timeline.segment_changed` | 同上 | |
  | `stage_panel.segment_selected(seg)` | `segment_editor.set_segment(seg)` | |
  | `effect_timeline.segment_selected(seg)` | `segment_editor.set_segment(seg)` | |
  | `segment_editor.segment_changed` | `_refresh_segments_only` + preview refresh | |
  | `preview.bridge.dialogue_advanced` | `_on_cursor` | 既有 |

- [ ] **3.4** 公開 API（`MainWindow` 仍會呼叫）：
  - `set_project(project)`
  - `set_current_scene(idx)`
  - `add_dialogues_to_current_scene(dialogues, insert_after=None)` — 改用 `Scene.insert_dialogue` 連續呼叫
  - `cleanup()`（preview teardown 用）

- [ ] **3.5** 加 `tests/test_center_panel.py`：
  - `instantiate + set_project + 三 widgets attribute 存在`
  - `add_dialogues_to_current_scene([Dialogue, ...])` 後 `dialogue_list` 顯示正確列數
  - `dialogue_moved` 觸發後 segments 端點同步（複用 test_scene_sync 的 fixture）

**Verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_center_panel.py -v
QT_QPA_PLATFORM=offscreen python -c "
from PyQt6.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
app = QApplication([])
from src.ui.main_window import MainWindow
w = MainWindow()
assert hasattr(w.center_panel, 'dialogue_list')
assert hasattr(w.center_panel, 'stage_panel')
assert hasattr(w.center_panel, 'effect_timeline')
assert hasattr(w.center_panel, 'segment_editor')
print('center_panel structure OK')
"
```

Expected: 兩個檢核都 OK。

---

## Step 4 — `src/ui/left_panel.py` 場景屬性面板

**動作**

- [ ] **4.1** 移除 `combo_effect` + `_on_effect_changed` + `effect_changed` signal 整段
- [ ] **4.2** 移除對應 `set_scene` / `refresh` 中讀寫 `scene.effect` 的程式碼
- [ ] **4.3** 場景刪除確認對話框升級：
  - 計算 `n_dialogues = len(scene.dialogues)`、`n_stage = sum of three lanes`、`n_effect = sum across effect_tracks`
  - dialog message：`「將連帶刪除 {n_dialogues} 則對話、{n_stage} 條立繪 segment、{n_effect} 條特效 segment。」`
- [ ] **4.4** 角色 / 場景的其他既有功能（拖曳重排、雙擊重命名）不動

**Verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -k "left_panel or scene"   # 既有測試應仍綠
grep -rn "combo_effect\|scene\.effect\b" src/ui/   # Expected: 空
```

---

## Step 5 — `src/ui/main_window.py` 角色刪除流程

**動作**

- [ ] **5.1** 找到 `_on_remove_character`：
  - 原本掃所有 dialogues 清 `dlg.character = None; dlg.type = "narration"; dlg.sprite = None; dlg.costume = None`
  - 新版（dlg.sprite/.costume/.stage 都不存在）：
    ```python
    for scene in self._project.scenes:
        for dlg in scene.dialogues:
            if dlg.character == removed_name:
                dlg.character = None
                dlg.type = "narration"
        # 同時掃 stage segments
        for lane in (scene.stage_left, scene.stage_center, scene.stage_right):
            lane[:] = [seg for seg in lane if seg.character != removed_name]
    ```

- [ ] **5.2** 加 `tests/test_main_window_remove_character.py`：
  - 建 Project 含 1 角色 + 3 dialogues 都用該角 + 3 stage segments 都該角
  - 呼叫 remove → 斷言 dialogues 全 narration、stage 三 lane 都空

**Verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_main_window_remove_character.py -v
```

---

## Step 6 — `src/ui/dialogs.py` 清理

**動作**

- [ ] **6.1** 刪除 `StageSlotPickerDialog` / `StageBatchDialog` / `BatchAssignDialog` 三個 class
- [ ] **6.2** 移除這三個 class 的所有 import（在 dialogs.py 內無用 import 一併清）
- [ ] **6.3** 確認 src/ 沒有其他 import 它們（Step 3 已刪 center_panel 用法；double-check）

**Verification**

```bash
grep -rn "StageSlotPickerDialog\|StageBatchDialog\|BatchAssignDialog" src/
```

Expected: 空輸出。

---

## Step 7 — `src/ui/preview_widget.py` signal 微調

**動作**

- [ ] **7.1** `PreviewBridge.stage_slot_clicked(scene_idx, dlg_idx, position, action)` 已沒對應 widget 觸發，**保留 signal 但不接 listener**（簡單，不破壞 engine.js 端 hook；Phase 3 engine.js 改寫時再決定要不要刪）
- [ ] **7.2** `dialogue_advanced` 不變
- [ ] **7.3** `_copy_assets` 既有的 `char.sprites` 屬性還在（property 展平），不動

**Verification**

既有 `tests/test_webengine_capture.py` 應仍綠。

---

## Step 8 — 文件更新

**動作**

- [ ] **8.1** `docs/DEVELOPMENT_HISTORY.md` 加 Phase 2 摘要（30-50 行）：
  - 拆掉的東西（QTableWidget + 7 處欄位寫入點）
  - 新結構（三域 + segment editor）
  - 給 CODEX 的備忘：MP4 此階段仍壞，等 Phase 3

**Verification**

`git diff docs/DEVELOPMENT_HISTORY.md` 顯示新增的 Phase 2 區塊。

---

## 完成判定（codex 跑這份檢核）

```bash
# 1) 完整測試
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v

# 2) MainWindow 結構
QT_QPA_PLATFORM=offscreen python -c "
from PyQt6.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
app = QApplication([])
from src.ui.main_window import MainWindow
w = MainWindow()
cp = w.center_panel
assert hasattr(cp, 'dialogue_list'), 'dialogue_list 缺'
assert hasattr(cp, 'stage_panel'), 'stage_panel 缺'
assert hasattr(cp, 'effect_timeline'), 'effect_timeline 缺'
assert hasattr(cp, 'segment_editor'), 'segment_editor 缺'
assert not hasattr(cp, 'dialogue_table'), '舊 QTableWidget 應已刪除'
print('STRUCTURE OK')
"

# 3) 沒有遺留欄位讀取
grep -rn '\.sprite\b\|\.costume\b\|dlg\.stage\|d\.stage\|scene\.effect\b' src/ui/
# Expected: 空

# 4) 舊 dialogs 已刪
grep -rn 'StageSlotPickerDialog\|StageBatchDialog\|BatchAssignDialog' src/
# Expected: 空

# 5) Phase 2 新檔案在位
ls src/ui/dialogue_list.py src/ui/stage_panel.py src/ui/effect_timeline.py src/ui/segment_editor.py src/ui/_timeline_shared.py

# 6) 預期會壞的（不是阻擋驗收，只是確認 Phase 3 範圍）
QT_QPA_PLATFORM=offscreen python -c "
from PyQt6.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
app = QApplication([])
from src.ui.main_window import MainWindow
w = MainWindow()
print('main.py 等價建構 OK；MP4 匯出仍預期壞（等 Phase 3）')
"
```

**驗收條件全部滿足才視為 Phase 2 完成。** Codex 若發現任何一項失敗，回報具體哪步出問題、stderr 末段、以及 grep 結果。

---

## 風險與已知地雷

1. **POC 固定列高 52px** 在某些 UI 字體（28px）下可能擠壓。先沿用 POC 值；若視覺出問題在 Step 3 結束時調整 `_timeline_shared.ROW_HEIGHT`，獨立小 commit。
2. **center_panel.py 重寫的 regression** 是最高風險。Step 3 切成 2-3 個小 commit（先層架構、再 signals、再 segment_editor 整合）便於 bisect。
3. **SegmentEditor 的 cascade race**：使用者改 character 後 sprite 還停留在舊角色的差分。處理：character ComboBox 變更時，重設 costume 為第一個（或 None），sprite 同樣 cascade reset。POC 沒做這部分。
4. **共用 Y 軸 + ScrollArea** 在 PyQt6 6.11 已驗證；但若 user 環境不同需確認。Step 3 結束跑 main.py 視覺檢查。
5. **Bug 1 / Bug 3 的處理**：兩者已在 main 上 merged（commits `f03b4f8` + `c237d1f`），Phase 1 分支自然 inherit。Bug 3 的 `set_stage_slot` 在 Phase 1 隨 `Dialogue.stage` 一起被刪了（dead code 不留）。Phase 2 不需重做。

## 工作量估計

3-5 天（取決於 SegmentEditor cascade UI 細節 + center_panel signal rewire 踩雷）。

## Phase 2 完成後狀態

- ✅ pytest 全綠
- ✅ `python main.py` 可開、可拖卡片、可拖 segment、可改 segment payload
- ❌ MP4 匯出仍壞（待 Phase 3）
- ❌ 預覽呈現可能與真實期望不符（engine.js 還讀舊欄位 → fallback null；Phase 3 接好）
- 分支：`feature/phase-2-ui`，**不 merge to main**

下一步：Phase 3 把 engine.js / exporter / `Project.to_script_json` 全部接到 `state_at`，MP4 端到端驗收後一起 merge。
