# 角色卡與角色設定 UX 改進實作計畫

> **已取代（superseded）**：設計方向變更為「作品/影片兩層 + 從其他作品匯入角色」，改由 `2026-06-11-episodes-and-character-reuse.md` 執行。本文件僅保留走查紀錄價值。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 補齊角色卡的生命週期管理（更新／刪除／預覽／外部匯入），並修掉新手走查證實的 6 個 UX 陷阱。

**Architecture:** 核心層（`src/core/character_library.py`）先補 overwrite、去重、卡片資訊讀取、外部卡匯入四個純函式能力；UI 層新增 `CharacterCardManagerDialog`（角色卡庫對話框，含縮圖列表）取代原本的原生檔案對話框，並在 `CharacterEditorDialog` / `CostumeEditorDialog` 上修補確認提示與孤兒檔清理。核心與 UI 嚴格分離（專案開發原則 #4）。

**Tech Stack:** Python 3.12 + PyQt6 + qfluentwidgets；測試用 pytest（`QT_QPA_PLATFORM=offscreen`），UI 測試沿用 `tests/conftest.py` 的 session-scope `qapp` fixture。

---

## 走查證實的問題清單（本計畫的 spec）

來源：2026-06-11 新手視角 offscreen 走查（`build/uxtest/novice_walkthrough.py`）+ 架構審查。

| # | 問題 | 對應 Task |
|---|------|----------|
| P1 | 角色卡庫空時按「從角色卡匯入…」直接 return，無法選取電腦裡的外部 .vncard | Task 5, 6, 7 |
| P2 | 重存同名角色卡不是更新而是複製出 `小美_1.vncard`，庫被舊版塞滿 | Task 1, 9 |
| P3 | 匯入卡後按「取消」，立繪孤兒檔留在專案 assets | Task 8 |
| P4 | 同一張卡重複匯入會複製出 `xxx_1.png` 重複素材（無內容去重） | Task 3 |
| P5 | 匯入卡無預警覆蓋正在編輯的名稱／顏色／立繪 | Task 7 |
| P6 | 零服裝角色在服裝編輯器按「新增差分」靜默無反應 | Task 10 |
| P7 | 移除整套服裝（含差分）零確認 | Task 11 |
| P8 | 編輯多服裝角色時對話框只顯示一張「預設立繪」，其餘服裝差分隱形 | Task 12 |
| P9 | `save_card` 遇缺圖靜默跳過，可能存出缺圖卡 | Task 2, 9 |
| P10 | 選卡時只有檔名可看，沒有角色縮圖／資訊 | Task 4, 6 |
| P11 | 使用教學沒提角色卡；卡片按鈕無 tooltip | Task 13 |

## 檔案結構

| 檔案 | 動作 | 職責 |
|------|------|------|
| `src/core/character_library.py` | 修改 | 補 overwrite / find_existing_card / collect_missing_assets / 去重 / read_card_info / import_card_file |
| `src/ui/card_manager.py` | **新增** | `CharacterCardManagerDialog`：角色卡庫的瀏覽、選取匯入、刪除、外部加入 |
| `src/ui/dialogs.py` | 修改 | `CharacterEditorDialog`（匯入/匯出流程、取消清理、摘要標籤）、`CostumeEditorDialog`（自動建服裝、移除確認） |
| `src/ui/main_window.py` | 修改 | 使用教學文案補角色卡 |
| `tests/test_character_library.py` | 修改 | Task 1–5 的核心測試 |
| `tests/test_card_manager.py` | **新增** | Task 6 的對話框測試 |
| `tests/test_character_editor_dialog.py` | 修改 | Task 7–9、12 的 UI 測試 |
| `tests/test_costume_editor.py` | **新增** | Task 10–11 的 UI 測試 |
| `docs/DEVELOPMENT_HISTORY.md` | 修改 | 收尾摘要 |

## 開工前

- [ ] **Step 0: 建分支**

```bash
git checkout -b feature/character-card-ux
```

---

### Task 1: `save_card` 支援覆寫更新 + `find_existing_card`

解 P2 的核心半邊：讓「更新既有卡」成為可能。

**Files:**
- Modify: `src/core/character_library.py`（`save_card`，約第 35–75 行）
- Test: `tests/test_character_library.py`

- [ ] **Step 1: 寫失敗測試**

加到 `tests/test_character_library.py` 的 `TestSaveListLoad` class 內：

```python
    def test_save_overwrite_replaces_existing(self, tmp_path: Path):
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")

        card_dir = tmp_path / "cards"
        first = save_card(_build_character("小美"), assets, target_dir=card_dir)
        second = save_card(_build_character("小美"), assets, target_dir=card_dir, overwrite=True)
        # 覆寫 → 同一個檔案，庫內不增生 _1 副本
        assert first == second
        assert len(list_cards(card_dir)) == 1

    def test_find_existing_card(self, tmp_path: Path):
        from src.core.character_library import find_existing_card
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")

        card_dir = tmp_path / "cards"
        assert find_existing_card("小美", card_dir) is None
        path = save_card(_build_character("小美"), assets, target_dir=card_dir)
        assert find_existing_card("小美", card_dir) == path
        # 名稱經過 _safe_filename 清洗也要找得到
        save_card(_build_character("a/b"), assets, target_dir=card_dir)
        assert find_existing_card("a/b", card_dir) is not None
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py -v -k "overwrite or find_existing"`（環境變數 `QT_QPA_PLATFORM=offscreen`，以下所有 pytest 指令皆同）
Expected: FAIL（`save_card() got an unexpected keyword argument 'overwrite'` / ImportError）

- [ ] **Step 3: 實作**

`src/core/character_library.py`，`save_card` 簽名與衝突處理段改為：

```python
def save_card(
    character: Character,
    assets_dir: Path,
    target_dir: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """把角色連同立繪打包為 .vncard。

    overwrite=False（預設）：目標檔已存在時加數字後綴另存。
    overwrite=True：直接覆寫同名卡（用於「更新角色卡」）。
    """
    target_dir = target_dir or get_library_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = _safe_filename(character.name)
    card_path = target_dir / f"{base_name}{CARD_EXTENSION}"
    if not overwrite:
        # 衝突時加 _1, _2...
        counter = 1
        while card_path.exists():
            card_path = target_dir / f"{base_name}_{counter}{CARD_EXTENSION}"
            counter += 1
```

（函式其餘部分不動。）並在 `list_cards` 之前新增：

```python
def find_existing_card(character_name: str, source_dir: Path | None = None) -> Path | None:
    """以角色名找庫內既有同名卡；不存在回傳 None。"""
    source_dir = source_dir or get_library_dir()
    candidate = source_dir / f"{_safe_filename(character_name)}{CARD_EXTENSION}"
    return candidate if candidate.exists() else None
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py -v`
Expected: 全 PASS（含既有 10 案例不退步）

- [ ] **Step 5: Commit**

```bash
git add src/core/character_library.py tests/test_character_library.py
git commit -m "feat(card): save_card 支援 overwrite 更新與 find_existing_card 查詢"
```

---

### Task 2: `collect_missing_assets` — 缺圖偵測

解 P9 的核心半邊：UI 匯出前能知道哪些立繪檔遺失。

**Files:**
- Modify: `src/core/character_library.py`
- Test: `tests/test_character_library.py`

- [ ] **Step 1: 寫失敗測試**

```python
class TestMissingAssets:
    def test_collect_missing_assets(self, tmp_path: Path):
        from src.core.character_library import collect_missing_assets
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        # xm_smile.png 故意不建

        char = _build_character()
        missing = collect_missing_assets(char, assets)
        assert missing == ["xm_smile.png"]

    def test_collect_missing_assets_all_present(self, tmp_path: Path):
        from src.core.character_library import collect_missing_assets
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")
        assert collect_missing_assets(_build_character(), assets) == []
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py::TestMissingAssets -v`
Expected: FAIL（ImportError: cannot import name 'collect_missing_assets'）

- [ ] **Step 3: 實作**

加在 `save_card` 之前：

```python
def collect_missing_assets(character: Character, assets_dir: Path) -> list[str]:
    """回傳角色引用、但 assets_dir 中找不到的立繪檔名（去重排序）。"""
    assets_dir = Path(assets_dir)
    missing: set[str] = set()
    for costume in character.costumes:
        for sv in costume.expressions:
            if sv.filename and not (assets_dir / sv.filename).is_file():
                missing.add(sv.filename)
    return sorted(missing)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/character_library.py tests/test_character_library.py
git commit -m "feat(card): collect_missing_assets 偵測缺圖立繪"
```

---

### Task 3: `load_card` 內容去重

解 P4：同內容檔案不再複製出 `_1` 副本，改重用既有檔。

**Files:**
- Modify: `src/core/character_library.py`（`load_card` 第 119–141 行的解壓迴圈）
- Test: `tests/test_character_library.py`

- [ ] **Step 1: 寫失敗測試**

加到 `TestSaveListLoad`：

```python
    def test_load_twice_dedups_identical_content(self, tmp_path: Path):
        src_assets = tmp_path / "src_assets"
        src_assets.mkdir()
        _make_sprite(src_assets, "xm_normal.png", b"same-bytes")
        _make_sprite(src_assets, "xm_smile.png", b"same-bytes-2")

        card_path = save_card(_build_character(), src_assets, target_dir=tmp_path / "cards")
        dst = tmp_path / "dst_assets"

        _, written1 = load_card(card_path, dst)
        char2, written2 = load_card(card_path, dst)

        # 第二次匯入：內容相同 → 重用既有檔，不寫新檔
        assert written2 == []
        assert sorted(p.name for p in dst.iterdir()) == ["xm_normal.png", "xm_smile.png"]
        # Character 指回既有檔名
        filenames = [e.filename for e in char2.costumes[0].expressions]
        assert set(filenames) == {"xm_normal.png", "xm_smile.png"}

    def test_load_conflict_different_content_still_renames(self, tmp_path: Path):
        src_assets = tmp_path / "src_assets"
        src_assets.mkdir()
        _make_sprite(src_assets, "xm_normal.png", b"card-version")
        _make_sprite(src_assets, "xm_smile.png", b"smile")

        card_path = save_card(_build_character(), src_assets, target_dir=tmp_path / "cards")
        dst = tmp_path / "dst_assets"
        dst.mkdir()
        (dst / "xm_normal.png").write_bytes(b"different-existing")

        char, written = load_card(card_path, dst)
        # 內容不同 → 照舊 rename，既有檔不被覆寫
        assert (dst / "xm_normal.png").read_bytes() == b"different-existing"
        assert "xm_normal_1.png" in written
        filenames = [e.filename for e in char.costumes[0].expressions]
        assert "xm_normal_1.png" in filenames
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py -v -k dedup`
Expected: FAIL（written2 含 `xm_normal_1.png` 等）

- [ ] **Step 3: 實作**

`load_card` 的解壓迴圈（原第 122–141 行）整段改為：

```python
        for info in zf.infolist():
            if not info.filename.startswith("assets/") or info.is_dir():
                continue
            orig_name = Path(info.filename).name
            if not orig_name:
                continue
            data = zf.read(info)
            stem = Path(orig_name).stem
            suffix = Path(orig_name).suffix
            dest = target_assets_dir / orig_name
            # 檔名衝突時依序找：內容相同 → 重用；全都不同 → 用第一個空缺名
            counter = 1
            while dest.exists() and dest.read_bytes() != data:
                dest = target_assets_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            if dest.exists():
                # 找到內容一模一樣的既有檔 → 直接重用，不寫新檔
                rename_map[orig_name] = dest.name
                continue
            dest.write_bytes(data)
            rename_map[orig_name] = dest.name
            written.append(dest.name)
```

並把檔頭 `import shutil` 留著（`save_card` 之外已無人用 `shutil` 的話可移除；`import_card_file`（Task 5）會用到，故保留）。

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py -v`
Expected: 全 PASS（注意既有 `test_load_handles_filename_conflict` 用不同內容衝突，行為不變）

- [ ] **Step 5: Commit**

```bash
git add src/core/character_library.py tests/test_character_library.py
git commit -m "feat(card): load_card 依檔案內容去重，重複匯入不再增生副本"
```

---

### Task 4: `read_card_info` — 不解壓讀取卡片資訊與縮圖

解 P10 的核心半邊：給管理器列表用的名稱／顏色／數量／縮圖 bytes。

**Files:**
- Modify: `src/core/character_library.py`
- Test: `tests/test_character_library.py`

- [ ] **Step 1: 寫失敗測試**

```python
class TestReadCardInfo:
    def test_read_card_info(self, tmp_path: Path):
        from src.core.character_library import read_card_info
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png", b"thumb-bytes")
        _make_sprite(assets, "xm_smile.png")

        path = save_card(_build_character("小明"), assets, target_dir=tmp_path / "cards")
        info = read_card_info(path)
        assert info.name == "小明"
        assert info.name_color == "#4682B4"
        assert info.costume_count == 1
        assert info.expression_count == 2
        assert info.thumbnail == b"thumb-bytes"  # 第一張差分的原始 bytes
        assert info.path == path

    def test_read_card_info_no_sprite(self, tmp_path: Path):
        from src.core.character_library import read_card_info
        char = Character(name="無圖", name_color="#222222", costumes=[])
        path = save_card(char, tmp_path / "assets", target_dir=tmp_path / "cards")
        info = read_card_info(path)
        assert info.thumbnail is None
        assert info.expression_count == 0

    def test_read_card_info_invalid_raises(self, tmp_path: Path):
        from src.core.character_library import read_card_info
        bad = tmp_path / "bad.vncard"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("unrelated.txt", "hi")
        with pytest.raises(ValueError):
            read_card_info(bad)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py::TestReadCardInfo -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 實作**

檔頭加 `from dataclasses import dataclass, field` 不需要——models 已有 dataclass 用法，這裡直接：

```python
from dataclasses import dataclass
```

加在 `CARD_EXTENSION` 之後：

```python
@dataclass
class CardInfo:
    """角色卡的輕量資訊（給列表 UI 用，不解壓 assets）。"""

    path: Path
    name: str
    name_color: str
    costume_count: int
    expression_count: int
    thumbnail: bytes | None  # 第一張差分圖的原始 bytes；無立繪為 None
```

加在 `load_card` 之後：

```python
def read_card_info(card_path: Path) -> CardInfo:
    """讀取 .vncard 的角色資訊與第一張立繪 bytes，不寫任何檔案。

    Raises:
        FileNotFoundError: card_path 不存在。
        ValueError: 卡內容格式不合法。
    """
    card_path = Path(card_path)
    if not card_path.exists():
        raise FileNotFoundError(f"角色卡不存在：{card_path}")
    with zipfile.ZipFile(card_path, "r") as zf:
        try:
            raw = zf.read("character.json").decode("utf-8")
        except KeyError as e:
            raise ValueError("角色卡缺少 character.json") from e
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"character.json 解析失敗：{e}") from e
        character = Character.from_dict(data)

        thumbnail: bytes | None = None
        for costume in character.costumes:
            for sv in costume.expressions:
                if not sv.filename:
                    continue
                try:
                    thumbnail = zf.read(f"assets/{sv.filename}")
                except KeyError:
                    continue
                break
            if thumbnail is not None:
                break

    return CardInfo(
        path=card_path,
        name=character.name,
        name_color=character.name_color,
        costume_count=len(character.costumes),
        expression_count=sum(len(c.expressions) for c in character.costumes),
        thumbnail=thumbnail,
    )
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/character_library.py tests/test_character_library.py
git commit -m "feat(card): read_card_info 不解壓讀取卡片資訊與縮圖"
```

---

### Task 5: `import_card_file` — 外部 .vncard 加入庫

解 P1 的核心半邊：別人傳來的卡可以收進庫。

**Files:**
- Modify: `src/core/character_library.py`
- Test: `tests/test_character_library.py`

- [ ] **Step 1: 寫失敗測試**

```python
class TestImportCardFile:
    def test_import_external_card(self, tmp_path: Path):
        from src.core.character_library import import_card_file
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")
        external = save_card(_build_character(), assets, target_dir=tmp_path / "downloads")

        lib = tmp_path / "lib"
        dest = import_card_file(external, target_dir=lib)
        assert dest.parent == lib
        assert dest.exists()
        assert external.exists()  # 原檔保留（copy 而非 move）

    def test_import_name_conflict_adds_suffix(self, tmp_path: Path):
        from src.core.character_library import import_card_file
        assets = tmp_path / "assets"
        assets.mkdir()
        _make_sprite(assets, "xm_normal.png")
        _make_sprite(assets, "xm_smile.png")
        external = save_card(_build_character(), assets, target_dir=tmp_path / "dl")

        lib = tmp_path / "lib"
        first = import_card_file(external, target_dir=lib)
        second = import_card_file(external, target_dir=lib)
        assert first != second
        assert len(list(lib.glob("*.vncard"))) == 2

    def test_import_invalid_card_raises(self, tmp_path: Path):
        from src.core.character_library import import_card_file
        bad = tmp_path / "bad.vncard"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("unrelated.txt", "hi")
        with pytest.raises(ValueError):
            import_card_file(bad, target_dir=tmp_path / "lib")
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py::TestImportCardFile -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 實作**

加在 `read_card_info` 之後：

```python
def import_card_file(src: Path, target_dir: Path | None = None) -> Path:
    """把外部 .vncard 複製進角色卡庫；先驗證可讀，檔名衝突加數字後綴。

    Raises:
        FileNotFoundError / ValueError: 同 read_card_info。
    """
    src = Path(src)
    read_card_info(src)  # 不合法直接拋錯，不汙染庫
    target_dir = target_dir or get_library_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / src.name
    counter = 1
    while dest.exists():
        dest = target_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    shutil.copy2(src, dest)
    return dest
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_library.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/character_library.py tests/test_character_library.py
git commit -m "feat(card): import_card_file 把外部 .vncard 收進角色卡庫"
```

---

### Task 6: `CharacterCardManagerDialog` — 角色卡庫對話框

解 P1 / P10 的 UI 半邊，並首次給「刪除卡」介面。一個對話框兩用：從編輯角色開啟時當「選卡匯入」用（accept 後讀 `selected_card_path`），平時也能刪卡、收外部卡。

**Files:**
- Create: `src/ui/card_manager.py`
- Test: `tests/test_card_manager.py`

- [ ] **Step 1: 寫失敗測試**

新檔 `tests/test_card_manager.py`：

```python
"""CharacterCardManagerDialog：列表渲染、選卡、刪除、外部加入。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from src.core.character_library import save_card
from src.core.models import Character, Costume, SpriteVariant


def _build_char(name: str = "小明") -> Character:
    return Character(
        name=name,
        name_color="#E05555",
        costumes=[Costume(name="預設", expressions=[
            SpriteVariant(label="普通", filename="a.png"),
            SpriteVariant(label="微笑", filename="b.png"),
        ])],
    )


@pytest.fixture
def lib_with_cards(tmp_path, monkeypatch):
    """假角色卡庫（兩張卡），並把 get_library_dir 指過去。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    # a.png 用 1x1 PNG 真實 bytes，讓縮圖路徑可被 QPixmap 解析
    png_1px = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c626001000000ffff03000006000557"
        "bfabd40000000049454e44ae426082"
    )
    (assets / "a.png").write_bytes(png_1px)
    (assets / "b.png").write_bytes(b"fake")
    lib = tmp_path / "lib"
    save_card(_build_char("小明"), assets, target_dir=lib)
    save_card(_build_char("小美"), assets, target_dir=lib)
    import src.core.character_library as cardlib
    monkeypatch.setattr(cardlib, "get_library_dir", lambda: lib)
    return lib


def test_lists_cards_with_info(qapp, lib_with_cards):
    from src.ui.card_manager import CharacterCardManagerDialog
    dlg = CharacterCardManagerDialog()
    assert dlg._card_list.count() == 2
    texts = [dlg._card_list.item(i).text() for i in range(2)]
    assert any("小明" in t for t in texts)
    assert any("1 套服裝" in t and "2 張差分" in t for t in texts)


def test_empty_library_shows_hint(qapp, tmp_path, monkeypatch):
    import src.core.character_library as cardlib
    empty = tmp_path / "empty_lib"
    empty.mkdir()
    monkeypatch.setattr(cardlib, "get_library_dir", lambda: empty)
    from src.ui.card_manager import CharacterCardManagerDialog
    dlg = CharacterCardManagerDialog()
    assert dlg._card_list.count() == 0
    assert dlg._empty_hint.isVisibleTo(dlg)
    assert not dlg.btn_use.isEnabled()
    assert not dlg.btn_delete.isEnabled()


def test_use_selected_card_accepts_with_path(qapp, lib_with_cards):
    from src.ui.card_manager import CharacterCardManagerDialog
    dlg = CharacterCardManagerDialog()
    dlg._card_list.setCurrentRow(0)
    dlg._on_use_clicked()
    assert dlg.result() == 1  # Accepted
    assert dlg.selected_card_path is not None
    assert dlg.selected_card_path.suffix == ".vncard"


def test_delete_card_with_confirm(qapp, lib_with_cards, monkeypatch):
    from src.ui.card_manager import CharacterCardManagerDialog
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )
    dlg = CharacterCardManagerDialog()
    dlg._card_list.setCurrentRow(0)
    dlg._on_delete_clicked()
    assert dlg._card_list.count() == 1
    assert len(list(lib_with_cards.glob("*.vncard"))) == 1


def test_delete_card_cancelled(qapp, lib_with_cards, monkeypatch):
    from src.ui.card_manager import CharacterCardManagerDialog
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No),
    )
    dlg = CharacterCardManagerDialog()
    dlg._card_list.setCurrentRow(0)
    dlg._on_delete_clicked()
    assert dlg._card_list.count() == 2
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_card_manager.py -v`
Expected: FAIL（ModuleNotFoundError: src.ui.card_manager）

- [ ] **Step 3: 實作**

新檔 `src/ui/card_manager.py`：

```python
"""角色卡庫對話框：瀏覽（縮圖+資訊）、選卡匯入、刪除、收外部卡。

從 CharacterEditorDialog 開啟時當選卡器用：exec() 回 Accepted 後
讀 `selected_card_path` 取得使用者選的卡。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import BodyLabel, ListWidget, PrimaryPushButton, PushButton, StrongBodyLabel

from src.core import character_library as cardlib


def _thumbnail_icon(info: cardlib.CardInfo) -> QIcon:
    """卡片縮圖：有立繪用立繪，否則用名牌色色塊。"""
    pm = QPixmap()
    if info.thumbnail and pm.loadFromData(info.thumbnail):
        pm = pm.scaled(
            48, 48,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    else:
        pm = QPixmap(48, 48)
        pm.fill(QColor(info.name_color))
    return QIcon(pm)


class CharacterCardManagerDialog(QDialog):
    """角色卡庫：列表 + 匯入此角色 / 從電腦加入 / 刪除。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.selected_card_path: Path | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("角色卡庫")
        self.setMinimumSize(440, 380)
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.addWidget(StrongBodyLabel("我的角色卡："))

        self._card_list = ListWidget()
        self._card_list.setIconSize(QSize(48, 48))
        self._card_list.itemDoubleClicked.connect(lambda _: self._on_use_clicked())
        self._card_list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._card_list)

        self._empty_hint = BodyLabel(
            "這裡還沒有角色卡。\n"
            "在「編輯角色」按「儲存為角色卡…」即可建立；\n"
            "別人傳給你的 .vncard 檔可按下方「從電腦加入角色卡…」收進來。"
        )
        self._empty_hint.setWordWrap(True)
        layout.addWidget(self._empty_hint)

        tool_row = QHBoxLayout()
        self.btn_add_file = PushButton("從電腦加入角色卡…")
        self.btn_add_file.clicked.connect(self._on_add_file_clicked)
        self.btn_delete = PushButton("刪除")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        tool_row.addWidget(self.btn_add_file)
        tool_row.addWidget(self.btn_delete)
        tool_row.addStretch()
        layout.addLayout(tool_row)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.btn_use = PrimaryPushButton("匯入此角色")
        self.btn_use.clicked.connect(self._on_use_clicked)
        self.btn_close = PushButton("關閉")
        self.btn_close.clicked.connect(self.reject)
        bottom_row.addWidget(self.btn_use)
        bottom_row.addWidget(self.btn_close)
        layout.addLayout(bottom_row)

        self.setLayout(layout)

    def _refresh(self) -> None:
        self._card_list.clear()
        for path in cardlib.list_cards():
            try:
                info = cardlib.read_card_info(path)
            except (ValueError, OSError):
                # 壞卡照列（可刪），但標明不可匯入
                item = QListWidgetItem(f"{path.stem}（檔案損毀）")
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                self._card_list.addItem(item)
                continue
            item = QListWidgetItem(
                _thumbnail_icon(info),
                f"{info.name}（{info.costume_count} 套服裝 · {info.expression_count} 張差分）",
            )
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self._card_list.addItem(item)
        has_cards = self._card_list.count() > 0
        self._empty_hint.setVisible(not has_cards)
        self._on_selection_changed(self._card_list.currentRow())

    def _on_selection_changed(self, row: int) -> None:
        has_sel = 0 <= row < self._card_list.count()
        self.btn_use.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)

    def _current_path(self) -> Path | None:
        item = self._card_list.currentItem()
        return Path(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _on_use_clicked(self) -> None:
        path = self._current_path()
        if path is None:
            return
        self.selected_card_path = path
        self.accept()

    def _on_delete_clicked(self) -> None:
        path = self._current_path()
        if path is None:
            return
        ret = QMessageBox.question(
            self, "刪除角色卡",
            f"確定刪除角色卡「{path.stem}」？\n（已匯入各專案的角色不受影響）",
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        cardlib.delete_card(path)
        self._refresh()

    def _on_add_file_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇角色卡檔案", "",
            "角色卡 (*.vncard);;所有檔案 (*)",
        )
        if not file_path:
            return
        try:
            cardlib.import_card_file(Path(file_path))
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(self, "加入失敗", str(e))
            return
        self._refresh()
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_card_manager.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/card_manager.py tests/test_card_manager.py
git commit -m "feat(card): 角色卡庫對話框（縮圖列表/匯入/刪除/收外部卡）"
```

---

### Task 7: `CharacterEditorDialog` 匯入流程改走管理器 + 覆蓋確認

解 P1 / P5 的 UI 半邊。同時記錄本次匯入寫了哪些檔（給 Task 8 用）。

**Files:**
- Modify: `src/ui/dialogs.py`（`__init__` 約第 308 行、`_on_import_card` 第 479–522 行）
- Test: `tests/test_character_editor_dialog.py`

- [ ] **Step 1: 寫失敗測試**

加到 `tests/test_character_editor_dialog.py` 尾端：

```python
# ── 角色卡匯入流程（管理器 + 覆蓋確認 + 寫入追蹤）──

from PyQt6.QtWidgets import QDialog, QMessageBox

from src.core.character_library import save_card
from src.core.models import Character as _Char


def _save_test_card(tmp_path):
    assets = tmp_path / "cardsrc" / "assets"
    assets.mkdir(parents=True)
    (assets / "card_sprite.png").write_bytes(b"png-bytes")
    char = _Char(name="卡片角", name_color="#336699", costumes=[
        Costume(name="預設", expressions=[SpriteVariant("普通", "card_sprite.png")]),
    ])
    return save_card(char, assets, target_dir=tmp_path / "lib")


def test_import_card_asks_before_overwriting_edits(qapp, tmp_path, monkeypatch):
    """名稱欄有內容時匯入 → 先確認；按 No 則完全不動。"""
    card = _save_test_card(tmp_path)
    dlg = CharacterEditorDialog(project_dir=tmp_path / "proj")
    dlg.edit_name.setText("打到一半的名字")

    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No),
    )
    opened = []
    import src.ui.card_manager as cm
    monkeypatch.setattr(
        cm.CharacterCardManagerDialog, "exec",
        lambda self: opened.append(1) or QDialog.DialogCode.Rejected,
    )
    dlg._on_import_card()
    assert opened == []  # 按 No → 管理器根本不開
    assert dlg.edit_name.text() == "打到一半的名字"


def test_import_card_via_manager_loads_and_tracks_files(qapp, tmp_path, monkeypatch):
    """空白編輯器匯入 → 不問直接開管理器；匯入後寫入檔被記錄。"""
    card = _save_test_card(tmp_path)
    proj = tmp_path / "proj"
    dlg = CharacterEditorDialog(project_dir=proj)

    import src.ui.card_manager as cm

    def fake_exec(self):
        self.selected_card_path = card
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(cm.CharacterCardManagerDialog, "exec", fake_exec)
    dlg._on_import_card()

    assert dlg.edit_name.text() == "卡片角"
    assert (proj / "assets" / "card_sprite.png").exists()
    assert dlg._card_written_files == ["card_sprite.png"]
    result = dlg.get_character()
    assert result.costumes[0].expressions[0].filename == "card_sprite.png"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v -k import_card`
Expected: FAIL（`_card_written_files` 不存在 / 仍走 QFileDialog 路徑）

- [ ] **Step 3: 實作**

`CharacterEditorDialog.__init__` 中 `self._loaded_from_card: bool = False` 之後加一行：

```python
        # 本次對話期間由角色卡匯入寫進專案 assets 的檔名；取消時用於清理（Task 8）
        self._card_written_files: list[str] = []
```

`_on_import_card` 整個函式改為：

```python
    def _on_import_card(self) -> None:
        from src.core.character_library import load_card
        from src.ui.card_manager import CharacterCardManagerDialog

        # 編輯到一半時先確認，避免無預警蓋掉
        if self.edit_name.text().strip() or self._sprite_filename:
            ret = QMessageBox.question(
                self, "覆蓋目前內容？",
                "匯入角色卡會以卡片內容取代目前的名稱、顏色與立繪。\n確定繼續？",
            )
            if ret != QMessageBox.StandardButton.Yes:
                return

        picker = CharacterCardManagerDialog(self)
        if picker.exec() != QDialog.DialogCode.Accepted or picker.selected_card_path is None:
            return

        try:
            char, written = load_card(picker.selected_card_path, self._project_dir / "assets")
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(self, "匯入失敗", str(e))
            return
        self._card_written_files.extend(written)

        # 覆蓋目前編輯值
        self.edit_name.setText(char.name)
        self._apply_color(char.name_color)
        if char.costumes and char.costumes[0].expressions:
            first = char.costumes[0].expressions[0]
            self._sprite_filename = first.filename
            self._lbl_sprite_name.setText(first.label)
            full = self._project_dir / "assets" / first.filename
            if full.exists():
                pm = QPixmap(str(full)).scaled(
                    116, 136, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._sprite_preview.setPixmap(pm)
        # 保留所有服裝（含差分）供 get_character 使用
        self._extra_costumes = list(char.costumes)
        self._loaded_from_card = True
```

（原本「庫空就 return」的分支整段刪除——空庫狀態改由管理器的 empty hint 處理。）

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v`
Expected: 全 PASS（含既有案例）

- [ ] **Step 5: Commit**

```bash
git add src/ui/dialogs.py tests/test_character_editor_dialog.py
git commit -m "feat(dialogs): 角色卡匯入改走卡庫管理器，編輯中內容先確認再覆蓋"
```

---

### Task 8: 取消編輯時清理本次匯入的孤兒立繪

解 P3。只清「本次對話期間由卡匯入新寫入」的檔（Task 3 去重後重用的既有檔不在 `written` 內，安全）。

**Files:**
- Modify: `src/ui/dialogs.py`（`CharacterEditorDialog`）
- Test: `tests/test_character_editor_dialog.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_reject_after_card_import_removes_orphan_assets(qapp, tmp_path, monkeypatch):
    """匯入卡後按取消 → 本次寫入的立繪檔被清掉。"""
    card = _save_test_card(tmp_path)
    proj = tmp_path / "proj"
    dlg = CharacterEditorDialog(project_dir=proj)

    import src.ui.card_manager as cm

    def fake_exec(self):
        self.selected_card_path = card
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(cm.CharacterCardManagerDialog, "exec", fake_exec)
    dlg._on_import_card()
    assert (proj / "assets" / "card_sprite.png").exists()

    dlg.reject()
    assert not (proj / "assets" / "card_sprite.png").exists()


def test_accept_after_card_import_keeps_assets(qapp, tmp_path, monkeypatch):
    """匯入卡後按 OK → 立繪保留。"""
    card = _save_test_card(tmp_path)
    proj = tmp_path / "proj"
    dlg = CharacterEditorDialog(project_dir=proj)

    import src.ui.card_manager as cm

    def fake_exec(self):
        self.selected_card_path = card
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(cm.CharacterCardManagerDialog, "exec", fake_exec)
    dlg._on_import_card()
    dlg._validate_and_accept()
    assert (proj / "assets" / "card_sprite.png").exists()
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v -k orphan`
Expected: FAIL（reject 後檔案仍在）

- [ ] **Step 3: 實作**

`CharacterEditorDialog` 內、`_validate_and_accept` 之前加：

```python
    def reject(self) -> None:
        """取消時清掉本次由角色卡匯入、尚未被採用的立繪檔（孤兒檔防治）。"""
        assets = self._project_dir / "assets"
        for name in self._card_written_files:
            f = assets / name
            try:
                if f.is_file():
                    f.unlink()
            except OSError:
                pass  # 清理失敗不阻擋關閉
        self._card_written_files = []
        super().reject()
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/dialogs.py tests/test_character_editor_dialog.py
git commit -m "fix(dialogs): 取消編輯角色時清理本次卡片匯入的孤兒立繪"
```

---

### Task 9: 匯出角色卡——同名卡詢問「更新或另存」+ 缺圖警告

解 P2 / P9 的 UI 半邊。

**Files:**
- Modify: `src/ui/dialogs.py`（`_on_export_card`，現第 524–547 行）
- Test: `tests/test_character_editor_dialog.py`

- [ ] **Step 1: 寫失敗測試**

```python
# ── 匯出角色卡：同名更新 / 缺圖警告 ──

def test_export_same_name_updates_card(qapp, tmp_path, monkeypatch):
    """庫內已有同名卡 → 問「更新？」，按 Yes 不增生新檔。"""
    import src.core.character_library as cardlib
    lib = tmp_path / "lib"
    lib.mkdir()
    monkeypatch.setattr(cardlib, "get_library_dir", lambda: lib)
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **kw: None)
    )

    proj = tmp_path / "proj"
    (proj / "assets").mkdir(parents=True)
    (proj / "assets" / "s.png").write_bytes(b"png")

    dlg = CharacterEditorDialog(project_dir=proj)
    dlg.edit_name.setText("小美")
    dlg._sprite_filename = "s.png"

    dlg._on_export_card()
    dlg._on_export_card()  # 第二次 → 應更新而非另存
    assert sorted(p.name for p in lib.glob("*.vncard")) == ["小美.vncard"]


def test_export_warns_on_missing_sprite_files(qapp, tmp_path, monkeypatch):
    """引用的立繪檔不存在 → 跳缺圖確認；按 No 取消匯出。"""
    import src.core.character_library as cardlib
    lib = tmp_path / "lib"
    lib.mkdir()
    monkeypatch.setattr(cardlib, "get_library_dir", lambda: lib)

    questions = []

    def fake_question(parent, title, text, *a, **kw):
        questions.append((title, text))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))

    proj = tmp_path / "proj"
    (proj / "assets").mkdir(parents=True)
    dlg = CharacterEditorDialog(project_dir=proj)
    dlg.edit_name.setText("小美")
    dlg._sprite_filename = "ghost.png"  # 檔案不存在

    dlg._on_export_card()
    assert any("ghost.png" in text for _, text in questions)
    assert list(lib.glob("*.vncard")) == []  # 按 No → 沒存
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v -k export`
Expected: FAIL（第二次匯出產生 `小美_1.vncard`；缺圖無提示）

- [ ] **Step 3: 實作**

`_on_export_card` 整個函式改為：

```python
    def _on_export_card(self) -> None:
        from src.core.character_library import (
            collect_missing_assets,
            find_existing_card,
            save_card,
        )

        # 必須先有名稱與立繪
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "缺少名稱", "請先輸入角色名稱才能匯出角色卡。")
            return
        if not self._sprite_filename and not self._extra_costumes:
            QMessageBox.warning(self, "缺少立繪", "請先匯入至少一張立繪才能匯出角色卡。")
            return

        # 編輯中的角色（未 accept）先組一個臨時 Character 出去
        char = self.get_character()
        assets_dir = self._project_dir / "assets"

        # 缺圖先警告，避免存出缺圖卡而不自知
        missing = collect_missing_assets(char, assets_dir)
        if missing:
            ret = QMessageBox.question(
                self, "部分立繪找不到",
                "下列立繪檔案在專案中不存在，存出的角色卡將缺少這些圖片：\n"
                + "\n".join(f"・{m}" for m in missing)
                + "\n\n仍要繼續儲存嗎？",
            )
            if ret != QMessageBox.StandardButton.Yes:
                return

        # 同名卡 → 問更新或另存
        overwrite = False
        if find_existing_card(name) is not None:
            ret = QMessageBox.question(
                self, "已有同名角色卡",
                f"角色卡「{name}」已存在。\n\n"
                "・是（Yes）：更新既有卡片\n"
                "・否（No）：另存為新卡片（自動加編號）",
            )
            overwrite = ret == QMessageBox.StandardButton.Yes

        try:
            path = save_card(char, assets_dir, overwrite=overwrite)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "儲存失敗", str(e))
            return
        QMessageBox.information(
            self, "角色卡已儲存",
            f"角色卡已寫入：\n{path}\n\n日後可在其他專案透過『從角色卡匯入』復用。",
        )
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/dialogs.py tests/test_character_editor_dialog.py
git commit -m "feat(dialogs): 匯出角色卡支援同名更新並警告缺圖立繪"
```

---

### Task 10: `CostumeEditorDialog` 零服裝時自動建「服裝1」

解 P6：新手按「新增差分」不再靜默失敗。

**Files:**
- Modify: `src/ui/dialogs.py`（`_on_add_expression` 第 756–765 行、`_on_files_dropped` 第 777–784 行）
- Test: Create `tests/test_costume_editor.py`

- [ ] **Step 1: 寫失敗測試**

新檔 `tests/test_costume_editor.py`：

```python
"""CostumeEditorDialog：零服裝自動建服裝、移除確認。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtWidgets import QMessageBox

from src.core.models import Character, Costume, SpriteVariant
from src.ui.dialogs import CostumeEditorDialog


def _png(tmp_path: Path, name: str = "pic.png") -> Path:
    p = tmp_path / name
    p.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c626001000000ffff03000006000557"
        "bfabd40000000049454e44ae426082"
    ))
    return p


def test_drop_image_on_empty_character_creates_costume(qapp, tmp_path, monkeypatch):
    """零服裝時拖圖進來 → 自動建「服裝1」並收下差分。"""
    from PyQt6.QtWidgets import QInputDialog
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
    """已有服裝時 _ensure_costume 不重複建。"""
    char = Character(name="小美", costumes=[Costume(name="校服")])
    dlg = CostumeEditorDialog(char, tmp_path)
    row = dlg._ensure_costume()
    assert row == 0
    assert len(dlg.get_costumes()) == 1
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_costume_editor.py -v`
Expected: FAIL（零服裝時 `_on_files_dropped` 直接 return，costumes 仍為空；`_ensure_costume` 不存在）

- [ ] **Step 3: 實作**

`CostumeEditorDialog` 內加（放在 `_on_add_costume` 之前）：

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

`_on_add_expression` 開頭兩行改為：

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

`_on_files_dropped` 開頭改為：

```python
    def _on_files_dropped(self, paths: list[Path]) -> None:
        """拖曳圖片到右側面板時批量匯入；零服裝時自動建服裝1。"""
        cos_row = self._ensure_costume()
        for p in paths:
            if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                self._import_expression(cos_row, p)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_costume_editor.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/dialogs.py tests/test_costume_editor.py
git commit -m "fix(dialogs): 服裝編輯器零服裝時自動建服裝1，新增差分不再靜默失敗"
```

---

### Task 11: 移除含差分的服裝前先確認

解 P7。空服裝直接刪（無資料損失），含差分才問。

**Files:**
- Modify: `src/ui/dialogs.py`（`_on_remove_costume` 第 750–754 行）
- Test: `tests/test_costume_editor.py`

- [ ] **Step 1: 寫失敗測試**

加到 `tests/test_costume_editor.py`：

```python
def test_remove_costume_with_expressions_asks(qapp, tmp_path, monkeypatch):
    """移除含差分的服裝 → 跳確認；按 No 不刪。"""
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
    assert len(dlg.get_costumes()) == 1  # 沒被刪


def test_remove_empty_costume_no_confirm(qapp, tmp_path, monkeypatch):
    """空服裝直接刪，不彈確認。"""
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

Run: `.venv\Scripts\python.exe -m pytest tests/test_costume_editor.py -v -k remove`
Expected: `test_remove_costume_with_expressions_asks` FAIL（直接刪掉了）

- [ ] **Step 3: 實作**

`_on_remove_costume` 改為：

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

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_costume_editor.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/dialogs.py tests/test_costume_editor.py
git commit -m "fix(dialogs): 移除含差分的服裝前先確認"
```

---

### Task 12: 編輯角色框顯示服裝摘要 + 角色卡按鈕 tooltip

解 P8 與 P11 的一半：多服裝角色在「編輯角色」框看得到其餘資料的存在。

**Files:**
- Modify: `src/ui/dialogs.py`（import 行第 31、`_setup_ui` sprite_group 之後、`_load_character`、`_on_import_card` 尾端）
- Test: `tests/test_character_editor_dialog.py`

- [ ] **Step 1: 寫失敗測試**

```python
# ── 服裝摘要標籤 ──

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

dialogs.py 第 31 行 import 加 `BodyLabel`：

```python
from qfluentwidgets import BodyLabel, ComboBox, LineEdit, ListWidget, PushButton, StrongBodyLabel
```

`_setup_ui` 中 `layout.addWidget(sprite_group)` 之後加：

```python
        # 多服裝角色提示：避免新手以為角色只有這一張圖
        self._lbl_costume_summary = BodyLabel("")
        self._lbl_costume_summary.setWordWrap(True)
        self._lbl_costume_summary.setVisible(False)
        layout.addWidget(self._lbl_costume_summary)
```

同函式中 C6 按鈕列加 tooltip（在 `card_row.addStretch()` 之前）：

```python
        self.btn_import_card.setToolTip("從角色卡庫挑一個之前存過的角色，連同立繪帶進這個專案")
        self.btn_export_card.setToolTip("把這個角色（含所有服裝與立繪）存成角色卡，給其他專案重複使用")
```

`CharacterEditorDialog` 內加共用方法（放 `_load_character` 之後），並在 `_load_character` 尾端與 `_on_import_card` 尾端（`self._loaded_from_card = True` 之後）各呼叫一次：

```python
    def _update_costume_summary(self, char: Character) -> None:
        """多於一張差分時顯示摘要，提示完整資料在「編輯服裝…」。"""
        total = len(char.sprites)
        if total > 1:
            self._lbl_costume_summary.setText(
                f"此角色共有 {len(char.costumes)} 套服裝、{total} 張差分。"
                "這裡只更換預設立繪；完整管理請用角色面板的「編輯服裝…」。"
            )
            self._lbl_costume_summary.setVisible(True)
        else:
            self._lbl_costume_summary.setVisible(False)
```

`_load_character` 尾端加：

```python
        self._update_costume_summary(char)
```

`_on_import_card` 尾端（`self._loaded_from_card = True` 之後）加：

```python
        self._update_costume_summary(char)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_character_editor_dialog.py -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/dialogs.py tests/test_character_editor_dialog.py
git commit -m "feat(dialogs): 編輯角色框顯示服裝差分摘要並補角色卡按鈕 tooltip"
```

---

### Task 13: 使用教學文案補角色卡

解 P11 的另一半。純文案，不寫測試。

**Files:**
- Modify: `src/ui/main_window.py:358-375`（`_on_show_tutorial`）

- [ ] **Step 1: 修改教學文字**

`_on_show_tutorial` 中第 364 行之後插入一行，使教學變成：

```python
    def _on_show_tutorial(self) -> None:
        QMessageBox.information(
            self, "使用教學",
            "VisualNovel Studio 使用教學\n\n"
            "1. 新增專案或匯入文字\n"
            "2. 在場景列表中管理場景，設定背景、BGM、特效\n"
            "3. 在角色列表中新增角色，設定名稱、顏色、立繪差分\n"
            "   ・常用角色可「儲存為角色卡」，其他專案一鍵匯入\n"
            "4. 在文字列表中編輯文字，指定角色與差分\n"
            "5. 預覽畫面即時顯示效果\n"
            "6. 完成後導出為影片 (MP4) 或網頁 (ZIP/HTML)\n\n"
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
git commit -m "docs(ui): 使用教學補角色卡說明"
```

---

### Task 14: 收尾——全測試、開發紀錄、合併

**Files:**
- Modify: `docs/DEVELOPMENT_HISTORY.md`

- [ ] **Step 1: 跑全測試**

Run: `.venv\Scripts\python.exe -m pytest tests/ -v`（`QT_QPA_PLATFORM=offscreen`）
Expected: 全 PASS，0 failed

- [ ] **Step 2: 追加開發紀錄**

在 `docs/DEVELOPMENT_HISTORY.md` 文件尾端追加章節（日期用實際完成日）：

```markdown
## feature/character-card-ux：角色卡生命週期與角色設定 UX（2026-06）

### 背景
新手視角 offscreen 走查（`build/uxtest/novice_walkthrough.py`）證實 6 個陷阱：
空庫無法匯入外部卡、重存卡增生副本、取消留孤兒立繪、重複匯入素材重複、
匯入無預警覆蓋編輯內容、零服裝按「新增差分」靜默無反應。

### 成果
- `character_library.py`：`save_card(overwrite=)`、`find_existing_card`、
  `collect_missing_assets`、`load_card` 內容去重、`read_card_info`（CardInfo + 縮圖 bytes）、
  `import_card_file`。
- 新增 `src/ui/card_manager.py::CharacterCardManagerDialog`：縮圖列表、匯入、刪除（有確認）、
  「從電腦加入角色卡…」收外部 .vncard；空庫顯示引導文案。
- `CharacterEditorDialog`：匯入改走管理器、編輯中先確認再覆蓋、`reject()` 清理本次匯入
  孤兒檔（`_card_written_files` 追蹤）、匯出同名卡詢問更新/另存、缺圖先警告、
  多服裝角色顯示摘要標籤。
- `CostumeEditorDialog`：零服裝自動建「服裝1」、移除含差分服裝先確認。

### 給接手者的備忘
- `load_card` 去重以「整檔 bytes 相等」判定；`written` 只含本次新寫入檔，
  reject 清理據此進行，重用檔不會被誤刪。
- `.vncard` 格式未變（zip + character.json + assets/），縮圖由 `read_card_info`
  即時從 zip 取第一張差分，無 metadata 欄位（YAGNI）。
```

- [ ] **Step 3: Commit**

```bash
git add docs/DEVELOPMENT_HISTORY.md
git commit -m "docs: 追加角色卡 UX 改進紀錄至 DEVELOPMENT_HISTORY"
```

- [ ] **Step 4: 合併（依專案分支工作流）**

使用 superpowers:finishing-a-development-branch skill 處理合併選項（merge 到 main 前確認 `pytest tests/` 全綠）。

---

## 自我審查紀錄

- **Spec 覆蓋**：P1→Task 5/6/7、P2→1/9、P3→8、P4→3、P5→7、P6→10、P7→11、P8→12、P9→2/9、P10→4/6、P11→12/13，全數對應。
- **型別一致性**：`CardInfo` 欄位（Task 4）與 `_thumbnail_icon` / `_refresh`（Task 6）一致；`_card_written_files`（Task 7 定義、Task 8 使用）；`_ensure_costume`（Task 10 定義並測試）；`find_existing_card` / `collect_missing_assets`（Task 1/2 定義、Task 9 使用）。
- **注意**：Task 3 改動 `load_card` 後，Task 7/8 測試依賴「written 只含新寫入檔」語意——執行順序勿對調（依 Task 編號執行即可）。
