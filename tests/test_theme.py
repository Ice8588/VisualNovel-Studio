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


def test_apply_theme_light_mode_no_error(qapp):
    """apply_theme 套用淺色主題時不應拋出例外，stylesheet template 格式正確。"""
    from src.ui.theme import apply_theme

    # 不應拋出任何例外（尤其是 KeyError，代表 }} 轉義正確）
    apply_theme(qapp, "light", 14)
    font = qapp.font()
    families = font.families()

    assert len(families) >= 2, f"期望有 fallback 字體，實際: {families}"
    assert "Microsoft JhengHei" in families
