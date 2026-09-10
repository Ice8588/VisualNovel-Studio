# 作品/影片兩層結構與跨作品角色復用 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 本計畫**取代** `2026-06-11-character-card-ux.md`（角色卡管理器方案）。設計討論結論：
> 一個專案 = 一個作品，底下多支影片（Episode）共用角色/素材/設定，各自導出 MP4；
> 跨作品復用改為「從其他作品匯入角色」（直接讀對方 .vnsproj），使用者語彙不出現「卡」；
> `character_library.py`（.vncard）保留為休眠的分享格式後端，UI 入口移除。

**Goal:** 讓一個作品能容納多支影片（共用角色與素材、各自導出），並以「從其他作品匯入角色」取代角色卡 UI，同時修掉角色設定的新手陷阱。

**Architecture:** `models.py` 在 Project 與 Scene 之間插入 `Episode` 層；`Project.scenes` 改為指向**目前影片**的 property（getter/setter），使 center_panel / exporter / preview 等約 40 個既有取用點零修改。存檔升級 v2（episodes），舊檔開啟時自動包成單影片作品。UI 採漸進揭露：單影片時介面與現狀完全相同，第二支影片出現後左側才顯示影片切換列。跨作品角色搬運為新核心模組 `character_transfer.py` + 選擇器對話框。

**Tech Stack:** Python 3.12 + PyQt6 + qfluentwidgets；pytest（`QT_QPA_PLATFORM=offscreen`），UI 測試用 `tests/conftest.py` 的 session-scope `qapp` fixture。

---

## Spec 對照表

| # | 需求/問題（來源：設計討論 + 2026-06-11 新手走查） | Task |
|---|------|------|
| S1 | 一個作品多支影片，共用角色/素材/設定，各自導出 MP4 | 1, 3, 4 |
| S2 | 舊 .vnsproj 自動遷移為單影片作品 | 1, 2 |
| S3 | 漸進揭露：單影片時 UI 不變；「新增影片」入口常駐檔案選單 | 3, 4 |
| S5 | 跨作品復用 = 從其他作品匯入角色（含立繪複製、同內容去重、同名詢問） | 5, 6 |
| S6 | 移除角色卡 UI（「從角色卡匯入/儲存為角色卡」按鈕與流程） | 7 |
| S7 | 走查陷阱：零服裝按「新增差分」靜默無反應 | 8 |
| S8 | 走查陷阱：移除含差分服裝零確認 | 8 |
| S9 | 走查陷阱：編輯多服裝角色只見一張圖，其餘隱形 | 9 |
| S10 | 教學文案補「影片」與「匯入角色」概念 | 10 |

（原 S4「`Episode.group` 預留欄位」經 2026-06-11 審查以 YAGNI 移除：`from_dict` 忽略未知 key，未來要加分組欄位時一行即可、舊 v2 檔免遷移，「預留」買不到任何相容性。編號保留缺口。）

## 檔案結構

| 檔案 | 動作 | 職責 |
|------|------|------|
| `src/core/models.py` | 修改 | 新增 `Episode`；`Project` 改 episodes + scenes property + v2 序列化 |
| `src/core/character_transfer.py` | **新增** | `copy_file_dedup`、`import_character`（純邏輯，無 Qt） |
| `src/ui/left_panel.py` | 修改 | 影片切換列（combo + 新增 + ⋯選單）、「從其他作品匯入…」按鈕 |
| `src/ui/character_import.py` | **新增** | `CharacterImportDialog` 勾選式角色選擇器（縮圖+統計） |
| `src/ui/main_window.py` | 修改 | episode 信號接線、檔案選單「新增影片」、匯入角色 handler、教學文案 |
| `src/ui/dialogs.py` | 修改 | 移除角色卡按鈕/方法；CostumeEditor 防陷阱；服裝摘要標籤 |
| `tests/test_models.py` 等 | 修改 | 見各 Task；另有 ctor 呼叫點機械式更新 |
| `tests/test_character_transfer.py` 等 | **新增** | 新模組測試 |
| `docs/DEVELOPMENT_HISTORY.md` | 修改 | 收尾摘要 |

不動的部份（驗證過邊界）：`engine.js`（吃的攤平 script 結構不變）、`scene_state.py`、`exporter_video.py` / `webengine_capture.py`（經 `project.scenes` property 自動取得目前影片）、`project_io.py`（遷移邏輯放在 `Project.from_dict`）。

## 開工前

- [ ] **Step 0a: 建分支**

```bash
git checkout -b feature/episodes-and-character-reuse
```

- [ ] **Step 0b: 標註舊計畫已被取代**

在 `docs/superpowers/plans/2026-06-11-character-card-ux.md` 第 1 行（標題行）之後插入：

```markdown

> **已取代（superseded）**：設計方向變更為「作品/影片兩層 + 從其他作品匯入角色」，
> 改由 `2026-06-11-episodes-and-character-reuse.md` 執行。本文件僅保留走查紀錄價值。
```

```bash
git add docs/superpowers/plans/2026-06-11-character-card-ux.md
git commit -m "docs: 標註角色卡管理器計畫已被 episodes 計畫取代"
```

---

### Task 1: Episode 資料模型 + Project v2 序列化

**Files:**
- Modify: `src/core/models.py`（`Scene` 之後、`GameSettings` 之前插入 `Episode`；改寫 `Project`）
- Test: `tests/test_models.py`

- [ ] **Step 1: 寫失敗測試**

加到 `tests/test_models.py` 尾端（檔案既有 import 應已含 `Project, Scene, Dialogue`；補 `Episode`）：

```python
from src.core.models import Episode


class TestEpisodes:
    def test_default_project_has_one_episode(self):
        p = Project()
        assert len(p.episodes) == 1
        assert p.episodes[0].name == "影片1"
        # scenes property 是 active episode 的 live reference
        assert p.scenes is p.episodes[0].scenes

    def test_scenes_property_follows_active_episode(self):
        e1 = Episode(name="第一集", scenes=[Scene(id="A")])
        e2 = Episode(name="第二集", scenes=[Scene(id="B")])
        p = Project(episodes=[e1, e2])
        assert [s.id for s in p.scenes] == ["A"]
        p.active_episode_index = 1
        assert [s.id for s in p.scenes] == ["B"]

    def test_scenes_setter_writes_into_active_episode(self):
        # left_panel 場景拖曳排序會做 project.scenes = new_order，必須寫進 active episode
        p = Project()
        p.scenes = [Scene(id="X")]
        assert [s.id for s in p.episodes[0].scenes] == ["X"]

    def test_to_dict_writes_v2(self):
        p = Project(title="作品", episodes=[
            Episode(name="第一集", scenes=[Scene(id="A")]),
            Episode(name="第二集"),
        ])
        p.active_episode_index = 1
        data = p.to_dict()
        assert data["version"] == 2
        assert "scenes" not in data  # 頂層不再有 scenes
        restored = Project.from_dict(data)
        assert [e.name for e in restored.episodes] == ["第一集", "第二集"]
        assert restored.active_episode_index == 1
        assert restored.episodes[0].scenes[0].id == "A"

    def test_from_dict_migrates_v1_file(self):
        old = {
            "title": "舊專案",
            "scenes": [{"id": "場景1", "dialogues": []}],
            "characters": [],
        }
        p = Project.from_dict(old)
        assert len(p.episodes) == 1
        assert p.episodes[0].name == "影片1"
        assert p.scenes[0].id == "場景1"

    def test_to_script_json_exports_active_episode_only(self):
        e1 = Episode(name="一", scenes=[Scene(id="A", dialogues=[Dialogue(type="narration", text="hi")])])
        e2 = Episode(name="二", scenes=[Scene(id="B", dialogues=[Dialogue(type="narration", text="yo")])])
        p = Project(episodes=[e1, e2])
        assert [s["id"] for s in p.to_script_json()["scenes"]] == ["A"]
        p.active_episode_index = 1
        assert [s["id"] for s in p.to_script_json()["scenes"]] == ["B"]

    def test_next_episode_name(self):
        p = Project()
        assert p.next_episode_name() == "影片2"
        p.episodes.append(Episode(name="自訂名"))
        assert p.next_episode_name() == "影片2"
        p.episodes.append(Episode(name="影片7"))
        assert p.next_episode_name() == "影片8"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py::TestEpisodes -v`（環境變數 `QT_QPA_PLATFORM=offscreen`，以下皆同）
Expected: FAIL（ImportError: cannot import name 'Episode'）

- [ ] **Step 3: 實作**

`src/core/models.py`，在 `Scene` 之後、`GameSettings` 之前插入：

```python
@dataclass
class Episode:
    """一支影片：擁有自己的場景與劇本；角色/素材/設定屬於上層 Project（作品）。"""

    name: str
    scenes: list[Scene] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "scenes": [s.to_dict() for s in self.scenes]}

    @classmethod
    def from_dict(cls, data: dict) -> Episode:
        return cls(
            name=data["name"],
            scenes=[Scene.from_dict(s) for s in data.get("scenes", [])],
        )
```

（不預留分組欄位：`from_dict` 忽略未知 key，未來要加時 `data.get("group", "")` 一行即可，舊檔免遷移。）

`Project` 改寫：docstring 與欄位區改為：

```python
@dataclass
class Project:
    """專案根物件 = 一個作品：角色/素材/設定全作品共用，底下多支影片（Episode）各自導出。"""

    title: str = "Untitled"
    episodes: list[Episode] = field(default_factory=lambda: [Episode(name="影片1")])
    active_episode_index: int = 0
    characters: list[Character] = field(default_factory=list)
    assets: dict[str, list[str]] = field(
        default_factory=lambda: {
            "backgrounds": [],
            "sprites": [],
            "music": [],
        }
    )
    project_path: Path | None = None
    game_settings: GameSettings = field(default_factory=GameSettings)

    @property
    def active_episode(self) -> Episode:
        """目前編輯中的影片。index 有效性由 from_dict（反序列化邊界）與 UI 操作維護；
        getter 不做防呆修復，索引 bug 應直接浮出而非被靜默吞掉。"""
        return self.episodes[self.active_episode_index]

    @property
    def scenes(self) -> list[Scene]:
        """目前影片的場景列表（live reference）。預覽/導出/UI 一律經此取得。"""
        return self.active_episode.scenes

    @scenes.setter
    def scenes(self, value: list[Scene]) -> None:
        self.active_episode.scenes = value

    def next_episode_name(self) -> str:
        """產生下一個影片名稱，如「影片2」（沿用 next_scene_id 的命名慣例）。"""
        nums = [
            int(e.name[2:]) for e in self.episodes
            if e.name.startswith("影片") and e.name[2:].isdigit()
        ]
        return f"影片{max(nums, default=1) + 1}"
```

`to_dict` 改為：

```python
    def to_dict(self) -> dict:
        """完整序列化（含素材路徑），用於 .vnsproj 儲存。格式 v2：頂層 episodes。"""
        return {
            "version": 2,
            "title": self.title,
            "episodes": [e.to_dict() for e in self.episodes],
            "active_episode_index": self.active_episode_index,
            "characters": [c.to_dict() for c in self.characters],
            "assets": self.assets,
            "project_path": str(self.project_path) if self.project_path else None,
            "game_settings": self.game_settings.to_dict(),
        }
```

`from_dict` 改為：

```python
    @classmethod
    def from_dict(cls, data: dict) -> Project:
        default_assets = {"backgrounds": [], "sprites": [], "music": []}
        assets = data.get("assets", default_assets)
        for key in default_assets:
            if key not in assets:
                assets[key] = []

        if "episodes" in data:
            episodes = [Episode.from_dict(e) for e in data["episodes"]]
        else:
            # v1 遷移：頂層 scenes 包成單一影片
            old_scenes = [Scene.from_dict(s) for s in data.get("scenes", [])]
            episodes = [Episode(name="影片1", scenes=old_scenes)]
        if not episodes:
            episodes = [Episode(name="影片1")]
        raw_idx = int(data.get("active_episode_index", 0))

        path_str = data.get("project_path")
        gs_data = data.get("game_settings", {})
        return cls(
            title=data.get("title", "Untitled"),
            episodes=episodes,
            active_episode_index=max(0, min(raw_idx, len(episodes) - 1)),
            characters=[Character.from_dict(c) for c in data.get("characters", [])],
            assets=assets,
            project_path=Path(path_str) if path_str else None,
            game_settings=GameSettings.from_dict(gs_data),
        )
```

（`to_script_json` 與 `next_scene_id` 內的 `self.scenes` 取用**不需改**——property 自動指向目前影片。）

- [ ] **Step 4: 跑新測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py::TestEpisodes -v`
Expected: 全 PASS

- [ ] **Step 5: Commit（先收模型，下一個 task 修舊呼叫點）**

```bash
git add src/core/models.py tests/test_models.py
git commit -m "feat(models): Episode 兩層結構；Project.scenes 改 property 指向目前影片；存檔 v2"
```

---

### Task 2: 修復既有 `Project(scenes=...)` 呼叫點與 v1 斷言

`scenes` 從 dataclass 欄位變 property 後，建構子不再接受 `scenes=` kwarg。

**Files:**
- Modify（機械式轉換，清單已逐檔 grep 驗證）：以下所有 `Project(... scenes=X ...)` 改為 `Project(... episodes=[Episode(name="影片1", scenes=X)] ...)`，並在該檔 import 加 `Episode`：
  - `tests/test_exporter.py:18`
  - `tests/test_exporter_video.py:177`、`:215`
  - `tests/test_left_panel_props_sync.py:27`、`:116`
  - `tests/test_project_io.py:17`
  - `tests/test_models.py:88`、`:137`、`:155`、`:162`
  - `tests/test_to_script_json_phase3.py:35`
  - `tests/test_webengine_capture.py:76`、`:112`
  - `tests/test_main_window_remove_character.py:30`

  注意：`test_center_panel.py`、`test_capture_multi_sprite.py`、`test_exporter_video_phase3.py` 的 `Project(` 呼叫**不含** scenes kwarg（建構後用 `proj.scenes.append(...)`，property 下照常可用），**不要改**。行號若有漂移，一律以 Step 1 的 pytest 失敗輸出為準。

- [ ] **Step 1: 跑全測試看破壞面**

Run: `.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: 多個 FAIL/ERROR（`TypeError: Project.__init__() got an unexpected keyword argument 'scenes'`）。**以此失敗輸出為修復依據**（應與上方清單吻合；不吻合時以實際輸出為準）。

- [ ] **Step 2: 機械式修復**

轉換範例（`tests/test_to_script_json_phase3.py:35`）：

```python
# 修改前
    return Project(title="T", scenes=[scene])
# 修改後
    return Project(title="T", episodes=[Episode(name="影片1", scenes=[scene])])
```

補充（已逐檔驗證，無需動作）：
1. 現有測試**沒有**斷言 `to_dict()` 頂層 `"scenes"` / `"version"` key——roundtrip 全走 `from_dict(to_dict())` 或 save/load，v2 下自動通過。`test_models.py:145` 與 `test_exporter.py:110` 的 `["scenes"]` 取值是 `to_script_json()` / data.js 輸出（結構不變），不受影響。
2. `scripts/build_phase3_mp4_fixture.py` 的 `Project(` 不含 scenes kwarg；其後的 `proj.scenes.append(...)` 經 property 照常可用，不需改。

- [ ] **Step 3: 跑全測試確認綠**

Run: `.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: 全 PASS，0 failed

- [ ] **Step 4: Commit**

```bash
git add tests/ scripts/
git commit -m "test: Project 建構子改用 episodes，斷言更新至存檔 v2"
```

---

### Task 3: 舊檔遷移的端到端驗證（project_io）

`from_dict` 已含遷移邏輯；此 task 補「真實舊檔案 → load → save → reload」的整合保障。

**Files:**
- Test: `tests/test_project_io.py`

- [ ] **Step 1: 寫失敗（或直接通過則視為回歸保障）測試**

加到 `tests/test_project_io.py` 尾端：

```python
from src.core.models import Episode
# json、load_project、save_project：tests/test_project_io.py 檔內既有 import 已涵蓋


class TestV1Migration:
    def test_load_v1_file_and_resave_as_v2(self, tmp_path):
        """v1 舊檔（頂層 scenes）→ 開啟成單影片作品 → 存檔變 v2 → 重開不丟資料。"""
        v1 = {
            "title": "舊作品",
            "scenes": [
                {"id": "場景1", "dialogues": [
                    {"type": "narration", "text": "第一行", "character": None},
                ]},
            ],
            "characters": [{"name": "小美", "name_color": "#E05555", "costumes": []}],
        }
        old_file = tmp_path / "old.vnsproj"
        old_file.write_text(json.dumps(v1, ensure_ascii=False), encoding="utf-8")

        p = load_project(old_file)
        assert len(p.episodes) == 1
        assert p.scenes[0].dialogues[0].text == "第一行"
        assert p.characters[0].name == "小美"

        save_project(p, old_file)
        raw = json.loads(old_file.read_text(encoding="utf-8"))
        assert raw["version"] == 2
        assert raw["episodes"][0]["scenes"][0]["id"] == "場景1"

        p2 = load_project(old_file)
        assert p2.scenes[0].dialogues[0].text == "第一行"

    def test_multi_episode_roundtrip(self, tmp_path):
        p = Project(title="系列作", episodes=[
            Episode(name="第一集", scenes=[Scene(id="A")]),
            Episode(name="第二集", scenes=[Scene(id="B"), Scene(id="C")]),
        ])
        p.active_episode_index = 1
        f = tmp_path / "multi.vnsproj"
        save_project(p, f)
        p2 = load_project(f)
        assert [e.name for e in p2.episodes] == ["第一集", "第二集"]
        assert p2.active_episode_index == 1
        assert [s.id for s in p2.scenes] == ["B", "C"]
```

（`tests/test_project_io.py` 既有 import 已含 `Project, Scene`；缺的補上。）

- [ ] **Step 2: 跑測試**

Run: `.venv\Scripts\python.exe -m pytest tests/test_project_io.py -v`
Expected: 全 PASS（Task 1 已實作完畢；此處若 FAIL 表示遷移有漏，修 `models.py` 直到綠）

- [ ] **Step 3: Commit**

```bash
git add tests/test_project_io.py
git commit -m "test(io): v1 舊檔遷移與多影片 roundtrip 整合測試"
```

---

### Task 4: LeftPanel 影片切換列（漸進揭露）

**Files:**
- Modify: `src/ui/left_panel.py`
- Test: Create `tests/test_left_panel_episodes.py`

- [ ] **Step 1: 寫失敗測試**

新檔 `tests/test_left_panel_episodes.py`：

```python
"""LeftPanel 影片切換列：漸進揭露、切換、新增、刪除。"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from src.core.models import Episode, Project, Scene
from src.ui.left_panel import LeftPanel


def test_episode_bar_hidden_when_single_episode(qapp):
    panel = LeftPanel()
    panel.set_project(Project())
    assert not panel._episode_bar.isVisibleTo(panel)


def test_episode_bar_visible_when_multi(qapp):
    p = Project(episodes=[Episode(name="一"), Episode(name="二")])
    panel = LeftPanel()
    panel.set_project(p)
    assert panel._episode_bar.isVisibleTo(panel)
    assert [panel.combo_episode.itemText(i) for i in range(panel.combo_episode.count())] == ["一", "二"]


def test_combo_switch_updates_active_and_scene_list(qapp):
    e1 = Episode(name="一", scenes=[Scene(id="A")])
    e2 = Episode(name="二", scenes=[Scene(id="B"), Scene(id="C")])
    p = Project(episodes=[e1, e2])
    panel = LeftPanel()
    panel.set_project(p)
    fired = []
    panel.episode_switched.connect(fired.append)

    panel.combo_episode.setCurrentIndex(1)
    assert p.active_episode_index == 1
    assert fired == [1]
    assert panel.scene_list.count() == 2  # 已切到第二集的場景


def test_add_episode_switches_and_reveals_bar(qapp, monkeypatch):
    monkeypatch.setattr(
        QInputDialog, "getText",
        staticmethod(lambda *a, **kw: ("第二集", True)),
    )
    p = Project()
    panel = LeftPanel()
    panel.set_project(p)
    fired = []
    panel.episodes_changed.connect(lambda: fired.append(1))

    panel.add_episode()
    assert [e.name for e in p.episodes] == ["影片1", "第二集"]
    assert p.active_episode_index == 1
    assert panel._episode_bar.isVisibleTo(panel)
    assert fired == [1]


def test_remove_episode_with_confirm(qapp, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )
    p = Project(episodes=[Episode(name="一"), Episode(name="二", scenes=[Scene(id="B")])])
    p.active_episode_index = 1
    panel = LeftPanel()
    panel.set_project(p)

    panel._on_remove_episode()
    assert [e.name for e in p.episodes] == ["一"]
    assert p.active_episode_index == 0
    assert not panel._episode_bar.isVisibleTo(panel)  # 回到單影片 → 隱藏


def test_remove_episode_cancelled(qapp, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No),
    )
    p = Project(episodes=[Episode(name="一"), Episode(name="二")])
    panel = LeftPanel()
    panel.set_project(p)
    panel._on_remove_episode()
    assert len(p.episodes) == 2
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_left_panel_episodes.py -v`
Expected: FAIL（AttributeError: `_episode_bar` / `episode_switched`）

- [ ] **Step 3: 實作**

`src/ui/left_panel.py`：

(a) import：`QMenu` 加入 PyQt6.QtWidgets import 清單；models import 行改為：

```python
from src.core.models import Character, Episode, Project, Scene
```

(b) class 信號區（`costume_edit_requested` 之後）加：

```python
    # 影片（Episode）信號
    episode_switched = pyqtSignal(int)   # 新 active episode index
    episodes_changed = pyqtSignal()      # 新增/改名/刪除影片
```

(c) `_setup_ui` 中 Page 0（`scene_layout.setSpacing(4)` 之後、`self.scene_list = ListWidget()` 之前）插入：

```python
        # 影片切換列（漸進揭露：單支影片時整列隱藏，入口在檔案選單「新增影片」）
        self._episode_bar = QWidget()
        ep_row = QHBoxLayout()
        ep_row.setContentsMargins(0, 0, 0, 0)
        ep_row.setSpacing(4)
        _ep_lbl = QLabel("影片:")
        _ep_lbl.setFixedWidth(56)
        ep_row.addWidget(_ep_lbl)
        self.combo_episode = ComboBox()
        ep_row.addWidget(self.combo_episode, 1)
        self.btn_add_episode = PushButton("＋")
        self.btn_add_episode.setFixedWidth(32)
        self.btn_add_episode.setToolTip("新增影片（共用本作品的角色與素材）")
        ep_row.addWidget(self.btn_add_episode)
        self.btn_episode_menu = PushButton("⋯")
        self.btn_episode_menu.setFixedWidth(32)
        self.btn_episode_menu.setToolTip("重新命名／刪除這支影片")
        ep_row.addWidget(self.btn_episode_menu)
        self._episode_bar.setLayout(ep_row)
        scene_layout.addWidget(self._episode_bar)
```

(d) 信號連接區（`self.btn_add_char.clicked.connect(...)` 之後）加：

```python
        self.combo_episode.currentIndexChanged.connect(self._on_episode_combo_changed)
        self.btn_add_episode.clicked.connect(self.add_episode)
        self.btn_episode_menu.clicked.connect(self._on_episode_menu)
```

(e) `set_project` 改為：

```python
    def set_project(self, project: Project) -> None:
        """綁定 Project，重建 UI。"""
        self._project = project
        self._refresh_episode_bar()
        self._refresh_scene_list()
        self._refresh_character_list()
```

(f) 「場景列表」區段之前新增影片區段方法：

```python
    # ── 影片（Episode）切換 ──

    def _refresh_episode_bar(self) -> None:
        """重建影片下拉選單；單支影片時整列隱藏（漸進揭露）。"""
        self._updating = True
        self.combo_episode.clear()
        if self._project:
            for ep in self._project.episodes:
                self.combo_episode.addItem(ep.name)
            self.combo_episode.setCurrentIndex(self._project.active_episode_index)
        multi = bool(self._project) and len(self._project.episodes) > 1
        self._episode_bar.setVisible(multi)
        self._updating = False

    def _on_episode_combo_changed(self, index: int) -> None:
        if self._updating or not self._project or index < 0:
            return
        self._project.active_episode_index = index
        self._refresh_scene_list()
        self.episode_switched.emit(index)

    def add_episode(self) -> None:
        """新增一支影片並切換過去；公開給檔案選單呼叫。"""
        if not self._project:
            return
        default = self._project.next_episode_name()
        name, ok = QInputDialog.getText(self, "新增影片", "影片名稱：", text=default)
        if not ok:
            return
        self._project.episodes.append(Episode(name=name.strip() or default))
        self._project.active_episode_index = len(self._project.episodes) - 1
        self._refresh_episode_bar()
        self._refresh_scene_list()
        self.episodes_changed.emit()

    def _on_episode_menu(self) -> None:
        menu = QMenu(self)
        act_rename = menu.addAction("重新命名")
        act_delete = menu.addAction("刪除這支影片")
        chosen = menu.exec(
            self.btn_episode_menu.mapToGlobal(self.btn_episode_menu.rect().bottomLeft())
        )
        if chosen == act_rename:
            self._on_rename_episode()
        elif chosen == act_delete:
            self._on_remove_episode()

    def _on_rename_episode(self) -> None:
        if not self._project:
            return
        ep = self._project.active_episode
        name, ok = QInputDialog.getText(self, "重新命名影片", "影片名稱：", text=ep.name)
        if ok and name.strip():
            ep.name = name.strip()
            self._refresh_episode_bar()
            self.episodes_changed.emit()

    def _on_remove_episode(self) -> None:
        if not self._project or len(self._project.episodes) <= 1:
            return  # 最後一支不可刪（按鈕列在單影片時本來就隱藏；此為保險）
        ep = self._project.active_episode
        n_dlg = sum(len(s.dialogues) for s in ep.scenes)
        result = QMessageBox.question(
            self, "刪除影片",
            f"「{ep.name}」含 {len(ep.scenes)} 個場景、{n_dlg} 則對話，將一併刪除。\n"
            "（角色與素材屬於整個作品，不受影響）\n確定刪除？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        idx = self._project.active_episode_index
        self._project.episodes.pop(idx)
        self._project.active_episode_index = max(0, idx - 1)
        self._refresh_episode_bar()
        self._refresh_scene_list()
        self.episodes_changed.emit()
```

- [ ] **Step 4: 跑測試確認通過（含既有 left_panel 測試不退步）**

Run: `.venv\Scripts\python.exe -m pytest tests/test_left_panel_episodes.py tests/test_left_panel_props_sync.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/left_panel.py tests/test_left_panel_episodes.py
git commit -m "feat(ui): 左側面板影片切換列，單影片時隱藏（漸進揭露）"
```

---

### Task 5: MainWindow 接線 + 檔案選單「新增影片」

**Files:**
- Modify: `src/ui/main_window.py`（`_setup_menu` 檔案選單、`_connect_signals`、新增兩個 slot）
- Test: Create `tests/test_main_window_episodes.py`

- [ ] **Step 1: 寫失敗測試**

新檔 `tests/test_main_window_episodes.py`：

```python
"""MainWindow 與影片切換的整合：切換後中央面板重新綁定、dirty 標記。"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QInputDialog

from src.core.models import Dialogue, Episode, Project, Scene
from src.ui.main_window import MainWindow


@pytest.fixture
def window(qapp):
    w = MainWindow()
    yield w
    w.center_panel.cleanup()
    w.deleteLater()


def test_switch_episode_rebinds_center_panel(window):
    e1 = Episode(name="一", scenes=[Scene(id="A", dialogues=[Dialogue(type="narration", text="x")])])
    e2 = Episode(name="二", scenes=[Scene(id="B")])
    window._project = Project(episodes=[e1, e2])
    window._rebuild_ui()

    window.left_panel.combo_episode.setCurrentIndex(1)
    # 中央面板的當前場景應屬於第二集
    assert window.center_panel._get_current_scene().id == "B"
    assert window._dirty


def test_menu_add_episode_creates_and_marks_dirty(window, monkeypatch):
    monkeypatch.setattr(
        QInputDialog, "getText",
        staticmethod(lambda *a, **kw: ("續集", True)),
    )
    window._dirty = False
    window._on_add_episode_menu()
    assert [e.name for e in window._project.episodes] == ["影片1", "續集"]
    assert window._project.active_episode_index == 1
    assert window._dirty
```

（`center_panel._get_current_scene()` 為既有方法，見 `src/ui/center_panel.py:426`。）

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main_window_episodes.py -v`
Expected: FAIL（`_on_add_episode_menu` 不存在；切換後 center_panel 未重綁）

- [ ] **Step 3: 實作**

`src/ui/main_window.py`：

(a) `_setup_menu` 檔案選單：`act_paste.setShortcut(...)` 的下一行**已有** `file_menu.addSeparator()`（main_window.py:100），在該既有分隔線之後插入（沿用它，避免雙分隔線）：

```python
        add_action(file_menu, "add", "新增影片", self._on_add_episode_menu)
        file_menu.addSeparator()
```

(b) `_connect_signals` 場景信號區之後加：

```python
        # 左側面板 → 影片切換
        self.left_panel.episode_switched.connect(self._on_episode_changed)
        self.left_panel.episodes_changed.connect(self._on_episode_changed)
```

(c) 「── 場景切換 ──」區段之前加兩個 slot：

```python
    # ── 影片（Episode）──

    def _on_episode_changed(self, _index: int = -1) -> None:
        """影片切換/增刪後：中央面板重綁到新場景列表，並標記變更。"""
        self.center_panel.set_project(self._project)
        self._on_project_changed()

    def _on_add_episode_menu(self) -> None:
        self.left_panel.add_episode()
```

(d) `_check_export_ready` 文案改以「目前影片」為主詞（多影片作品下「專案中沒有場景」會誤導——別支影片可能有場景）：

```python
    def _check_export_ready(self) -> bool:
        if not self._project.scenes:
            dialogs.show_error(
                self, "無法導出", "目前影片沒有任何場景。\n請先新增場景。"
            )
            return False
        if not self._has_dialogues():
            dialogs.show_error(
                self, "無法導出", "目前影片的所有場景都沒有對話。\n請先匯入文字或新增對話。"
            )
            return False
        return True
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main_window_episodes.py tests/test_main_window_remove_character.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/main_window.py tests/test_main_window_episodes.py
git commit -m "feat(ui): 影片切換接線與檔案選單「新增影片」"
```

---

### Task 6: `character_transfer.py` — 跨作品角色搬運核心

**Files:**
- Create: `src/core/character_transfer.py`
- Test: Create `tests/test_character_transfer.py`

- [ ] **Step 1: 寫失敗測試**

新檔 `tests/test_character_transfer.py`：

```python
"""character_transfer：檔案去重複製、角色搬運（filename 改寫、缺檔回報）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.character_transfer import copy_file_dedup, import_character
from src.core.models import Character, Costume, SpriteVariant


class TestCopyFileDedup:
    def test_copies_new_file(self, tmp_path):
        src = tmp_path / "a.png"
        src.write_bytes(b"data")
        target = tmp_path / "assets"
        assert copy_file_dedup(src, target) == "a.png"
        assert (target / "a.png").read_bytes() == b"data"

    def test_same_content_reuses_existing(self, tmp_path):
        src = tmp_path / "a.png"
        src.write_bytes(b"data")
        target = tmp_path / "assets"
        target.mkdir()
        (target / "a.png").write_bytes(b"data")
        assert copy_file_dedup(src, target) == "a.png"
        assert list(target.iterdir()) == [target / "a.png"]  # 沒有 a_1.png

    def test_different_content_adds_suffix(self, tmp_path):
        src = tmp_path / "a.png"
        src.write_bytes(b"new")
        target = tmp_path / "assets"
        target.mkdir()
        (target / "a.png").write_bytes(b"old")
        assert copy_file_dedup(src, target) == "a_1.png"
        assert (target / "a.png").read_bytes() == b"old"   # 既有檔不被覆寫
        assert (target / "a_1.png").read_bytes() == b"new"


class TestImportCharacter:
    def _char(self) -> Character:
        return Character(name="小美", name_color="#E05555", costumes=[
            Costume(name="校服", expressions=[
                SpriteVariant("微笑", "smile.png"),
                SpriteVariant("生氣", "angry.png"),
            ]),
        ])

    def test_copies_sprites_and_returns_new_character(self, tmp_path):
        src_assets = tmp_path / "src"
        src_assets.mkdir()
        (src_assets / "smile.png").write_bytes(b"s")
        (src_assets / "angry.png").write_bytes(b"a")
        target = tmp_path / "dst"

        original = self._char()
        new_char, missing = import_character(original, src_assets, target)
        assert missing == []
        assert (target / "smile.png").exists()
        assert (target / "angry.png").exists()
        assert new_char is not original           # 深拷貝
        assert original.costumes[0].expressions[0].filename == "smile.png"  # 原物件不動

    def test_conflict_rewrites_filename(self, tmp_path):
        src_assets = tmp_path / "src"
        src_assets.mkdir()
        (src_assets / "smile.png").write_bytes(b"from-source")
        (src_assets / "angry.png").write_bytes(b"a")
        target = tmp_path / "dst"
        target.mkdir()
        (target / "smile.png").write_bytes(b"already-here")

        new_char, _ = import_character(self._char(), src_assets, target)
        filenames = [e.filename for e in new_char.costumes[0].expressions]
        assert "smile_1.png" in filenames  # 衝突改名且寫回 Character

    def test_missing_source_file_reported(self, tmp_path):
        src_assets = tmp_path / "src"
        src_assets.mkdir()
        (src_assets / "smile.png").write_bytes(b"s")
        # angry.png 缺檔

        new_char, missing = import_character(self._char(), src_assets, tmp_path / "dst")
        assert missing == ["angry.png"]
        # 缺檔差分保留原 filename，不複製
        assert new_char.costumes[0].expressions[1].filename == "angry.png"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_transfer.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 實作**

新檔 `src/core/character_transfer.py`：

```python
"""跨作品角色搬運：從其他作品（.vnsproj）讀出的角色複製進目標專案。

純邏輯模組（無 Qt）。「角色卡」概念對使用者不可見；
.vncard 分享格式（character_library.py）為獨立休眠後端，與此模組無耦合。
"""

from __future__ import annotations

import copy
from pathlib import Path

from src.core.models import Character


def copy_file_dedup(src: Path, target_dir: Path) -> str:
    """把 src 複製進 target_dir：同名同內容重用既有檔；同名異內容加 _1, _2… 後綴。

    Returns:
        最終落在 target_dir 內的檔名。
    """
    src = Path(src)
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    dest = target_dir / src.name
    counter = 1
    while dest.exists() and dest.read_bytes() != data:
        dest = target_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    if not dest.exists():
        dest.write_bytes(data)
    return dest.name


def import_character(
    char: Character, source_assets: Path, target_assets: Path
) -> tuple[Character, list[str]]:
    """深拷貝角色並把引用的立繪複製到 target_assets。

    Returns:
        (filename 已改寫的新 Character, 來源缺檔清單)
        缺檔差分保留原 filename 不複製，由呼叫端決定如何提示。
    """
    source_assets = Path(source_assets)
    new_char = copy.deepcopy(char)
    missing: list[str] = []
    for costume in new_char.costumes:
        for sv in costume.expressions:
            if not sv.filename:
                continue
            src_file = source_assets / sv.filename
            if not src_file.is_file():
                missing.append(sv.filename)
                continue
            sv.filename = copy_file_dedup(src_file, target_assets)
    return new_char, missing
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_transfer.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/character_transfer.py tests/test_character_transfer.py
git commit -m "feat(core): character_transfer 跨作品角色搬運（內容去重、缺檔回報）"
```

---

### Task 7: 「從其他作品匯入角色」UI

**Files:**
- Create: `src/ui/character_import.py`
- Modify: `src/ui/left_panel.py`（角色頁加按鈕）、`src/ui/main_window.py`（handler）
- Test: Create `tests/test_character_import.py`

- [ ] **Step 1: 寫失敗測試**

新檔 `tests/test_character_import.py`：

```python
"""CharacterImportDialog 勾選器 + MainWindow 匯入 handler。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from src.core.models import Character, Costume, Episode, Project, Scene, SpriteVariant
from src.core.project_io import save_project


def _source_project(tmp_path: Path) -> Path:
    """造一個含兩個角色的來源作品（立繪用 Pillow 產生，確保是合法 PNG）。"""
    from PIL import Image

    src_dir = tmp_path / "source_work"
    (src_dir / "assets").mkdir(parents=True)
    Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(src_dir / "assets" / "mei.png")
    p = Project(title="來源作品", characters=[
        Character(name="小美", name_color="#E05555", costumes=[
            Costume(name="校服", expressions=[SpriteVariant("微笑", "mei.png")]),
        ]),
        Character(name="小明", name_color="#336699", costumes=[]),
    ])
    proj_file = src_dir / "source.vnsproj"
    p.project_path = proj_file  # 先定位來源目錄，避免 save_project 把 %TEMP% 未存檔素材複製進來
    save_project(p, proj_file)
    return proj_file


def test_dialog_lists_characters_checked_by_default(qapp, tmp_path):
    from src.core.project_io import load_project
    from src.ui.character_import import CharacterImportDialog

    proj_file = _source_project(tmp_path)
    source = load_project(proj_file)
    dlg = CharacterImportDialog(source, proj_file.parent / "assets")
    assert dlg._char_list.count() == 2
    assert "小美" in dlg._char_list.item(0).text()
    assert dlg._char_list.item(0).checkState() == Qt.CheckState.Checked
    assert len(dlg.selected_characters()) == 2

    dlg._char_list.item(1).setCheckState(Qt.CheckState.Unchecked)
    assert [c.name for c in dlg.selected_characters()] == ["小美"]


def test_main_window_import_flow(qapp, tmp_path, monkeypatch):
    from src.ui.main_window import MainWindow
    import src.ui.character_import as ci

    proj_file = _source_project(tmp_path)
    w = MainWindow()
    try:
        # 目標專案存到磁碟（決定 assets 目錄）
        target_file = tmp_path / "target" / "t.vnsproj"
        target_file.parent.mkdir(parents=True)
        monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **kw: None))
        w._project.project_path = target_file

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **kw: (str(proj_file), "")),
        )
        monkeypatch.setattr(ci.CharacterImportDialog, "exec", lambda self: QDialog.DialogCode.Accepted)

        w._on_import_characters_from_work()
        names = [c.name for c in w._project.characters]
        assert names == ["小美", "小明"]
        assert (target_file.parent / "assets" / "mei.png").exists()
        assert "mei.png" in w._project.assets["sprites"]
    finally:
        w.center_panel.cleanup()
        w.deleteLater()


def test_same_name_skip_on_no(qapp, tmp_path, monkeypatch):
    from src.ui.main_window import MainWindow
    import src.ui.character_import as ci

    proj_file = _source_project(tmp_path)
    w = MainWindow()
    try:
        w._project.project_path = tmp_path / "t2" / "t.vnsproj"
        w._project.project_path.parent.mkdir(parents=True)
        w._project.characters.append(Character(name="小美", name_color="#000000"))

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **kw: (str(proj_file), "")),
        )
        monkeypatch.setattr(ci.CharacterImportDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No))
        monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **kw: None))

        w._on_import_characters_from_work()
        # 小美被略過（保留原本黑色版本），小明照常匯入
        mei = [c for c in w._project.characters if c.name == "小美"]
        assert len(mei) == 1 and mei[0].name_color == "#000000"
        assert any(c.name == "小明" for c in w._project.characters)
    finally:
        w.center_panel.cleanup()
        w.deleteLater()
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_import.py -v`
Expected: FAIL（ModuleNotFoundError: src.ui.character_import）

- [ ] **Step 3: 實作選擇器對話框**

新檔 `src/ui/character_import.py`：

```python
"""「從其他作品匯入角色」對話框：列出來源作品的角色，勾選後匯入。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import BodyLabel, ListWidget, StrongBodyLabel

from src.core.models import Character, Project


def _char_thumb(char: Character, assets_dir: Path) -> QPixmap:
    """角色縮圖：第一張立繪縮放 40px；無立繪用名牌色色塊。"""
    if char.sprites:
        path = assets_dir / char.sprites[0].filename
        if path.exists():
            pm = QPixmap(str(path))
            if not pm.isNull():
                return pm.scaled(
                    40, 40,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
    pm = QPixmap(40, 40)
    pm.fill(QColor(char.name_color))
    return pm


class CharacterImportDialog(QDialog):
    """勾選來源作品中要帶進本作品的角色（預設全勾）。"""

    def __init__(self, source_project: Project, source_assets: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self._chars = source_project.characters
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(f"從「{source_project.title}」匯入角色")
        self.setMinimumSize(380, 360)

        layout = QVBoxLayout()
        layout.addWidget(StrongBodyLabel("勾選要帶進本作品的角色："))
        self._char_list = ListWidget()
        self._char_list.setIconSize(QSize(40, 40))
        for char in self._chars:
            item = QListWidgetItem(
                f"{char.name}（{len(char.costumes)} 套服裝 · {len(char.sprites)} 張差分）"
            )
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setIcon(QIcon(_char_thumb(char, Path(source_assets))))
            self._char_list.addItem(item)
        layout.addWidget(self._char_list)
        layout.addWidget(BodyLabel("匯入會把角色連同立繪複製進本作品，之後與來源作品互不影響。"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def selected_characters(self) -> list[Character]:
        return [
            c for i, c in enumerate(self._chars)
            if self._char_list.item(i).checkState() == Qt.CheckState.Checked
        ]
```

- [ ] **Step 4: LeftPanel 加入口按鈕**

`src/ui/left_panel.py` `_setup_ui` Page 1，`char_layout.addWidget(self.btn_add_char)` 之後插入：

```python
        self.btn_import_char = QPushButton(" 從其他作品匯入…")
        self.btn_import_char.setObjectName("dashedButton")
        self.btn_import_char.setIcon(themed_icon("open"))
        self.btn_import_char.setIconSize(QSize(16, 16))
        self.btn_import_char.setToolTip("把另一個作品做好的角色（含立繪）複製進來")
        char_layout.addWidget(self.btn_import_char)
```

class 信號區（`episodes_changed` 之後）加：

```python
    # 角色匯入信號
    character_import_requested = pyqtSignal()
```

信號連接區加：

```python
        self.btn_import_char.clicked.connect(self.character_import_requested.emit)
```

- [ ] **Step 5: MainWindow handler**

`src/ui/main_window.py`：

(a) `_connect_signals` 角色操作區加：

```python
        self.left_panel.character_import_requested.connect(self._on_import_characters_from_work)
```

(b) `_on_costume_edit` 之後加：

```python
    def _on_import_characters_from_work(self) -> None:
        """從另一個 .vnsproj 挑角色複製進本作品（含立繪；同名詢問取代或略過）。"""
        from src.core.character_transfer import import_character
        from src.ui.character_import import CharacterImportDialog

        path_str, _ = QFileDialog.getOpenFileName(
            self, "選擇作品檔", "",
            "VisualNovel Studio 專案 (*.vnsproj);;所有檔案 (*)",
        )
        if not path_str:
            return
        src_path = Path(path_str)
        try:
            source = load_project(src_path)
        except (OSError, ValueError, KeyError) as e:
            dialogs.show_error(self, "開啟失敗", f"無法讀取作品檔：\n{e}")
            return
        if not source.characters:
            dialogs.show_info(self, "沒有角色", f"「{source.title}」裡沒有任何角色。")
            return

        source_assets = src_path.parent / "assets"
        dlg = CharacterImportDialog(source, source_assets, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        target_assets = self._get_project_dir() / "assets"
        existing = {c.name: i for i, c in enumerate(self._project.characters)}
        imported = 0
        all_missing: list[str] = []
        for char in dlg.selected_characters():
            if char.name in existing:
                ret = QMessageBox.question(
                    self, "同名角色",
                    f"本作品已有角色「{char.name}」。要用匯入的版本取代嗎？\n"
                    "（選「No」會跳過這個角色）",
                )
                if ret != QMessageBox.StandardButton.Yes:
                    continue
            new_char, missing = import_character(char, source_assets, target_assets)
            all_missing.extend(missing)
            if new_char.name in existing:
                self._project.characters[existing[new_char.name]] = new_char
            else:
                self._project.characters.append(new_char)
                existing[new_char.name] = len(self._project.characters) - 1
            for sv in new_char.sprites:
                if sv.filename and sv.filename not in self._project.assets["sprites"]:
                    self._project.assets["sprites"].append(sv.filename)
            imported += 1

        if all_missing:
            dialogs.show_info(
                self, "部分立繪遺失",
                "下列立繪在來源作品中找不到，已略過：\n"
                + "\n".join(f"・{m}" for m in sorted(set(all_missing))),
            )
        if imported:
            self.left_panel.refresh_characters()
            self.center_panel.refresh()
            self._on_project_changed()
```

(c) 檔頭 import 補 `QDialog`（加進既有 PyQt6.QtWidgets import 清單）。

- [ ] **Step 6: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_import.py -v`
Expected: 全 PASS

- [ ] **Step 7: Commit**

```bash
git add src/ui/character_import.py src/ui/left_panel.py src/ui/main_window.py tests/test_character_import.py
git commit -m "feat(ui): 從其他作品匯入角色（勾選器+立繪複製+同名詢問）"
```

---

### Task 8: 移除角色卡 UI（S6）+ CostumeEditor 防陷阱（S7/S8）

**Files:**
- Modify: `src/ui/dialogs.py`（`CharacterEditorDialog` 移除卡片相關；`CostumeEditorDialog` 加 `_ensure_costume` 與移除確認）
- Modify: `tests/test_character_editor_dialog.py`（刪卡片測試）
- Test: Create `tests/test_costume_editor.py`

- [ ] **Step 1: 寫 CostumeEditor 失敗測試**

新檔 `tests/test_costume_editor.py`：

```python
"""CostumeEditorDialog：零服裝自動建服裝、移除確認。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from src.core.models import Character, Costume, SpriteVariant
from src.ui.dialogs import CostumeEditorDialog


def _png(tmp_path: Path, name: str = "pic.png") -> Path:
    """用 Pillow 產生合法 PNG——拖入流程會經 normalize_sprite 的 Pillow 解碼，假 bytes 會炸。"""
    from PIL import Image

    p = tmp_path / name
    Image.new("RGBA", (4, 4), (120, 160, 200, 255)).save(p)
    return p


def test_drop_image_on_empty_character_creates_costume(qapp, tmp_path, monkeypatch):
    """零服裝時拖圖進來 → 自動建「服裝1」並收下差分（修走查陷阱 P6）。"""
    monkeypatch.setattr(
        QInputDialog, "getText",
        staticmethod(lambda *a, **kw: ("微笑", True)),
    )
    char = Character(name="小美", costumes=[])
    dlg = CostumeEditorDialog(char, tmp_path)
    dlg._on_files_dropped([_png(tmp_path)])

    costumes = dlg.get_costumes()
    assert len(costumes) == 1
    assert costumes[0].name == "服裝1"
    assert [e.label for e in costumes[0].expressions] == ["微笑"]


def test_ensure_costume_reuses_existing(qapp, tmp_path):
    char = Character(name="小美", costumes=[Costume(name="校服")])
    dlg = CostumeEditorDialog(char, tmp_path)
    assert dlg._ensure_costume() == 0
    assert len(dlg.get_costumes()) == 1


def test_remove_costume_with_expressions_asks(qapp, tmp_path, monkeypatch):
    """移除含差分的服裝 → 跳確認；按 No 不刪（修走查陷阱 P7）。"""
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No),
    )
    char = Character(name="小美", costumes=[
        Costume(name="校服", expressions=[SpriteVariant("微笑", "a.png")]),
    ])
    dlg = CostumeEditorDialog(char, tmp_path)
    dlg._costume_list.setCurrentRow(0)
    dlg._on_remove_costume()
    assert len(dlg.get_costumes()) == 1


def test_remove_empty_costume_no_confirm(qapp, tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: asked.append(1) or QMessageBox.StandardButton.Yes),
    )
    char = Character(name="小美", costumes=[Costume(name="空服裝")])
    dlg = CostumeEditorDialog(char, tmp_path)
    dlg._costume_list.setCurrentRow(0)
    dlg._on_remove_costume()
    assert asked == []
    assert dlg.get_costumes() == []
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_costume_editor.py -v`
Expected: FAIL（`_ensure_costume` 不存在；零服裝 drop 靜默 return；移除無確認）

- [ ] **Step 3: 實作 CostumeEditor 修補**

`src/ui/dialogs.py` `CostumeEditorDialog`：

(a) `_on_add_costume` 之前加：

```python
    def _ensure_costume(self) -> int:
        """確保至少有一套服裝（無則自動建「服裝1」）；回傳目前選中的服裝索引。"""
        if not self._costumes:
            self._costumes.append(Costume(name="服裝1"))
            self._populate_costume_list()
        row = self._costume_list.currentRow()
        if row < 0:
            self._costume_list.setCurrentRow(0)
            row = 0
        return row
```

(b) `_on_add_expression` 開頭（原 `cos_row = self._costume_list.currentRow()` 與越界 return 兩行）改為：

```python
    def _on_add_expression(self) -> None:
        cos_row = self._ensure_costume()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇差分圖片", "", "圖片 (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        self._import_expression(cos_row, Path(file_path))
```

(c) `_on_files_dropped` 開頭同樣改用 `_ensure_costume`：

```python
    def _on_files_dropped(self, paths: list[Path]) -> None:
        """拖曳圖片到右側面板時批量匯入；零服裝時自動建服裝1。"""
        cos_row = self._ensure_costume()
        for p in paths:
            if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                self._import_expression(cos_row, p)
```

(d) `_on_remove_costume` 改為：

```python
    def _on_remove_costume(self) -> None:
        row = self._costume_list.currentRow()
        if not (0 <= row < len(self._costumes)):
            return
        cos = self._costumes[row]
        if cos.expressions:
            ret = QMessageBox.question(
                self, "移除服裝",
                f"「{cos.name}」內含 {len(cos.expressions)} 張立繪差分，確定一併移除？",
            )
            if ret != QMessageBox.StandardButton.Yes:
                return
        self._costumes.pop(row)
        self._populate_costume_list()
```

- [ ] **Step 4: 移除 CharacterEditorDialog 的角色卡 UI**

`src/ui/dialogs.py` `CharacterEditorDialog`，全部刪除以下內容：

1. `__init__` 中兩行（含註解）：

```python
        # C6：若透過角色卡匯入，除主立繪外還可能夾帶額外差分，存在這裡作為 get_character() 的 costumes 輸出
        self._extra_costumes: list[Costume] = []
        self._loaded_from_card: bool = False
```

2. `_setup_ui` 中整段「C6 角色卡按鈕列」（`card_row = QHBoxLayout()` 至 `layout.addLayout(card_row)`）。
3. `_on_clear_sprite` 尾端兩行：

```python
        self._extra_costumes = []
        self._loaded_from_card = False
```

4. 整個 `_on_import_card` 與 `_on_export_card` 方法（含「── C6：角色卡匯入 / 匯出 ──」區段註解）。
5. `_on_export_card` 對應的 `_on_export_card` 檢查條件中曾引用 `_extra_costumes`——隨方法一併刪除。
6. `get_character` 開頭「情境 1」分支整段刪除：

```python
        # 情境 1：角色卡匯入 → 保留卡內所有服裝（現行行為不變）
        if self._loaded_from_card and self._extra_costumes:
            return Character(name=name, name_color=color, costumes=list(self._extra_costumes))
```

並把其後註解「情境 2」「情境 3」改為「情境 1」「情境 2」。
7. class docstring 改為：

```python
    """新增或編輯角色：名稱、名牌顏色、預設立繪；支援拖曳圖片匯入。"""
```

同時刪除 `tests/test_character_editor_dialog.py` 中的 `test_card_import_preserves_extra_costumes` 測試（連同其區段註解）。

- [ ] **Step 5: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_costume_editor.py tests/test_character_editor_dialog.py tests/test_character_library.py -v`
Expected: 全 PASS（`test_character_library.py` 為休眠後端的既有測試，必須維持綠）

- [ ] **Step 6: Commit**

```bash
git add src/ui/dialogs.py tests/test_costume_editor.py tests/test_character_editor_dialog.py
git commit -m "feat(dialogs): 移除角色卡 UI；服裝編輯器零服裝自動建服裝、移除前確認"
```

---

### Task 9: 編輯角色框顯示服裝摘要（S9）

**Files:**
- Modify: `src/ui/dialogs.py`（import、`_setup_ui`、`_load_character`）
- Test: `tests/test_character_editor_dialog.py`

- [ ] **Step 1: 寫失敗測試**

加到 `tests/test_character_editor_dialog.py` 尾端：

```python
# ── 服裝摘要標籤（修走查陷阱 P8：多服裝角色其餘資料隱形）──

def test_summary_label_visible_for_multi_costume_char(qapp, tmp_path):
    char = _make_multi_costume_char()  # 2 套服裝 / 3 張差分（檔案開頭已定義）
    dlg = CharacterEditorDialog(character=char, project_dir=tmp_path)
    assert dlg._lbl_costume_summary.isVisibleTo(dlg)
    assert "2 套服裝" in dlg._lbl_costume_summary.text()
    assert "3 張差分" in dlg._lbl_costume_summary.text()


def test_summary_label_hidden_for_single_sprite_char(qapp, tmp_path):
    char = Character(name="單圖", costumes=[
        Costume(name="服裝1", expressions=[SpriteVariant("正面", "a.png")]),
    ])
    dlg = CharacterEditorDialog(character=char, project_dir=tmp_path)
    assert not dlg._lbl_costume_summary.isVisibleTo(dlg)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v -k summary`
Expected: FAIL（AttributeError: `_lbl_costume_summary`）

- [ ] **Step 3: 實作**

(a) `src/ui/dialogs.py` 檔頭 qfluentwidgets import 行改為：

```python
from qfluentwidgets import BodyLabel, ComboBox, LineEdit, ListWidget, PushButton, StrongBodyLabel
```

(b) `_setup_ui` 中 `layout.addWidget(sprite_group)` 之後插入：

```python
        # 多服裝角色提示：避免新手以為角色只有這一張圖
        self._lbl_costume_summary = BodyLabel("")
        self._lbl_costume_summary.setWordWrap(True)
        self._lbl_costume_summary.setVisible(False)
        layout.addWidget(self._lbl_costume_summary)
```

(c) `_load_character` 尾端加：

```python
        total = len(char.sprites)
        if total > 1:
            self._lbl_costume_summary.setText(
                f"此角色共有 {len(char.costumes)} 套服裝、{total} 張差分。"
                "這裡只更換預設立繪；完整管理請用角色面板的「編輯服裝…」。"
            )
            self._lbl_costume_summary.setVisible(True)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/dialogs.py tests/test_character_editor_dialog.py
git commit -m "feat(dialogs): 編輯角色框顯示服裝差分摘要"
```

---

### Task 10: 使用教學文案（S10）

**Files:**
- Modify: `src/ui/main_window.py`（`_on_show_tutorial`，現第 358–375 行）

- [ ] **Step 1: 修改教學文字**

`_on_show_tutorial` 整個函式改為：

```python
    def _on_show_tutorial(self) -> None:
        QMessageBox.information(
            self, "使用教學",
            "VisualNovel Studio 使用教學\n\n"
            "1. 新增專案或匯入文字\n"
            "2. 在場景列表中管理場景，設定背景、BGM、特效\n"
            "3. 在角色列表中新增角色，設定名稱、顏色、立繪差分\n"
            "   ・「從其他作品匯入」可直接帶入以前做好的角色\n"
            "4. 在文字列表中編輯文字，指定角色與差分\n"
            "5. 預覽畫面即時顯示效果\n"
            "6. 完成後導出為影片 (MP4) 或網頁 (ZIP/HTML)\n"
            "7. 做續集？「檔案 > 新增影片」在同一作品裡開新影片，\n"
            "   角色與素材自動共用，各支影片獨立導出\n\n"
            "快捷鍵：\n"
            "  Ctrl+N/O/S — 新增/開啟/儲存專案\n"
            "  Delete — 刪除選取的句子\n"
            "  雙擊台詞 — 編輯文字\n"
            "  右鍵台詞列 — 插入/刪除句子\n"
            "  Ctrl+C — 複製句子文字\n"
            "  Ctrl+Shift+V — 貼上文字（也可走 檔案 > 貼上文字）"
        )
```

- [ ] **Step 2: 跑全測試確認沒弄壞**

Run: `.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: 全 PASS

- [ ] **Step 3: Commit**

```bash
git add src/ui/main_window.py
git commit -m "docs(ui): 使用教學補影片（續集）與跨作品匯入角色說明"
```

---

### Task 11: 收尾——全測試、開發紀錄、合併

**Files:**
- Modify: `docs/DEVELOPMENT_HISTORY.md`

- [ ] **Step 1: 跑全測試**

Run: `.venv\Scripts\python.exe -m pytest tests/ -v`（`QT_QPA_PLATFORM=offscreen`）
Expected: 全 PASS，0 failed

- [ ] **Step 2: 追加開發紀錄**

在 `docs/DEVELOPMENT_HISTORY.md` 文件尾端追加（日期用實際完成日）：

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add docs/DEVELOPMENT_HISTORY.md
git commit -m "docs: 追加作品/影片兩層結構與跨作品角色復用紀錄"
```

- [ ] **Step 4: 合併（依專案分支工作流）**

使用 superpowers:finishing-a-development-branch skill 處理合併（merge 到 main 前確認 `pytest tests/` 全綠）。

---

## 自我審查紀錄

- **Spec 覆蓋**：S1→Task 1/3/4（含導出：exporter 經 `project.scenes` property 取得目前影片，`test_to_script_json_exports_active_episode_only` 守護）、S2→1/2/3、S3→4/5、S5→6/7、S6→8、S7/S8→8、S9→9、S10→10（S4 已依審查刪除）。
- **型別一致性**：`Episode(name, scenes, group)` 在 Task 1 定義，Task 2–5/7 的用法一致；`episode_switched`/`episodes_changed`/`character_import_requested` 信號（Task 4 宣告）與 Task 5/7 接線一致；`copy_file_dedup`/`import_character`（Task 6）與 Task 7 handler 簽名一致；`_ensure_costume`（Task 8）僅 CostumeEditor 內部使用。
- **順序依賴**：Task 2 必須緊跟 Task 1（中間全測試是紅的）；Task 7 依賴 Task 4 宣告的信號與 Task 6 的核心函式；其餘任務獨立。
- **已知取捨**：同名角色匯入只提供「取代/略過」二選（不做改名匯入，YAGNI）；`_update_title` 不顯示影片名（YAGNI）；v1→v2 為單向升級；不預留 Episode 分組欄位（未知 key 相容，未來免遷移）。
- **2026-06-11 子代理驗證紀錄**：技術查核（對照真實程式碼 + 實際執行 dataclass property / ComboBox 信號 / PNG 解碼）與 Karpathy 準則審查各一輪。已修正：壞 PNG bytes 改 Pillow 產圖（原 hex 的 IDAT CRC 錯誤會讓 Task 8 測試永遠紅）、Task 2 呼叫點清單（補 1 漏、刪 4 誤列、行號校正）、移除 Episode.group 與 active_episode 防呆 getter（投機設計）、檔案選單雙分隔線、_check_export_ready 文案、Task 7 信號宣告歸位、測試暫存目錄污染。
