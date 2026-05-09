"""集中管理：主題感知 semantic colors + 註冊器。

設計動機
--------
原本 timeline paint 端用 `_timeline_shared.py` 的 6 份 palette；
QSS 端用 `theme.py` 的 6 份字串模板；setStyleSheet 直接寫 hex 散落各處。
本模組統一三條路徑：

1. **Palette dataclass**：所有 widget 共用的 semantic 色彩名稱
   （bg / surface / text_primary / text_muted / accent / warning / border ...）
2. **6 主題各一份 Palette 實例**
3. **register_themed(widget, builder)** 註冊器：widget 提供 `lambda p: f"...{p.bg}..."`
   切主題時自動重套 stylesheet，不會漏掉
4. `_timeline_shared.py` 透過 `__getattr__` 動態 forward 到本模組

Critical：本模組是 single source of truth，新增主題色只動這裡。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import weakref

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget


@dataclass(frozen=True)
class Palette:
    """單一主題的所有 semantic 顏色。

    使用約定：
    - bg / surface / surface_alt：依層級從外到內
    - text_primary / text_secondary / text_disabled：對比強度遞減
    - accent：品牌主色（按鈕主動作、focus、選中等）
    - warning / danger / info：狀態色
    - border：分隔線、邊框
    - cursor / drop_indicator：所有主題共用同一色（保持品牌識別）
    - card_dialogue_bg / card_narration_bg：dialogue_list 卡片底色
    - grid_line / row_alt：timeline 列分隔線 / alternating bg
    """

    name: str
    is_dark: bool

    bg: QColor              # window / panel root
    surface: QColor         # 第一層內層（header bar / panel inset）
    surface_alt: QColor     # 第二層（hover / pressed bg）

    text_primary: QColor    # 主要可讀文字
    text_secondary: QColor  # muted / secondary
    text_disabled: QColor

    accent: QColor          # 品牌主色（focus / 主按鈕）
    accent_hover: QColor

    warning: QColor         # 警告（橙）
    danger: QColor          # 錯誤（紅）
    info: QColor            # 資訊（藍）

    border: QColor          # 分隔線
    border_focus: QColor

    grid_line: QColor       # timeline 列分隔
    row_alt: QColor         # timeline alternating bg

    cursor: QColor          # timeline 游標線（主題共用 #FFB300）
    drop_indicator: QColor  # drag-drop 提示（主題共用 #00B7C3）

    card_dialogue_bg: QColor
    card_narration_bg: QColor

    # QSS 額外的 widget 專用色（從 theme.py 提煉）
    button_bg: QColor       # QPushButton 預設背景（比 surface 略淺/略深）
    button_hover: QColor    # QPushButton hover
    input_bg: QColor        # QLineEdit / QPlainTextEdit / QSpinBox bg
    accent_text: QColor     # accent 上對比的文字（通常白）
    title_bar: QColor       # menu / toolbar 條的背景（通常 == surface 但可不同）


_CURSOR = QColor("#FFB300")
_DROP   = QColor("#00B7C3")


_PALETTES: dict[str, Palette] = {
    "dark": Palette(
        name="dark", is_dark=True,
        bg=QColor("#1E1E1E"), surface=QColor("#2B2B2B"), surface_alt=QColor("#2D2D30"),
        text_primary=QColor("#DDDDDD"), text_secondary=QColor("#9AA0A6"), text_disabled=QColor("#666666"),
        accent=QColor("#4682B4"), accent_hover=QColor("#5A9BD6"),
        warning=QColor("#E0A020"), danger=QColor("#E05555"), info=QColor("#4682B4"),
        border=QColor("#3C3C3C"), border_focus=QColor("#4682B4"),
        grid_line=QColor(255, 255, 255, 18), row_alt=QColor(255, 255, 255, 6),
        cursor=_CURSOR, drop_indicator=_DROP,
        card_dialogue_bg=QColor("#2E3440"), card_narration_bg=QColor("#2D2D30"),
        button_bg=QColor("#3C3C3C"), button_hover=QColor("#4A4A4A"),
        input_bg=QColor("#1E1E1E"), accent_text=QColor("#FFFFFF"),
        title_bar=QColor("#2B2B2B"),
    ),
    "light": Palette(
        name="light", is_dark=False,
        bg=QColor("#EEEEEE"), surface=QColor("#F5F5F5"), surface_alt=QColor("#E8E8E8"),
        text_primary=QColor("#333333"), text_secondary=QColor("#6E6E73"), text_disabled=QColor("#A0A0A0"),
        accent=QColor("#4682B4"), accent_hover=QColor("#3A75D9"),
        warning=QColor("#D17B0A"), danger=QColor("#C43434"), info=QColor("#4682B4"),
        border=QColor("#CCCCCC"), border_focus=QColor("#4682B4"),
        grid_line=QColor(0, 0, 0, 32), row_alt=QColor(0, 0, 0, 8),
        cursor=_CURSOR, drop_indicator=_DROP,
        card_dialogue_bg=QColor("#E5EFFA"), card_narration_bg=QColor("#F5F5F5"),
        button_bg=QColor("#E8E8E8"), button_hover=QColor("#DDDDDD"),
        input_bg=QColor("#FFFFFF"), accent_text=QColor("#FFFFFF"),
        title_bar=QColor("#F5F5F5"),
    ),
    # 羊皮紙詩歌：對齊 Design preview/colors-paper.html + accents.html
    # paper #F5ECD7 / paper-2 #EADFBF / ink #2B2416 / vermilion #C15F3C / indigo #3A4A6B
    "parchment": Palette(
        name="parchment", is_dark=False,
        bg=QColor("#F5ECD7"), surface=QColor("#EADFBF"), surface_alt=QColor("#DBCBA0"),
        text_primary=QColor("#2B2416"), text_secondary=QColor("#5A4E36"), text_disabled=QColor("#8A7B5C"),
        accent=QColor("#3A4A6B"), accent_hover=QColor("#4A5A7B"),  # indigo (selected/focus/link)
        warning=QColor("#C15F3C"), danger=QColor("#C15F3C"), info=QColor("#3A4A6B"),
        border=QColor("#C9B98E"), border_focus=QColor("#3A4A6B"),
        grid_line=QColor(120, 90, 40, 60), row_alt=QColor(120, 90, 40, 14),
        cursor=_CURSOR, drop_indicator=_DROP,
        card_dialogue_bg=QColor("#FCF6E3"), card_narration_bg=QColor("#EADFBF"),
        button_bg=QColor("#EADFBF"), button_hover=QColor("#DBCBA0"),
        input_bg=QColor("#FCF6E3"), accent_text=QColor("#F5ECD7"),  # paper-on-indigo
        title_bar=QColor("#EADFBF"),
    ),
    # Ivory Titanium：對齊 Design preview/theme-ivory-titanium.html
    # bg #E8E7E2 / surface #EEECE6 / surface_alt #D6D3CB / accent #3A75D9 / text #1C1B19
    "ivory": Palette(
        name="ivory", is_dark=False,
        bg=QColor("#E8E7E2"), surface=QColor("#EEECE6"), surface_alt=QColor("#D6D3CB"),
        text_primary=QColor("#1C1B19"), text_secondary=QColor("#6E6C67"), text_disabled=QColor("#A39F92"),
        accent=QColor("#3A75D9"), accent_hover=QColor("#2E63C2"),
        warning=QColor("#C85C3C"), danger=QColor("#C85C3C"), info=QColor("#3A75D9"),
        border=QColor("#DCDAD3"), border_focus=QColor("#3A75D9"),
        grid_line=QColor(0, 0, 0, 28), row_alt=QColor(0, 0, 0, 8),
        cursor=_CURSOR, drop_indicator=_DROP,
        card_dialogue_bg=QColor("#EAF1FA"), card_narration_bg=QColor("#EEECE6"),
        button_bg=QColor("#EEECE6"), button_hover=QColor("#E1DFD8"),
        input_bg=QColor("#FFFFFF"), accent_text=QColor("#F5F3EE"),
        title_bar=QColor("#D6D3CB"),
    ),
    # Midnight Ink：對齊 Design preview/theme-midnight-ink.html
    # bg #0A0A0A / surface #141414 / accent #7090A0（霧霾藍灰，跟設計一致）
    "midnight": Palette(
        name="midnight", is_dark=True,
        bg=QColor("#0A0A0A"), surface=QColor("#141414"), surface_alt=QColor("#1A1A1A"),
        text_primary=QColor("#F0F0F0"), text_secondary=QColor("#B0B0B0"), text_disabled=QColor("#606060"),
        accent=QColor("#7090A0"), accent_hover=QColor("#8AAAB8"),  # 設計用的霧霾藍灰
        warning=QColor("#E0A020"), danger=QColor("#C85555"), info=QColor("#7090A0"),
        border=QColor("#2A2A2A"), border_focus=QColor("#7090A0"),
        grid_line=QColor(255, 255, 255, 16), row_alt=QColor(255, 255, 255, 5),
        cursor=_CURSOR, drop_indicator=_DROP,
        card_dialogue_bg=QColor("#1A1C22"), card_narration_bg=QColor("#161616"),
        button_bg=QColor("#1E1E1E"), button_hover=QColor("#252525"),
        input_bg=QColor("#141414"), accent_text=QColor("#F8F3EE"),  # 設計裡的奶白
        title_bar=QColor("#161616"),
    ),
    # Figma Dark：對齊 Design preview/theme-figma-dark.html
    # 高對比 IDE 感、深紫底調、signature accent #B06EF7（vibrant purple）
    "figma-dark": Palette(
        name="figma-dark", is_dark=True,
        bg=QColor("#0D0D12"), surface=QColor("#16151E"), surface_alt=QColor("#1C1B26"),
        text_primary=QColor("#FFFFFF"), text_secondary=QColor("#9090B8"), text_disabled=QColor("#5A5878"),
        accent=QColor("#B06EF7"), accent_hover=QColor("#7C4FD4"),  # signature vibrant purple
        warning=QColor("#FFA940"), danger=QColor("#FF5C7C"), info=QColor("#B06EF7"),
        border=QColor("#2A2738"), border_focus=QColor("#B06EF7"),
        grid_line=QColor(176, 110, 247, 28), row_alt=QColor(255, 255, 255, 5),
        cursor=_CURSOR, drop_indicator=_DROP,
        card_dialogue_bg=QColor("#1E1D2C"), card_narration_bg=QColor("#1C1B26"),
        button_bg=QColor("#1E1D2A"), button_hover=QColor("#252338"),
        input_bg=QColor("#1C1B28"), accent_text=QColor("#F8F0FF"),
        title_bar=QColor("#1A1928"),
    ),
}

_current_name: str = "dark"


def current() -> Palette:
    return _PALETTES.get(_current_name, _PALETTES["dark"])


def current_theme() -> str:
    return _current_name


def is_light() -> bool:
    return not current().is_dark


# ── 註冊器：widget 提供 builder(p)→str（QSS 字串），切主題時自動重套 ──

# 用 weakref 避免延長 widget 生命；widget 被 GC 時自動移除
_registry: list[tuple[weakref.ReferenceType, Callable[[Palette], str]]] = []


def register_themed(widget: QWidget, builder: Callable[[Palette], str]) -> None:
    """註冊 widget 與其 stylesheet builder。

    建議用法：
        palette.register_themed(self, lambda p: f"background:{p.surface.name()};")

    builder 接收當前 Palette，回傳完整 QSS 字串。註冊當下會立即套一次。
    主題切換時 set_theme() 會自動再套；widget GC 時自動清掉。
    """
    ref = weakref.ref(widget)
    _registry.append((ref, builder))
    _apply_one(widget, builder, current())


def _apply_one(widget: QWidget, builder: Callable[[Palette], str], pal: Palette) -> None:
    try:
        widget.setStyleSheet(builder(pal))
    except RuntimeError:
        # 底層 C++ widget 已被刪除（Qt object lifetime）— 忽略，下次 GC 會清
        pass


def set_theme(theme_name: str) -> None:
    """切主題：更新內部狀態 + 廣播給所有註冊 widget。"""
    global _current_name
    if theme_name not in _PALETTES:
        # fallback 用 qfluentwidgets isDarkTheme 推斷
        try:
            from qfluentwidgets import isDarkTheme
            theme_name = "dark" if isDarkTheme() else "light"
        except ImportError:
            theme_name = "dark"

    _current_name = theme_name
    pal = current()

    # 走 registry，移除已 GC 的 entry
    alive: list[tuple[weakref.ReferenceType, Callable[[Palette], str]]] = []
    for ref, builder in _registry:
        widget = ref()
        if widget is None:
            continue
        _apply_one(widget, builder, pal)
        alive.append((ref, builder))
    _registry[:] = alive


def qss_substitutions(pal: Palette | None = None) -> dict:
    """把 Palette 轉成 QSS template format() 用的字串 dict。

    給 theme.apply_custom_overrides 用：把 _QSS_TEMPLATE 的 {accent}、{bg} 等
    占位符填進當前主題的 hex 字串。
    """
    p = pal or current()
    return {
        "bg":             p.bg.name(),
        "surface":        p.surface.name(),
        "surface_alt":    p.surface_alt.name(),
        "title_bar":      p.title_bar.name(),
        "button_bg":      p.button_bg.name(),
        "button_hover":   p.button_hover.name(),
        "input_bg":       p.input_bg.name(),
        "text_primary":   p.text_primary.name(),
        "text_secondary": p.text_secondary.name(),
        "text_disabled":  p.text_disabled.name(),
        "accent":         p.accent.name(),
        "accent_hover":   p.accent_hover.name(),
        "accent_text":    p.accent_text.name(),
        "warning":        p.warning.name(),
        "danger":         p.danger.name(),
        "info":           p.info.name(),
        "border":         p.border.name(),
        "border_focus":   p.border_focus.name(),
    }


def contrast_text(bg: QColor) -> QColor:
    """依 YIQ 公式回傳對比色（深色底→白、淺色底→黑）。

    供 paint 端使用：當背景色由資料（角色名色 / 效果類型色）決定，
    文字顏色不能寫死為主題的 text_primary。
    """
    yiq = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
    return QColor("#1E1E1E") if yiq >= 140 else QColor("#FFFFFF")
