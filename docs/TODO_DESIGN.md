# 設計系統待辦事項

本文件追蹤「VisualNovel Studio _ Design」設計檔案中**尚未套用**的項目，依規模 / 優先級分類。
原始設計檔位於專案根目錄外的 `VisualNovel Studio _ Design/`；資產已搬入 `assets/design/`。

更新日期：2026-05-02

---

## ✅ 已完成

- 6 主題 QSS（dark / light / parchment / midnight / figma-dark / ivory）
- 預設主題改為 Ivory Titanium，預設字級 18px
- Preview body class 同步 6 主題（`src/engine/style.css`）
- Noto Sans TC 5 個字重打包與啟動載入（`main.py`）
- 設計資產搬入 `assets/design/`（27 個 SVG：logo / icons / textures）
- PyInstaller spec 啟用 `PyQt6.QtSvg` + 打包 `assets/`
- 主選單 SVG icon（檔案 / 導出 / 說明）
- `_design_icon` 抽出到共用模組 `src/ui/icons.py`
- 左側面板「新增場景 / 新增角色」加 `add.svg`
- 場景 / 角色 hover 刪除按鈕（`hoverDeleteButton`）改為 `close.svg`
- SegmentEditor 浮動視窗關閉按鈕改為 `close.svg`
- EffectTimeline track 右鍵選單加 `edit.svg` / `brush.svg` / `delete.svg`
- About dialog 改寫為自訂 `QDialog`（`logo-wordmark.svg` + 版本 + 描述）

---

## 🔴 高優先（小改動，下次可做）

### 餘下未補的 button-level icon

| 元件 | 建議 icon | 位置 | 備註 |
|---|---|---|---|
| Preview 區的 play / pause / stop | `play.svg` / `pause.svg` / `stop.svg` | `src/ui/preview_widget.py` | **目前 UI 沒有播放控制按鈕**，需先實作播放控件再加 icon |
| Segment editor 的「編輯」/「刪除」 | `edit.svg` / `delete.svg` | `src/ui/segment_editor.py` | 目前 SegmentEditor 為 inline 編輯，沒有獨立編輯/刪除按鈕；待設計確認是否需新增 |
| Scene tree 展開箭頭 | `chevron-right.svg` / `chevron-down.svg` | QSS `QTreeView::branch` | 目前場景 / 角色用 `ListWidget`（無分支），待出現 `QTreeView` 時再補 QSS |

完整 21 個 icon 清單見 `assets/design/icons/`。

---

## 🟡 中優先（DESIGN.md §8–§9，Timeline 互動強化）

設計師 HANDOFF 標 🟡 的功能性改動，每項都需要寫程式 + 測試。

| 章節 | 功能 | 影響範圍 |
|---|---|---|
| §8.1 | 對話列 hover gap 顯示插入指示器（藍線 + ＋按鈕） | `dialogue_list.py` |
| §8.1 | 對話列拖曳強化（ghost card / opacity / cursor 變化） | `dialogue_list.py` |
| §8.2 | Segment lane 空格插入提示 | `stage_panel.py` / `effect_timeline.py` |
| §8.2 | Segment 拖曳整段平移 | `stage_panel.py` / `effect_timeline.py` |
| §8.4 | 視覺密度切換（ROW_HEIGHT 三段：36 / 52 / 62） | `_timeline_shared.py` + 外觀選單 |
| §9 | 對話列右鍵選單（複製 / 刪除 / 在此插入） | `dialogue_list.py` |
| §9 | Segment 右鍵選單（編輯 / 刪除 / 顏色設定） | `stage_panel.py` / `effect_timeline.py` |
| §12 | QUndoStack 整合（Ctrl+Z / Ctrl+Shift+Z） | 跨檔案，需設計 Command pattern |

每章 DESIGN.md 內有完整 PyQt6 code snippet 可參考。

---

## 🟢 低優先（DESIGN.md §10–§13，UX 細節）

| 章節 | 功能 | 影響範圍 |
|---|---|---|
| §10 | Command Palette ⌘K (`CommandPaletteDialog`) | 新增 dialog class |
| §11 | Shortcut Hint Tooltip (`ShortcutButton`) | 新增 widget class |
| §13.3 | Status Bar 進度條（取代部分 `QProgressDialog`） | `main_window.py` |
| §13.4 | 預覽重整 Loading Overlay | `preview_widget.py` |

完成 §10 / §12 後需更新 `_on_show_tutorial` 補快捷鍵說明（`main_window_patch.py` PATCH 4）。

---

## 🟠 待設計師補完

### Ivory Titanium QSS 精修

目前 `_IVORY_OVERRIDES` 是照 5 個 token（paper `#FDFDFC` / paper-2 `#F4F3EF` / ink `#1C1B19` / accent `#3A75D9` / rule `#DCDAD3`）**自動展開**的，仿照 `_LIGHT_OVERRIDES` 的 widget 覆蓋模式。

設計師若需精修 hover / pressed / disabled 細節，直接覆寫 `src/ui/theme.py` 的 `_IVORY_OVERRIDES` 即可。

### Parchment 紋理 background

HANDOFF README §5.7 提到「subtle parchment fiber texture, ~2% opacity, tileable 240×240, applied to `QMainWindow` only」。

資產已就位（`assets/design/textures/parchment.svg`），但設計師原版 `_PARCHMENT_OVERRIDES` 沒包這條規則。考量：

1. PyQt QSS 用 `background-image: url(...)` 套 SVG 在 frozen 模式下路徑處理較複雜
2. SVG 紋理覆 2% opacity 需先轉成 PNG 才能在 QSS 控制透明度
3. 設計師注意事項標記為「optional」

建議：等設計師明確要求 + 提供 PNG 版本（或同意走 `QPainter` 自繪）後再做。

### Custom icon 擴充

HANDOFF 注意事項說：「長尾 icon（folder tree chevrons / scrollbar arrows / dialog close）目前 fall back to qfluentwidgets。若要 100% 一致需擴充 `assets/design/icons/`」。

目前 21 個 icon 涵蓋主要 chrome；scroll bar / dialog 標準按鈕仍走 fluent。

---

## 🚫 故意不做（行為破壞性 / 推測過頭）

| 項目 | 出處 | 原因 |
|---|---|---|
| Tutorial 補快捷鍵 `Ctrl+K / Ctrl+Z / Ctrl+Shift+Z / Ctrl+Enter` | `main_window_patch.py` PATCH 4 | 對應功能（Command Palette / Undo / 插入對話）尚未實作，寫進去會誤導使用者 |
| `tweaks-panel.jsx` 與 `ux-prototype/` | 設計檔案 | React 互動原型，是視覺參考非程式藍圖，不適合搬到 PyQt |

---

## 參考資料

- 完整設計規格：`VisualNovel Studio _ Design/DESIGN.md`（872 行）
- 交接文件：`VisualNovel Studio _ Design/HANDOFF.md`
- Patch 範例：`VisualNovel Studio _ Design/main_window_patch.py`
- UI Kit reference：`VisualNovel Studio _ Design/ui_kits/`（4 個主題的可點擊 HTML）
