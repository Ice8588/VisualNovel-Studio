"""CharacterEditorDialog.get_character() 資料完整性測試。

TDD：先跑這些測試應該「失敗」，修正 get_character() 後才全綠。
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from src.core.models import Character, Costume, SpriteVariant
from src.ui.dialogs import CharacterEditorDialog


# qapp fixture 來自 tests/conftest.py（session scope）


# ── 輔助函式 ──

def _make_multi_costume_char() -> Character:
    """建立含多服裝、多差分的角色（Bug 重現案例）。"""
    return Character(
        name="穹月",
        name_color="#E05555",
        costumes=[
            Costume(
                name="服裝1",
                expressions=[
                    SpriteVariant("正面", "a.png"),
                    SpriteVariant("微笑", "b.png"),
                ],
            ),
            Costume(
                name="制服",
                expressions=[
                    SpriteVariant("白絲", "c.png"),
                ],
            ),
        ],
    )


# ── 測試 1：編輯多服裝角色、未改動直接 OK → costumes 完整保留 ──

def test_edit_preserves_all_costumes_unchanged(qapp, tmp_path):
    """Bug 重現案例：編輯多服裝角色後直接 OK，costumes 應完整保留。"""
    char = _make_multi_costume_char()
    dlg = CharacterEditorDialog(character=char, project_dir=tmp_path)

    result = dlg.get_character()

    # 服裝數量不能少
    assert len(result.costumes) == 2, (
        f"應有 2 套服裝，實際得到 {len(result.costumes)}：{result.costumes}"
    )

    # 服裝1 有 2 個差分
    cos0 = result.costumes[0]
    assert cos0.name == "服裝1"
    assert len(cos0.expressions) == 2
    assert cos0.expressions[0].filename == "a.png"
    assert cos0.expressions[0].label == "正面"
    assert cos0.expressions[1].filename == "b.png"
    assert cos0.expressions[1].label == "微笑"

    # 制服不能消失
    cos1 = result.costumes[1]
    assert cos1.name == "制服"
    assert len(cos1.expressions) == 1
    assert cos1.expressions[0].filename == "c.png"
    assert cos1.expressions[0].label == "白絲"


# ── 測試 2：編輯時更換預設立繪 → 只有 costumes[0].expressions[0] 換新 ──

def test_edit_replace_default_sprite_only_changes_first_expression(qapp, tmp_path):
    """更換預設立繪時，只替換 costumes[0].expressions[0]，其餘服裝/差分不動。"""
    char = _make_multi_costume_char()
    dlg = CharacterEditorDialog(character=char, project_dir=tmp_path)

    # 模擬使用者選了新立繪（直接設 internal state，不開 file dialog）
    dlg._sprite_filename = "new_sprite.png"
    dlg._lbl_sprite_name.setText("新差分")

    result = dlg.get_character()

    # 仍有 2 套服裝
    assert len(result.costumes) == 2

    # costumes[0].expressions[0] 已換成新立繪
    cos0 = result.costumes[0]
    assert cos0.expressions[0].filename == "new_sprite.png"
    assert cos0.expressions[0].label == "新差分"

    # costumes[0].expressions[1] 不動
    assert cos0.expressions[1].filename == "b.png"
    assert cos0.expressions[1].label == "微笑"

    # 制服整套不動
    cos1 = result.costumes[1]
    assert cos1.name == "制服"
    assert cos1.expressions[0].filename == "c.png"


# ── 測試 3：編輯時按「清除」立繪後 OK → costumes 不變 ──

def test_edit_clear_sprite_preserves_costumes(qapp, tmp_path):
    """使用者按「清除」後 OK，costumes 應維持原樣（不可無聲毀資料）。"""
    char = _make_multi_costume_char()
    dlg = CharacterEditorDialog(character=char, project_dir=tmp_path)

    # 模擬使用者按了「清除」
    dlg._on_clear_sprite()  # 這會把 _sprite_filename 設為 None

    result = dlg.get_character()

    # costumes 應完整保留
    assert len(result.costumes) == 2
    assert result.costumes[0].expressions[0].filename == "a.png"
    assert result.costumes[1].expressions[0].filename == "c.png"


# ── 測試 4：新增角色選一張立繪 → 得到 [服裝1[該立繪]] ──

def test_new_character_single_sprite_creates_default_costume(qapp, tmp_path):
    """新增角色（_original=None）選一張立繪，應建立 [Costume('服裝1', [該立繪])]。"""
    dlg = CharacterEditorDialog(character=None, project_dir=tmp_path)
    dlg.edit_name.setText("測試角色")
    dlg._sprite_filename = "hero.png"
    dlg._lbl_sprite_name.setText("正面")

    result = dlg.get_character()

    assert result.name == "測試角色"
    assert len(result.costumes) == 1
    assert result.costumes[0].name == "服裝1"
    assert len(result.costumes[0].expressions) == 1
    assert result.costumes[0].expressions[0].filename == "hero.png"
    assert result.costumes[0].expressions[0].label == "正面"


# ── 測試 5：新增角色未選立繪 → costumes 為空 ──

def test_new_character_no_sprite_has_empty_costumes(qapp, tmp_path):
    """新增角色不選立繪，costumes 應為空列表（守住既有行為）。"""
    dlg = CharacterEditorDialog(character=None, project_dir=tmp_path)
    dlg.edit_name.setText("空白角色")

    result = dlg.get_character()

    assert result.name == "空白角色"
    assert result.costumes == []


# ── 測試 7：編輯角色時，名稱與顏色從對話框取得（不從 _original） ──

def test_edit_updates_name_and_color(qapp, tmp_path):
    """編輯角色時，回傳的名稱與名牌色應反映對話框目前值，而非舊資料。"""
    char = _make_multi_costume_char()
    dlg = CharacterEditorDialog(character=char, project_dir=tmp_path)

    # 使用者修改名稱與顏色
    dlg.edit_name.setText("新名稱")
    dlg._apply_color("#00FF00")

    result = dlg.get_character()

    assert result.name == "新名稱"
    assert result.name_color == "#00FF00"
    # costumes 仍完整
    assert len(result.costumes) == 2


# ── 測試 8：編輯 costumes 為空的既有角色時，新立繪應建立預設服裝 ──

def test_edit_character_with_empty_costumes_and_new_sprite(qapp, tmp_path):
    """編輯一個沒有服裝的既有角色時，若選了立繪應建立 Costume('服裝1', [新立繪])。"""
    char = Character(name="空服裝角色", name_color="#4682B4", costumes=[])
    dlg = CharacterEditorDialog(character=char, project_dir=tmp_path)

    dlg._sprite_filename = "solo.png"
    dlg._lbl_sprite_name.setText("正面")

    result = dlg.get_character()

    assert len(result.costumes) == 1
    assert result.costumes[0].name == "服裝1"
    assert result.costumes[0].expressions[0].filename == "solo.png"


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


# ── 測試 9：get_character() 回傳深拷貝，不污染 _original ──

def test_edit_returns_deep_copy_not_original(qapp, tmp_path):
    """get_character() 應回傳獨立物件，修改結果不應影響 _original。"""
    char = _make_multi_costume_char()
    original_label = char.costumes[0].expressions[0].label  # "正面"
    dlg = CharacterEditorDialog(character=char, project_dir=tmp_path)

    result = dlg.get_character()
    # 修改回傳值
    result.costumes[0].expressions[0].label = "已竄改"

    # _original 不受影響
    assert dlg._original.costumes[0].expressions[0].label == original_label
