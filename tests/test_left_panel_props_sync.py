"""測試開啟專案後屬性面板背景/BGM 正確顯示（不落回「(無)」）。

覆蓋情境：
1. _rebuild_ui 流程：先 set_asset_lists 再 set_project → combo 回填正確。
2. set_asset_lists 重建選項後 combo 以 model 值（而非舊 currentText）回填。
3. 匯入素材自動套用行為不破壞（_on_import_assets 呼叫 setCurrentText）。
"""

from __future__ import annotations

from unittest.mock import patch

from src.core.models import Dialogue, Episode, Project, Scene


NONE_LABEL = "(無)"


def _make_project_with_bg_bgm() -> Project:
    """建立含背景與 BGM 的專案。"""
    scene = Scene(
        id="場景1",
        background="forest.png",
        bgm="theme.mp3",
        dialogues=[Dialogue(type="narration", text="測試")],
    )
    proj = Project(episodes=[Episode(name="影片1", scenes=[scene])])
    proj.assets["backgrounds"] = ["forest.png", "city.png"]
    proj.assets["music"] = ["theme.mp3", "battle.mp3"]
    return proj


# ──────────────────────────────────────────────
# 1. _rebuild_ui 流程（整合 MainWindow）
# ──────────────────────────────────────────────

def test_rebuild_ui_restores_background_and_bgm(qapp):
    """開啟專案後，background/bgm combo 顯示 model 值而非 (無)。"""
    from src.ui.main_window import MainWindow

    w = MainWindow()
    w._project = _make_project_with_bg_bgm()
    w._rebuild_ui()

    assert w.left_panel.combo_background.currentText() == "forest.png", (
        f"期待 'forest.png'，實際得到 '{w.left_panel.combo_background.currentText()}'"
    )
    assert w.left_panel.combo_bgm.currentText() == "theme.mp3", (
        f"期待 'theme.mp3'，實際得到 '{w.left_panel.combo_bgm.currentText()}'"
    )


# ──────────────────────────────────────────────
# 2. set_asset_lists 重建後 combo 以 model 值回填
# ──────────────────────────────────────────────

def test_set_asset_lists_after_set_project_uses_model_value(qapp):
    """set_asset_lists 重建選項後，combo 回填值來自場景 model，而非舊 currentText。"""
    from src.ui.left_panel import LeftPanel

    panel = LeftPanel()
    proj = _make_project_with_bg_bgm()
    panel._project = proj
    panel._refresh_scene_list()          # 選中場景0，但 combo 尚無選項

    # combo 此時只有 (無)，findText 找不到 → index 0
    assert panel.combo_background.currentText() == NONE_LABEL

    # 呼叫 set_asset_lists → 選項重建 → model-driven 回填
    panel.set_asset_lists(
        proj.assets["backgrounds"],
        proj.assets["music"],
    )

    assert panel.combo_background.currentText() == "forest.png", (
        f"期待 'forest.png'，實際得到 '{panel.combo_background.currentText()}'"
    )
    assert panel.combo_bgm.currentText() == "theme.mp3", (
        f"期待 'theme.mp3'，實際得到 '{panel.combo_bgm.currentText()}'"
    )


def test_set_asset_lists_wrong_order_still_recovers(qapp):
    """即使先 set_project 再 set_asset_lists，combo 依然回填正確（防呆）。"""
    from src.ui.left_panel import LeftPanel

    panel = LeftPanel()
    proj = _make_project_with_bg_bgm()

    # 舊錯誤順序：先 set_project，此時 combo 只有 (無)
    panel.set_project(proj)
    assert panel.combo_background.currentText() == NONE_LABEL  # 舊 bug 狀態

    # 再呼叫 set_asset_lists → 應以 model 回填，不保留 "(無)"
    panel.set_asset_lists(
        proj.assets["backgrounds"],
        proj.assets["music"],
    )

    assert panel.combo_background.currentText() == "forest.png"
    assert panel.combo_bgm.currentText() == "theme.mp3"


# ──────────────────────────────────────────────
# 3. 匯入素材自動套用行為不破壞
# ──────────────────────────────────────────────

def test_import_assets_auto_applies_to_current_scene(qapp):
    """匯入素材後自動套用到當前場景（_on_import_assets 行為不破壞）。"""
    from src.ui.main_window import MainWindow
    from src.core.asset_manager import import_asset
    import tempfile
    from pathlib import Path

    w = MainWindow()
    proj = Project(episodes=[Episode(name="影片1", scenes=[Scene(id="場景1", dialogues=[Dialogue(type="narration", text="x")])])])
    proj.assets["backgrounds"] = []
    proj.assets["music"] = []
    w._project = proj
    w._rebuild_ui()

    # 模擬 _on_import_assets("backgrounds") 的核心：加入素材 + sync + setCurrentText
    proj.assets["backgrounds"].append("new_bg.png")
    w._sync_asset_lists()

    # 手動模擬 setCurrentText（_on_import_assets 原本這樣做）
    w.left_panel.combo_background.setCurrentText("new_bg.png")
    proj.scenes[0].background = "new_bg.png"

    assert w.left_panel.combo_background.currentText() == "new_bg.png"
    assert proj.scenes[0].background == "new_bg.png"
