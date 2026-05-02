# Design Brief · VisualNovel Studio 「羊皮紙詩歌」主題

> 本文件是設計輸入稿，供 Claude Design / Figma Make / v0 / Lovable 等 AI 設計工具使用。
> 目標：在既有深色 / 淺色主題之外，新增第三種視覺風格「羊皮紙詩歌（Parchment Poetry）」。
> **不改 UX、不改佈局、不改元件階層**，只換視覺語彙。
>
> 語言：繁體中文為主，色值與 token 英文。
> 版本：v1 · 2026-04

---

## 1 · Project Snapshot

### 一段話簡介

VisualNovel Studio 是給台灣文字創作者的桌面工具。使用者匯入一份 `.txt` 或 `.docx`，加上背景圖、立繪、BGM，就能一鍵導出 MP4 影片、可分享的 HTML 網頁，或單一 HTML 檔。定位不是遊戲引擎，而是「把小說變成可播放動畫的書寫工具」。

### 核心功能優先級

1. **MP4 影片導出**（最重要，WYSIWYG 截幀 + FFmpeg）
2. **ZIP 網頁導出**（互動版，可上 itch.io）
3. **單一 HTML 導出**（Base64 打包）
4. **專案儲存**（`.vnsproj` JSON 格式）

所有視覺設計決策都必須**不傷害 MP4 導出品質**。MP4 的每一幀都要乾淨、可讀、沒有殘留 UI overlay。

### 關鍵技術限制

| 項目 | 規格 |
|---|---|
| 桌面軟體最小解析度 | 1280×720 |
| 引擎預覽比例 | 16:9 letterbox |
| 主要語言 | 繁體中文 |
| 桌面框架 | Python + PyQt6 + qfluentwidgets |
| 播放引擎 | HTML5 + Vanilla JS（無框架） |
| 字體限制 | Microsoft JhengHei / Noto Sans TC 已內建；襯線字型需使用者系統有 |

### 為什麼要新主題

現況兩種主題都是 IDE 風：深色 `#1e1e1e` / 淺色 `#eee`，強調色一律鋼藍 `#4682B4`。這個風格對工程師友善，但對**寫小說的人**不友善。使用者打開軟體時看到的是一個 Visual Studio，而不是一個寫作空間。羊皮紙詩歌主題要補回這個空缺。

### 這份 brief 的產出用途

- 貼進 Claude Design 產生 mockup 與 token JSON
- 貼進 Figma Make 產生元件庫雛形
- 貼進 v0 / Lovable 快速做 HTML 風格驗證

---

## 2 · User & Tone

### 主要使用者

- **獨立文字創作者**：寫短篇、連載、同人文的人
- **內容教學者**：國高中老師、作文班、寫作工作坊
- **同人誌圈**：製作改編劇場版、角色廣播劇
- **非技術人為主**：多數沒碰過 Unity / RPG Maker / Ren'Py

### 次要使用者

- 學生（投稿比賽、畢業製作）
- 手作社團、書店活動（把書介轉成影片）

### 情緒關鍵字（要有）

安靜、書感、手寫稿紙、晨間書房、墨水、**未裝訂的詩集**、舊藏書票、信箋、木質桌面、暖燈、紙張摩擦聲、手刻印章。

### 反面關鍵字（要避免）

- 遊戲引擎 / Unity / Unreal / RPG Maker
- 霓虹色、賽博龐克、太空感
- 企業 SaaS、Stripe、Linear、Figma 的藍紫漸層
- 過度 Material Design（Ripple、Elevation 大陰影）
- 「AI 感」（紫色漸層 + 星光 + glass morphism）

### 競品與參考基準

**可參考的美學方向：**
- Scrivener（寫作專業戶首選；紙感強）
- Ulysses（極簡寫作；米色暖調）
- iA Writer（等寬字 + 紙色）
- 一頁文化、春山出版、新經典文化（台灣獨立出版視覺）
- Claude.ai 介面（已使用 `#F4F3EE` 暖米白，是業界最接近的量產樣本）

**不要參考：**
- Unity Hub、Godot、Ren'Py 編輯器（都是典型 IDE 風）
- Notion（太企業）
- Discord、Figma（太飽和）

---

## 3 · Visual Style Direction — 羊皮紙詩歌

### Moodboard 描述（可直接貼進 Claude Design）

> 一本還沒裝訂的詩集躺在木桌上，晨光穿過紗簾落在紙頁。紙是舊黃色、略有纖維紋理、邊緣微捲。墨色是手寫的黑，不是螢幕純黑。旁邊是一支沾了墨的毛筆、一枚未乾的朱紅印章、一張剛撕下的便箋。空氣安靜，像圖書館閉館前十分鐘。
>
> 介面要讓人聯想到這個場景，而不是一個軟體。使用者打開 app 的瞬間，應該想「我可以在這裡寫東西」，而不是「我要開始幹活了」。

### 四個具體視覺錨點

**① 紙張質地**
- 主背景用羊皮紙色（非純米色，略帶橘黃）
- 極淡紋理：1% 不透明度的纖維噪點，或完全平面（讓 AI 設計工具挑一種）
- 無縫背景，可在大面積使用不會有重複感

**② 墨韻**
- 分隔線用手繪感線條（輕微粗細變化）或 hairline 淡褐
- 按鈕邊框用 `#8B7355` 系淡褐，不用純黑
- 主要動作色用朱紅 / 硃砂（Cinnabar `#C15F3C`），取代現況的鋼藍

**③ 襯線標題 + 無襯線內文**
- 標題、空狀態、Splash：中文思源宋體 / Noto Serif TC；英文 Georgia
- 介面內文、表格、按鈕：維持現況黑體（避免小字襯線在 Qt 下糊掉）
- 關鍵反差：對話框裡的**角色名牌用襯線 + 墨色**，台詞用黑體 — 像「台詞框是稿紙、名牌是印章」

**④ 留白慷慨**
- padding 較 IDE 風加大 20-30%
- 元件間距加大；但**佈局不變**（左面板仍 320px、splitter 位置不動）
- 圓角統一 4px（溫潤、但不過圓；不要 8px+ 的 Material 風）

### 四個明確「不要」

| 不要 | 原因 | 替代方案 |
|---|---|---|
| 純白 `#FFF` 背景 | 太冷、像 office 軟體 | Paper Primary `#F5ECD7` |
| 銳利黑色邊框 `#000` | 太硬、切割感強 | Ink Hairline `#D4C3A3` 淡褐 |
| 霓虹色 / 漸層按鈕 | 與「書感」完全衝突 | 單色扁平 + 朱紅強調 |
| Material ripple / elevation | 太數位、太 Google | 墨暈陰影 `0 1px 2px rgba(43,36,22,0.06)` |

### Claude / Pampas 作為業界樣本

Claude.ai 使用 `#F4F3EE`（Pampas）作為暖米白主背景，是目前最成熟的「非白暖色 UI」商業實作。本主題可借用其明度層級邏輯，但把色相再推往黃色 10-15°，讓紙感更明顯。

---

## 4 · Color Palette

### 設計原則

- 所有顏色 HSL 落在暖色區（hue 30-50°）
- 明度層級清楚：背景三階、文字三階、強調四色
- 每一對前景 / 背景組合都要通過 WCAG AA（4.5:1）

### A · Parchment Base（背景系）

| Token | Hex | HSL | 用途 |
|---|---|---|---|
| `paper-primary` | `#F5ECD7` | 42° 62% 90% | 主視窗背景、左面板、對話表格 |
| `paper-secondary` | `#EFE4C8` | 43° 57% 86% | 副面板、hover 底、GroupBox 內層 |
| `paper-deep` | `#E8D9B5` | 41° 51% 81% | 選中態底、強調區塊 |
| `paper-sheet` | `#FAF4E3` | 46° 73% 94% | 輸入框 / 卡片內部 (比主背景更亮) |
| `pampas-ref` | `#F4F3EE` | 45° 23% 94% | Claude 原色備案，可用於 toolbar 分層 |

### B · Ink（文字與邊框系）

| Token | Hex | 用途 | 對比 vs paper-primary |
|---|---|---|---|
| `ink-primary` | `#2B2416` | 主文字 | **12.3:1**（AAA） |
| `ink-secondary` | `#5C4F38` | 副文字、icon | **7.1:1**（AAA） |
| `ink-tertiary` | `#8B7355` | 分隔線、disabled 文字、placeholder | **3.8:1**（AA Large） |
| `ink-hairline` | `#D4C3A3` | 細框線、表格 gridline | — |
| `ink-mist` | `rgba(43,36,22,0.06)` | 墨暈陰影專用 | — |

### C · Accent（強調與功能色）

| Token | Hex | 用途 | 對比 vs paper-primary |
|---|---|---|---|
| `cinnabar` | `#C15F3C` | 主要動作、匯出按鈕、focus ring | **4.6:1**（AA） |
| `cinnabar-hover` | `#A84D2C` | primary hover | **6.1:1** |
| `indigo-ink` | `#3A4A6B` | 連結、選中態背景、取代原鋼藍 | **9.2:1**（AAA） |
| `indigo-ink-selected-fg` | `#FAF4E3` | 選中態文字（在 indigo 上） | **8.5:1**（AAA） |
| `seal-red` | `#8B3A2F` | 刪除確認、錯誤 | **7.8:1** |
| `moss-green` | `#5A6B3C` | 成功、匯出完成 toast | **6.3:1** |
| `amber-mark` | `#B88A2C` | 警告、未儲存提示 | **4.5:1**（AA） |

### 關鍵映射表（舊 → 新）

| 目前值（theme.py / style.css） | 新值 | 備註 |
|---|---|---|
| `#1e1e1e`（dark 主背景） | `#F5ECD7` paper-primary | |
| `#eee`（light 主背景） | `#F5ECD7` paper-primary | |
| `#4682B4` 鋼藍（強調色） | `#3A4A6B` indigo-ink | 選中、hover border |
| `#4682B4` → `#fff` 文字 | `#3A4A6B` → `#FAF4E3` | 對比度維持 |
| `#2a2a3e`（引擎對話框底） | `rgba(245,236,215,0.92)` | 半透明羊皮紙 |
| `#e05555` 刪除 hover | `#8B3A2F` seal-red | |

### 暗色備註

**不做 parchment-dark 版**。使用者要深色就用既有 dark theme。Parchment 是一種「氣氛選擇」，強制暗色會破壞紙感。

---

## 5 · Typography

### 字體堆疊（從高優先到低）

**中文襯線（標題、標章、Splash）：**
```
"Noto Serif TC", "Source Han Serif TC", "思源宋體", "PMingLiU", serif
```

**中文無襯線（介面內文、表格、按鈕）：**
```
"Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif
```

**英數襯線（標題英文、logo）：**
```
"Georgia", "Charter", "Iowan Old Style", serif
```

**英數無襯線（介面、數字）：**
```
"Inter", "Segoe UI", system-ui, sans-serif
```

### 字級階層

| 角色 | 字型 | 大小 | 行距 | 字距 | 用途 |
|---|---|---|---|---|---|
| H1 | 中文襯線 / Georgia | 32px | 1.3 | 0.02em | Splash 標題 |
| H2 | 中文襯線 | 24px | 1.35 | 0.01em | 對話框標題、區段標題 |
| H3 | 中文襯線 | 20px | 1.4 | 0 | 面板小標 |
| H4 | 中文無襯線 bold | 16px | 1.45 | 0 | GroupBox title |
| Body | 中文無襯線 | 14-18px（跟 QSettings） | 1.5 | 0 | 一般內文 |
| Caption | 中文無襯線 | 12px | 1.4 | 0.02em | 時間戳、說明文字 |
| Mono | `"JetBrains Mono", Consolas, monospace` | 13px | 1.5 | 0 | 檔名、ID、debug |

### 特殊規則

- `theme.py::apply_theme` 目前以 `font.setPixelSize(font_size)` 統一設定，使用者可調。新主題保留此機制，只補「襯線族群」作為特定元件的覆寫。
- 角色名牌（`#speaker-name`）改用襯線 + `ink-primary`；台詞（`#dialogue-text`）維持無襯線。
- 對話框內「小說本文」若有長段旁白，考慮給 option 用中文襯線（提升沉浸感）— 但此為進階、不列入 v1。

### 為什麼 body 還是用黑體

繁體中文小字用襯線在螢幕（特別是低 DPI 與 Qt 的文字渲染）會糊掉，影響專業使用者長時間編輯。襯線只用在「儀式性」的位置（標題、名牌、空狀態），保持**工具該好用、情緒該到位**的平衡。

---

## 6 · Component Style Tokens

以下針對 `src/ui/theme.py` 中 `_LIGHT_OVERRIDES` 涵蓋的元件給出視覺方向。設計工具不需要產 QSS 代碼，只要給出對應的 token 值；實作會把它們轉成 Qt Style Sheet。

### Button

**Primary（匯出、儲存、確認）**
- 背景：`cinnabar`
- 文字：`paper-sheet`
- 邊框：無
- Hover：背景 → `cinnabar-hover`
- Pressed：背景 → `#8E3A1F`，下移 1px
- Radius：4px
- Padding：8px 18px

**Secondary（一般操作）**
- 背景：`paper-sheet`
- 文字：`ink-primary`
- 邊框：1px `ink-hairline`
- Hover：邊框 → `ink-tertiary`，背景 → `paper-secondary`
- Pressed：背景 → `paper-deep`
- Radius：4px

**Ghost（工具列、連結型）**
- 背景：透明
- 文字：`ink-secondary`
- Hover：背景 → `paper-secondary`，文字 → `ink-primary`
- 邊框：無

**Danger（刪除）**
- 正常：Ghost 樣式 + 文字 `ink-tertiary`
- Hover：背景 `#F2DFD8`（seal-red 的 paper 版），文字 `seal-red`

**Dashed（dashedButton — 匯入提示用）**
- 邊框：2px dashed `ink-tertiary`
- 文字：`ink-tertiary`
- Hover：邊框 → `ink-secondary`，文字 → `ink-primary`

### Input / ComboBox / LineEdit

- 背景：`paper-sheet`
- 邊框：1px `ink-hairline`
- Radius：4px
- Padding：8px 12px
- Focus：邊框 2px `cinnabar`（不加光暈；內縮 1px 避免跳動）
- Disabled：背景 `paper-secondary`、文字 `ink-tertiary`
- Placeholder：`ink-tertiary`
- Selection 反白：背景 `indigo-ink`、文字 `paper-sheet`

**Table 內聯 ComboBox（`QComboBox#tableCombo`）**
- 無邊框，背景透明
- Hover：背景 `paper-deep`、1px `ink-hairline`

### Table（對話表格）

- 背景：`paper-sheet`
- Grid line：`ink-hairline`（1px，不粗）
- Header 底：`paper-secondary`
- Header 文字：`ink-secondary`（中等粗細）
- Row hover：背景 `#F0E5CA`
- Row selected：背景 `indigo-ink`、文字 `paper-sheet`
- Alternate row：`#F2E8D0`（比 primary 深一階）

### Scrollbar

- 極細：width 6-8px（目前 10px）
- Track：透明（hover 才淡出 `paper-secondary`）
- Thumb：`ink-tertiary` → hover `ink-secondary`
- 無箭頭按鈕

### Splitter handle

- 背景：`ink-hairline`
- Hover：`cinnabar` 漸淡（0.4 alpha）
- 寬：1px

### GroupBox

**目前做法：硬框 + 浮標題** → 改為「hairline 上緣線 + 標題貼左」
- 上緣 1px `ink-hairline`，左右 0，無下緣
- 標題貼上緣左 8px，內縮半行壓在線上
- 標題字：H4 襯線、`ink-secondary`

### Menu / Menubar / Toolbar

- Menubar 背景：`pampas-ref` `#F4F3EE`（比主背景更白，明顯分層）
- Menubar item hover：背景 `indigo-ink`、文字 `paper-sheet`
- 下拉 Menu 背景：`paper-sheet`
- Menu item hover：背景 `paper-deep`、文字不變
- 分隔線：`ink-hairline`
- Toolbar：同 menubar；icon 單色 `ink-secondary`，hover `ink-primary`

### Tab

- Tab 預設：背景 `paper-secondary`、文字 `ink-secondary`
- 選中：背景 `paper-sheet`、文字 `ink-primary`、**下緣 2px `cinnabar`**
- 無 border（靠背景層次區分）

### Tree / List

- 背景：`paper-sheet`
- 選中：背景 `indigo-ink`、文字 `paper-sheet`
- Icon：`ink-secondary`
- 展開箭頭：`ink-tertiary`

### Progress Dialog（匯出 MP4 進度）

- 背景：`paper-primary`
- Progress bar 底：`paper-deep`
- Progress bar fill：`cinnabar`
- 標題字：H3 襯線
- 備註文字：caption `ink-tertiary`

---

## 7 · HTML 播放引擎樣式（`src/engine/style.css`）

> **關鍵提醒**：這層改動會直接影響 MP4 導出觀感。使用者看到的成品（朋友收到的分享檔）長什麼樣，取決於這裡。
>
> 同時要意識到：使用者自己選的**背景圖片**可能是任何東西（森林、夜晚、太空），羊皮紙對話框要在**淺底與暗底**都能讀。

### 對話框（`#dialog-box`）

- 背景：`rgba(245,236,215,0.92)` （paper-primary + 半透明）
- 邊框：1px `rgba(139,115,85,0.4)` （ink-tertiary 半透明）
- Radius：6px
- 陰影：`0 2px 8px rgba(43,36,22,0.15)` 墨暈
- 內 Padding：20px 28px
- 位置 / 尺寸 / 離底距離：**不變**（保持現有 letterbox 邏輯）

### 角色名牌（`#speaker-name`）

- 字型：中文襯線
- 大小：`GameSettings.name_font_size` 維持不變
- 顏色：`Character.name_color` 維持（per-character 自訂不動）
- 名牌底：`paper-deep` 不透明，微縮進、左下圓角貼齊對話框上緣
- Padding：4px 14px

### 台詞文字（`#dialogue-text`）

- 字型：中文無襯線（**不用襯線**，小字可讀優先）
- 顏色：`ink-primary`
- 大小：`GameSettings.dialogue_font_size` 維持
- 打字機效果：保留（Capture Mode 自動跳過，無需改）

### 文字效果 `fx-*` 在羊皮紙底上的色調

現有 effects：`bold`, `italic`, `shake`, `glow`, `fade`, `pulse`（以實際 TEXT_EFFECTS 為準）

- `fx-bold`：粗體，顏色仍 ink-primary
- `fx-italic`：斜體，顏色不變
- `fx-shake`：抖動動畫，顏色不變
- `fx-glow`：發光 — 原本設計若是白光，在羊皮紙上不明顯，改為 `0 0 8px rgba(193,95,60,0.5)` 朱紅暈
- `fx-fade`：透明漸變不變
- `fx-pulse`：顏色往 `cinnabar` 微脈動

### UI overlay（`#stage-overlay`, `#scene-title`, 按鈕）

- **Capture Mode 必須隱藏**：現有 `body.capture-mode #stage-overlay { display:none!important }` 邏輯保留
- Stage slot 按鈕（`+` / `✕` / `▼`）：
  - 底：`paper-sheet` 半透明 0.85
  - 框：1px `ink-hairline`
  - 文字：`ink-primary`
  - Hover：框 → `cinnabar`

### Background 背景圖衝突備援

使用者可能放**暗色背景圖**（夜晚、太空）。此時純羊皮紙對話框仍可讀（半透明 0.92 已足夠對比），但若視覺需要可提供「低亮度紙」備援：
- `rgba(240,225,195,0.88)` + `ink-primary` 文字
- 或給使用者一個「對話框色調」下拉（進階功能，不列 v1）

### Loading / 音量 UI

- Loading spinner：`cinnabar` 旋轉圓（不要純色 gif）
- 音量 slider：軌道 `paper-deep`、把手 `cinnabar`、已走過部分 `ink-secondary`

### Capture Mode 注意事項

- 所有動畫（shake、pulse）在 `window.VN_CAPTURE_MODE = true` 時維持現況：引擎自行處理
- Capture 畫面**不能有**浮動按鈕、紅點、進度條
- 背景轉場在 Capture Mode 跳過（現況邏輯維持）

---

## 8 · Brand & App Icon

### App Icon 概念

**方向 A（推薦）：羊皮紙卷 + 墨痕**
- 一卷半展開的羊皮紙，紙上有一筆墨痕（像剛落筆的一橫）
- 色調：`paper-primary` 底 + `ink-primary` 墨痕 + `cinnabar` 印章點綴
- 256px 下可見印章，48px 下僅見紙卷輪廓，16px 下簡化為「一橫 + 紙邊」

**方向 B：印章**
- 一枚朱紅方印，印面刻簡體化的「VN」或「視」字
- 色調：`cinnabar` 底 + `paper-sheet` 字
- 風險：太像公司 logo、較冷硬

**方向 C：毛筆筆尖**
- 一支蘸墨的毛筆尖，滴落一滴墨
- 色調：`ink-primary` + `cinnabar` 墨滴
- 風險：動態難靜態化、小尺寸糊

### 各尺寸交付

- 256×256 PNG（應用主圖示）
- 128×128 / 48×48 / 32×32 / 16×16 PNG（Windows ICO）
- 1024×1024 PNG（macOS .icns 來源）
- 512×512 PNG（網頁 favicon 來源 & social）
- SVG 向量原檔

### Splash Screen

- 尺寸：640×400 或 800×500
- 背景：`paper-primary` + 極淡纖維紋理
- 中央上：App icon 128px
- 下方：標題「視覺小說工作室」中文襯線 28px、副標「VisualNovel Studio」Georgia italic 16px `ink-secondary`
- 底部右：版本號 `v1.0.0` caption `ink-tertiary`
- 底部左：「載入中⋯」 caption + 三點 `cinnabar` 動畫

### README 封面圖

- 尺寸：1200×600
- 構圖：左半為紙本手稿（角色設定卡、場景草圖）、右半為 app 截圖
- 右下浮標：app icon + 文字 slogan「把你的故事變成影片」
- 色調整體貼 `paper-primary`

### 社群 / OG Image

- 尺寸：1200×630（OG 標準）
- 極簡版：`paper-primary` 底 + 中央大字「VisualNovel Studio」襯線 + 下方一行副標
- 右下角印章 logo
- **要可讀於 LINE / Facebook / 小紅書縮圖**

---

## 9 · Layout Rules（佈局規則）

### 明確不改的項目

- 主視窗：左右 QSplitter，左 320px / 右佔滿
- 左面板：上下堆疊「場景列表／場景屬性／角色列表」
- 中央面板：上下堆疊「預覽區（16:9）／對話表格」
- 所有對話框的 modal / widget 階層不動
- 所有 signal / bridge / 資料流不動

### 視覺規則（僅樣式）

**間距**
- 容器 padding：現況 +4px（給空間呼吸）
- 元件垂直間隔：最少 12px，區塊之間 20px+

**圓角**
- 按鈕 / 輸入框：4px（現況 3px）
- 卡片 / GroupBox：6px
- 對話框：8px

**陰影 / 深度**
- 取消所有 Material 風陰影
- 統一用「墨暈」：`0 1px 2px rgba(43,36,22,0.06)` 小卡片
- 對話框：`0 8px 24px rgba(43,36,22,0.12)`
- 無 elevation 層級（平面優先）

**分隔**
- 區塊分隔優先用「留白 + hairline」，不用粗線
- Splitter handle：1px hairline，hover 顯示 cinnabar 微光

**動畫**
- 所有 transition 150-200ms ease-out
- 不要 bounce / spring
- Hover / focus 切換不要跳動（寬度變化用內縮補償）

---

## 10 · Key Screens

每個畫面給 Claude Design 的提示包含：主背景色、3-5 個關鍵元件、一句話情緒。

### Screen 1 · Empty State（尚無專案）

**情緒：一張空白稿紙等你開始寫。**

- 主背景：`paper-primary`
- 中央：大型虛線框（dashed button style）內含：
  - 上：App icon 96px
  - 中：H2 襯線「開始一個故事」
  - 下：Caption「拖放 `.txt` 或點此選擇檔案」
- 次要行動：下方兩個 Ghost 按鈕「開啟專案」「查看範例」
- 角落不放任何 UI chrome（刻意留白）

### Screen 2 · Main Editor（主編輯畫面）

**情緒：開著稿紙的書桌，工具在手邊。**

關鍵元件（由左至右、由上至下）：
1. 頂部 Menubar（Pampas 色分層）
2. 左面板（Paper-primary）：
   - 場景列表（Tree widget，selected 用 indigo-ink）
   - 場景屬性 GroupBox（hairline 上緣 + 襯線標題）
   - 角色列表（卡片式，每張卡 paper-sheet + hairline）
3. 中央預覽區（16:9 letterbox）：
   - 外框羊皮紙，letterbox 兩側灰白（`paper-secondary`）
   - 內部是實際引擎畫面（見 §7）
4. 中央下方對話表格：
   - Paper-sheet 底 + hairline grid
   - 選中 row 用 indigo-ink 強調
5. 底部 status bar：caption 文字 `ink-tertiary`「未儲存的變更」

### Screen 3 · Character Dialog（角色編輯對話框）

**情緒：一張角色設定卡，像桌遊說明書。**

- 對話框尺寸：640×480
- 背景：`paper-primary`
- 頂部：襯線 H2「編輯角色」 + 關閉 X
- 左側：立繪預覽區（160×240）含換圖按鈕
- 右側：
  - 角色名稱（LineEdit + color picker 名牌顏色）
  - 服裝 Tab（襯線 tab、cinnabar 下緣）
  - 每個服裝內是表情差分 grid（縮圖卡片）
- 底部：右對齊「取消」（ghost）「儲存」（primary cinnabar）

### Screen 4 · Stage Slot Picker（舞台槽位選角）

**情緒：在座位表上安排誰坐哪。**

- 輕量對話框 480×320
- 背景：`paper-primary`
- 頂部：caption「為這句台詞選擇 [左] 槽位的角色」
- 中央：角色卡片 grid（每卡 paper-sheet、hover paper-deep）
- 每卡顯示：立繪縮圖、名字（襯線）、目前服裝（caption）
- 底部：「清空此槽位」（ghost danger）

### Screen 5 · Export Dialog（匯出設定）

**情緒：送稿到印刷廠前最後確認。**

- 對話框 560×440
- 頂部 Tab：`MP4 影片` / `ZIP 網頁` / `單一 HTML`
- MP4 Tab 內容：
  - 解析度（Combo：720p / 1080p）
  - FPS（Combo：24 / 30 / 60）
  - 輸出路徑（LineEdit + 瀏覽按鈕）
  - 品質 slider（cinnabar 把手）
  - 預估檔案大小 caption
- 底部：左「取消」ghost、右「開始匯出」primary cinnabar
- 匯出中切換至 Progress Dialog（見 §6）

### Screen 6 · Playback Engine（實際 MP4 播放畫面）

**情緒：翻開一本正在說話的書。**

- 畫面比例 16:9
- 背景：使用者選的背景圖（可能為任何色調）
- 底部對話框（見 §7 規格）
- 左 / 中 / 右 三槽立繪（依 `stage` 資料）
- **無任何 UI 控制（Capture Mode 下）**
- Preview Mode 額外顯示：槽位 `+` / `✕` / `▼` 按鈕（見 §7）

---

## 11 · Prompt Pack — 可複製片段

以下三段 prompt 可分別貼進 Claude Design / Figma Make / v0。每段已自帶 context、token、規避項、期望輸出格式。

### Prompt A · 整體風格探索（第一次貼、產概念稿）

```
我在設計一個給台灣文字創作者的桌面工具「VisualNovel Studio」，
風格方向：羊皮紙詩歌（Parchment Poetry）。

請基於以下設定，產出 3 張 concept mockup：
1. 應用主畫面（左面板 + 中央預覽 + 下方對話表格）
2. 空狀態歡迎頁
3. 匯出設定對話框

色票：
- 背景：#F5ECD7（紙主）、#EFE4C8（副）、#E8D9B5（深）、#FAF4E3（卡片）
- 文字：#2B2416（主）、#5C4F38（副）、#8B7355（弱）
- 強調：#C15F3C（朱紅，主要動作）、#3A4A6B（靛墨，選中）
- 分隔線：#D4C3A3（hairline）

字型：
- 中文標題：Noto Serif TC / 思源宋體
- 中文內文：Microsoft JhengHei / Noto Sans TC
- 英文標題：Georgia
- 英文內文：Inter

情緒關鍵字：安靜、書感、手寫稿紙、晨間書房、未裝訂詩集
不要：遊戲引擎感、霓虹、漸層按鈕、Material elevation、純白背景

風格特徵：
- 留白慷慨、圓角 4-6px
- 按鈕扁平單色、朱紅主色
- 表格與卡片用 hairline 分隔而非粗框
- 標題用中文襯線、內文用黑體
- 陰影極淡（墨暈感）

輸出：靜態 mockup 圖 + 色票 token JSON。
```

### Prompt B · 主編輯畫面 Single Screen Detail

```
請幫我畫一張 1440×900 的桌面軟體編輯畫面。

結構（不可改）：
- 左右 splitter，左面板固定 320px，右側佔滿
- 左面板由上至下：場景列表（tree）/ 場景屬性（表單）/ 角色列表（卡片）
- 右側由上至下：16:9 預覽區（letterbox）/ 對話表格（QTableWidget）
- 頂部有 menubar（檔案 / 編輯 / 導出 / 說明）
- 底部有細 status bar

視覺風格：羊皮紙詩歌
- 主背景 #F5ECD7
- 卡片與輸入框 #FAF4E3
- 選中態 #3A4A6B 靛墨底 + 米白字
- 主要按鈕（如「匯出 MP4」）朱紅 #C15F3C
- 分隔線 hairline #D4C3A3
- 中文標題用襯線、內文用黑體
- 圓角 4px、陰影極淡

對話表格內容範例（繁中）：
| 角色 | 立繪 | 服裝 | 台詞 | 特效 |
| — | — | — | 下著細雨的午後，鐘聲從遠處傳來。 | — |
| 小明 | 普通 | 制服 | 「妳怎麼還在這裡？」 | shake |
| 小華 | 側臉 | 制服 | 「再等一下，就好。」 | — |

預覽區要顯示一個範例對話框（paper-primary 半透明 0.92）+ 角色名牌（襯線字 + 自訂顏色）+ 三槽立繪佔位。

不要：任何霓虹、漸層、cyber 元素、西方 fantasy 風。
輸出：單張高解析 PNG + 對應元件 style token 清單。
```

### Prompt C · HTML 播放引擎對話框（Capture Mode）

```
請幫我設計一個視覺小說播放介面的對話框 UI（HTML + CSS），
這是 MP4 影片匯出時實際被截圖的畫面。

基礎規格：
- 畫面比例 16:9（1920×1080 基準）
- 背景圖為使用者自訂（示例請用一張淡色森林背景）
- 對話框位於畫面下方，寬度滿版、離底 64px、高約 220px
- 畫面上同時有三槽立繪（左 / 中 / 右），此示例左與中有立繪

對話框視覺：
- 底色 rgba(245,236,215,0.92) 半透明羊皮紙
- 邊框 1px rgba(139,115,85,0.4)
- 圓角 6px
- 陰影 0 2px 8px rgba(43,36,22,0.15)
- 內距 20px 28px

角色名牌（在對話框左上，微凸出）：
- 底色 #E8D9B5 不透明
- 文字襯線（Noto Serif TC）#2B2416
- 角色自訂名牌色覆寫時以 color 呈現
- 範例角色：小明（色 #4682B4）

台詞文字：
- 無襯線（Microsoft JhengHei）
- 顏色 #2B2416
- 字級 28px
- 範例文字：「下著細雨的午後，鐘聲從遠處傳來，她沒有回頭。」

額外要求：
- Capture Mode — 畫面上不能有任何按鈕、進度條、提示
- 要在淺色背景與暗色背景下都可讀（請一併示範兩版）

輸出：HTML + CSS（純靜態、無 JS），對應 class 名稱使用 #dialog-box / #speaker-name / #dialogue-text。
```

### Prompt 使用建議

- 初次先用 Prompt A 產概念稿，看整體方向對不對
- 方向確認後用 Prompt B 要詳細主畫面
- 對話框單獨用 Prompt C 確認（因為會影響 MP4 成品）
- 若 Claude Design 產出仍太「科技」，在 prompt 最後加一句：
  > 請把整體風格再往「台灣獨立出版社封面、手工書、一頁文化」方向推，減弱任何軟體感與 AI 感。
- 若產出顏色飽和度過高，補一句：
  > 所有顏色都必須是「褪色的、像翻過幾年的書」的質感。

---

## 12 · Deliverables & Next Steps

### 從 Claude Design 應期望拿到什麼

1. 3-6 張主畫面 mockup（PNG / Figma frame）
2. 完整 token JSON（色、radius、spacing、typography）
3. 元件庫雛形（Button、Input、Card、Dialog 各狀態）
4. App icon 至少 2 個方向各 4 尺寸

### 後續套用到 repo 的 3 步流程

這份 brief **不執行**以下實作，只是給出方向。實作為後續任務：

**Step 1 · Python 端（`src/ui/theme.py`）**
- 增加 `_PARCHMENT_OVERRIDES` 字串常數（對應 _LIGHT_OVERRIDES 結構）
- `apply_theme(app, theme_name, font_size)` 的 `theme_name` 接受 `"parchment"`
- `apply_custom_overrides()` 依 theme_name 選 template
- `qfluentwidgets.setTheme`：目前只有 `Theme.LIGHT / Theme.DARK`，parchment 先共用 LIGHT 作基底，再用 QSS 覆寫（qfluentwidgets 不支援自訂 theme，硬上 QSS 即可）

**Step 2 · 引擎端（`src/engine/style.css` + `engine.js`）**
- 在 body 加 `theme-parchment` class
- `style.css` 新增 `body.theme-parchment #dialog-box { ... }` 等規則
- `engine.js` 於啟動時讀 `SCRIPT_DATA.theme`（新欄位）並 `document.body.classList.add("theme-" + theme)`
- 匯出端（`preview_widget.py` / `webengine_capture.py` / `exporter_html.py`）把目前主題傳給 script data

**Step 3 · 資料模型（`src/core/models.py`）**
- `GameSettings` 增加 `theme: str = "default"` 欄位
- `to_script_json()` 寫出 `"theme"` 欄
- `Project.from_dict()` 向下相容（舊檔預設 default）

### 不納入此 brief 的項目

- 修改 UX / 流程
- 新增功能按鈕
- 改動 engine.js 行為邏輯
- 改動測試
- 改 CLAUDE.md / README / CONTRIBUTING
- 實作本身（見 Step 1-3，屬後續）

### 驗收標準

設計產出成功的判斷：
1. 把 Claude Design 產出的主畫面截圖拿給任何一位**不寫程式**的朋友看，問「這是什麼軟體？」回答是「寫作 / 電子書 / 排版」而不是「遊戲引擎 / 後台管理」→ 風格達標
2. 色票 token JSON 可以直接貼進 `theme.py` 轉成 QSS
3. 對話框設計在淺色與暗色背景圖下都可讀（對比 WCAG AA）
4. App icon 在 16px 下仍可辨識

---

## References

### Claude Design 官方資源
- [Get started with Claude Design — Anthropic Help Center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- [Claude Design: Complete Guide for Non-Designers (2026)](https://www.buildfastwithai.com/blogs/claude-design-anthropic-guide-2026)
- [How to Use Claude Design for Product Mockups (2026)](https://aigcdev.com/en/articles/claude-design-tutorial-2026)

### 色彩與品牌參考
- [Claude Brand Color Palette — Mobbin](https://mobbin.com/colors/brand/claude) — Crail `#C15F3C`、Pampas `#F4F3EE`
- [Claude Brand Color Codes — BrandColorCode](https://www.brandcolorcode.com/claude)
- [Parchment Color #F1E9D2 — Figma](https://www.figma.com/colors/parchment/)

### 美學方向對標
- Scrivener（寫作軟體紙感範本）
- Ulysses（極簡暖米介面）
- iA Writer（紙色 + 等寬）
- 一頁文化、春山出版、新經典文化（台灣出版視覺）

### 專案內參考檔案
- [src/ui/theme.py](../src/ui/theme.py) — `_DARK_OVERRIDES` / `_LIGHT_OVERRIDES` 結構作為元件清單依據
- [src/engine/style.css](../src/engine/style.css) — 播放引擎 selector 範圍
- [CLAUDE.md](../CLAUDE.md) — 架構概覽與同步規則
- [README.md](../README.md) — 功能與快捷鍵

---

*本 brief 由設計師、前端工程師、PM 共同維護。修改請保留章節編號與 token 命名，避免打破已產出的 mockup 參照。*
