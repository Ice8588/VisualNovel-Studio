# Phase 4-6 Closeout — 重構收尾

> **給驗證 AI（codex）：** 本文件為 Phase 4-6 的剩餘工作 spec，可獨立讀懂。
> 上游：`main`（已含 Phase 1+2+3 + 批 A/B/C + Phase 4 lane mgmt 共 17 個 commit）。
> 本 Phase 分支：`feat/phase-4-6-closeout`，從 `main` branch off。
>
> 本計畫**不**新增大型 feature；只完成原 task.md / 重構 plan 中 Phase 4-6 落網的小事。

---

## Goal（一句話）

把 Phase 4-6 計畫中**還沒做的**polish 一次掃乾淨，重構正式 closeout，後續可開新 feature。

## 目前剩餘清單（4 項；已盤點 main 確認）

| # | 來自 | 內容 | 大小 |
|---|---|---|---|
| 4.2 | Phase 4 | EffectTrack 顏色設定（per-track override） | 小 |
| 5.1 | Phase 5 | 焦點保護：reload_preview 後恢復 dlg 位置 | 小 |
| 6.2 | Phase 6 | qfluentwidgets 樣式 pass（深淺色雙側） | 中（review-only） |
| 6.3 | Phase 6 | DEVELOPMENT_HISTORY 收斂 Phase 4-6 摘要 | 小 |

**已完成不重做**（已驗 main code 確認）：
- 4.1 軌道 rename / delete — `feat/effect-track-rename-delete` 已 merge
- engine.js screen_shake 渲染 — 批 A
- 5.2 場景刪除 confirm + 角色刪除軟性解綁 — Phase 2
- 6.1 頭像上 40% × 中 40% 裁切 — `left_panel.py:541-556` 已實作

**明確排除**（user 沒要求 / 不必要）：
- EffectSegment payload editor 換成 known-kinds form — JSON 編輯器目前夠用，engine.js 也未消化 params；列為 future work
- RemovalReport pattern — 目前 UI 沒有「刪除單一對話」入口，無從觸發
- Multi-effect 同 lane 疊加渲染 — 設計已決定 mutual exclusive，POC 起就這樣

---

## 假設（codex 確認；user 可推翻）

1. **EffectTrack 加 `color: str | None` 欄位**：to_dict / from_dict 序列化；`None` fallback 到 `EFFECT_COLORS` by effect_type。
2. **顏色設定 UX**：右鍵軌道 header → 「設定顏色…」→ `QColorDialog`；選好寫入 `track.color`。
3. **焦點保護**：CenterPanel 追蹤 `_last_preview_dlg_idx`（已從 `_on_preview_dialogue_advanced` / `_on_cursor_from_widget` 知道），在 `_on_segment_committed` reload 後 `QTimer.singleShot(500ms)` 跳回。500ms 是保守值；若 user 環境慢可調。
4. **qfluentwidgets pass**：只做 review，發現不一致再修，不 preemptive。
5. **DEVELOPMENT_HISTORY 寫法**：合併 Phase 4-6 進一個 closeout 區段；不分節（畢竟剩的少）。

---

## 前置狀態檢查

- [ ] **0.1** 在 main 上：

```bash
git checkout main
git log --oneline -3
# Expected: 最新含 8c403cf feat(timeline): 特效軌道支援右鍵 rename / delete
git status   # working tree clean
```

- [ ] **0.2** pytest baseline：

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
# Expected: 全綠（≈203 passed + 1 skipped）
```

- [ ] **0.3** 開分支：

```bash
git checkout -b feat/phase-4-6-closeout
```

---

## Step 1 — 4.2 EffectTrack 顏色設定

**檔案**：[src/core/models.py](src/core/models.py) [src/ui/effect_timeline.py](src/ui/effect_timeline.py) [src/ui/center_panel.py](src/ui/center_panel.py)

- [ ] **1.1** `src/core/models.py::EffectTrack` 加欄位：

```python
@dataclass
class EffectTrack:
    name: str
    color: str | None = None  # Phase 4.2：使用者覆寫；None 走 effect_type 預設
    segments: list[EffectSegment] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"name": self.name, "segments": [s.to_dict() for s in self.segments]}
        if self.color:
            d["color"] = self.color
        return d

    @classmethod
    def from_dict(cls, data: dict) -> EffectTrack:
        return cls(
            name=data["name"],
            color=data.get("color"),
            segments=[EffectSegment.from_dict(s) for s in data.get("segments", [])],
        )
```

- [ ] **1.2** `EffectLaneWidget._paint_segment`：base color 從 `self.track.color` 優先取，再 fallback `_effect_color(seg.effect_type)`。

```python
base = QColor(self.track.color) if self.track.color else _effect_color(seg.effect_type)
```

- [ ] **1.3** `_TrackLabel`（已存在的 right-click menu）加新動作：

```python
menu.addAction("設定顏色…", lambda: self.color_requested.emit(self.track_name))
```

新 signal `color_requested(str)`；header 接到後彈 `QColorDialog`。

- [ ] **1.4** `EffectTimelineHeader` 接 `color_requested`：

```python
track_color_changed = pyqtSignal(str, str)   # (name, hex)

def _on_color_requested(self, name: str) -> None:
    track = next((t for t in self.scene.effect_tracks if t.name == name), None)
    initial = QColor(track.color) if track and track.color else QColor("#5F6368")
    chosen = QColorDialog.getColor(initial, self, "選擇軌道顏色")
    if chosen.isValid():
        self.track_color_changed.emit(name, chosen.name())  # "#RRGGBB"
```

- [ ] **1.5** `EffectTimelineWidget` 加 `set_track_color(name, hex) -> bool`：找到 track 寫 color、emit segment_committed。

- [ ] **1.6** `CenterPanel._rebuild_workspace` 接 `track_color_changed` → 呼叫 `effect_timeline.set_track_color()` + 更新 header label 背景色（讓使用者看出顏色設了哪條）。

- [ ] **1.7** Header label 顯示：在 label 上加一個小 4px 左豎條塊或整個 label 底色微調，反映目前 track.color。

- [ ] **1.8** 測試 `tests/test_effect_timeline.py` 加：
  - `set_track_color` 回 True、emit committed、color 寫入
  - 不存在的 track 回 False
  - color None 時 _paint_segment 用 effect_type 預設色（不崩）
  - to_dict / from_dict roundtrip 含 / 不含 color

**Verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_effect_timeline.py -v
```

---

## Step 2 — 5.1 焦點保護：preview position preservation

**檔案**：[src/ui/center_panel.py](src/ui/center_panel.py)

**現況**：`_on_segment_committed` / `_on_segment_edited` / `_on_add_effect_track` / 任何 lane mgmt 動作都呼叫 `preview.reload_preview()`，preview restart 從 scene 0 dlg 0。使用者剛剛在 dlg 5 拖了 segment，畫面跳回開頭，難用。

- [ ] **2.1** 加 instance attr 追蹤 last preview position：

```python
def __init__(...):
    ...
    self._last_preview_pos: tuple[int, int] = (0, 0)  # (scene_idx, dlg_idx)
```

- [ ] **2.2** 在三個地方更新 `_last_preview_pos`：
  - `_on_preview_dialogue_advanced(scene_idx, dlg_idx)` 開頭
  - `_on_cursor_from_widget(idx)`：`self._last_preview_pos = (self._current_scene_index, idx)`
  - `set_current_scene(idx)`：`self._last_preview_pos = (idx, 0)`

- [ ] **2.3** 新 helper `_reload_preview_keep_position()`：

```python
from PyQt6.QtCore import QTimer

def _reload_preview_keep_position(self) -> None:
    if not self._project or self._current_scene_index < 0:
        return
    scene_idx, dlg_idx = self._last_preview_pos
    self.preview.reload_preview(self._project)
    # 等 webengine 載完再跳回；500ms 是保守值
    QTimer.singleShot(
        500,
        lambda: self.preview.jump_to_dialogue(scene_idx, dlg_idx),
    )
```

- [ ] **2.4** 把所有現有 `self.preview.reload_preview(self._project)` 呼叫改為 `self._reload_preview_keep_position()`。grep 過 4 處：
  - `_on_segment_committed`
  - `_on_segment_edited`（SegmentEditor 改 payload）
  - `_on_add_effect_track`（加軌道後 rebuild_workspace 也會走這條？要確認）
  - 其他若有

- [ ] **2.5** Edge case：scene 切換時不該 keep position（不同 scene、dlg_idx 沒意義）。`set_current_scene` 仍直接呼叫 `reload_preview`，**不**走 keep。

**Verification**

手動：
- main.py → 開 fixture → 點 dialogue 3 預覽到第 3 句 → 拖 stage segment 端點 → release → preview 應仍停在第 3 句而非跳回第 1 句

自動測試難寫（涉及 webengine timing），不強制；commit message 註明「手動驗收」。

---

## Step 3 — 6.2 qfluentwidgets 樣式 pass

**檔案**：[src/ui/](src/ui/) 多檔；review-driven，可能 0 改動或數行調整

- [ ] **3.1** Review checklist：
  - 所有對話框（dialogs.py 的 ScenePropertiesDialog 等）按鈕用 qfluentwidgets `PushButton` 嗎？
  - 預覽 toolbar 的 SpinBox / DoubleSpinBox 是否與其他 qfluentwidgets 元件視覺一致？
  - 深 / 淺色主題切換時，新加的 widgets（SegmentEditor popup / TrackLabel 等）有沒有破綻？
  - 新加 widgets 用 hard-coded color (`#XXXXXX`) 還是讀 theme palette？硬編在 dark 主題 OK，淺色主題可能對比不足。

- [ ] **3.2** 跑 main.py，深 / 淺色各切一次：
  - **深色**：默認狀態，所有元件已驗證
  - **淺色**：View → Theme → Light → 檢查
    - DialogueColumn 卡片背景 `#2E3440` / `#2D2D30`：在淺色主題會太深？應加 `theme.is_light()` 條件
    - StagePanel / EffectLane segment 顏色：character_color 用使用者選的色，OK
    - SegmentEditor popup 樣式：寫死 `#2D2D30 + #3D8AC4`，淺色主題會突兀
    - TrackLabel `#252526` 背景：同上

- [ ] **3.3** 若發現破綻，最小修：把寫死的 `#2D2D30` 等改為從 `_timeline_shared` 讀，並在 `_timeline_shared.py` 內加 `is_light_mode()` 判斷返回不同色。

  簡化版：定義兩組色（dark / light），開個 `set_theme_mode(mode)` API；CenterPanel 在主題切換時呼叫。

- [ ] **3.4** 若沒大破綻，記下「目前狀態：dark 已驗證，light 已可用但部分 widgets 仍用 dark hardcoded color，list 為 follow-up」。

**Verification**：commit message 註明 review 結果（多少個 widget 修了 / 沒修但已知）。

---

## Step 4 — 6.3 DEVELOPMENT_HISTORY 收斂

**檔案**：[docs/DEVELOPMENT_HISTORY.md](docs/DEVELOPMENT_HISTORY.md)

- [ ] **4.1** 加 Phase 4-6 closeout 區段（30-50 行）：

```markdown
## Phase 4-6 Closeout 紀錄（2026-04-19）

### 完成
- 4.1 軌道 rename / delete（feat/effect-track-rename-delete）
- 4.2 EffectTrack 顏色設定 per-track override
- 5.1 reload_preview 後跳回原 dlg 位置（焦點保護）
- 6.1 頭像上 40% × 中 40% 裁切（已在 left_panel.py:541-556）
- 6.2 qfluentwidgets 樣式 pass：[review 結果摘要]
- 6.3 此紀錄

### 排除（明確 future work，非 bug）
- EffectSegment payload editor 改 known-kinds form（目前 JSON 夠用）
- RemovalReport pattern（無 UI 入口）
- Multi-effect 同 lane 疊加（設計：mutual exclusive）

### ADR-006：to_script_json 為 engine 消化的 view
（已在 Phase 3 紀錄，這裡引用）

### 給下一位的備忘
- 重構主線到此完成。後續新 feature 開 main 直接做。
- experimental/timeline_poc/ 可丟棄但有歷史價值，先留著。
- experimental/phase3_mp4_verify/ fixture 是 user MP4 驗收標準，動 engine.js / exporter 時記得跑一次。
```

- [ ] **4.2** （optional）整理 docs/superpowers/plans/ 加 README 列出已完成的 phase plan 檔，便於後續查閱。

---

## 完成判定（codex 跑這份檢核）

```bash
# 1) 完整測試
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v
# Expected: 全綠（含新增的 set_track_color tests）

# 2) Track color 持久化
QT_QPA_PLATFORM=offscreen python -c "
from src.core.models import EffectTrack
t = EffectTrack(name='測試', color='#FF6600')
t2 = EffectTrack.from_dict(t.to_dict())
assert t2.color == '#FF6600'
print('track color persistence OK')
"

# 3) 焦點保護手動驗收
#   - main.py → 開 fixture → 點對話 3
#   - 拖 stage segment 端點 → release
#   - 預覽應停在對話 3 不回跳
#   （此項目視驗收，無自動 test）

# 4) DEVELOPMENT_HISTORY 已更新
git diff docs/DEVELOPMENT_HISTORY.md | head -30
```

**完成標準**：1 + 2 + 4 通過 + 3 由 user 手動驗收。

---

## 風險與已知地雷

1. **Step 2 焦點保護 timing 不可靠**：500ms 在某些慢機器仍不夠，使用者會看到「跳回後再跳到正確位置」。改善：加 webengine loadFinished 信號偵測（複雜），或拉長到 800ms（簡單但慢）。先 500ms ship、收回饋。
2. **Step 1 軌道顏色**：character_color 也支援使用者自訂（已有），形成「角色色 + 軌道色」雙制度。**注意只有特效軌道用 track.color；舞台 segment 仍只用角色色**，避免衝突。
3. **Step 3 light mode**：若 review 發現多個 widget 需改主題感知，scope 會膨脹。**保守 = 只記錄不修**，避免變成大重構。
4. **Step 4 文件**：避免重複 Phase 1-3 已寫過的細節，只記 Phase 4-6 增量。

## 工作量估計

1-2 天。Step 1 半天；Step 2 1-2 小時；Step 3 review 1 小時 + 修 0-2 小時；Step 4 半小時。

## Phase 4-6 完成後狀態

- ✅ 重構計畫所有 phase 完成（含 polish）
- ✅ pytest 全綠
- ✅ 文件收斂

下一步：等 user 提新 feature 或 bug；本重構告一段落。
