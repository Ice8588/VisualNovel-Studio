# VisualNovel Studio v1.0.0

給台灣文字創作者的視覺小說製作工具。
匯入文字和圖片，零學習門檻產出可分享的視覺小說。

## 功能

- **匯入文字** — 支援 `.txt` / `.docx`，自動辨識台詞（「」）與旁白
- **素材管理** — 匯入背景圖、角色立繪（PNG/JPG）、背景音樂（MP3/WAV）
- **場景編輯** — 拖拉排序場景、指定背景與 BGM、編輯對話內容與角色
- **即時預覽** — 內嵌 WebView 即時呈現播放效果
- **導出網頁 (ZIP)** — 打包為 HTML + JS，可上傳至 itch.io 或 Netlify
- **導出影片 (MP4)** — 透過 ffmpeg 輸出影片，可上傳 YouTube 或巴哈姆特
- **專案儲存** — JSON 格式 `.vnsproj`，隨時存取

## 安裝

### 從原始碼執行

```bash
# 1. 安裝 Python 3.12+
# 2. 安裝依賴
pip install -r requirements.txt

# 3. 啟動
python main.py
```

### 從執行檔啟動（Windows）

```bash
# 打包
pip install pyinstaller
python -m PyInstaller vnstudio.spec --noconfirm

# 執行
dist/VisualNovel Studio/VisualNovel Studio.exe
```

## 影片導出

影片導出需要 ffmpeg。將 `ffmpeg.exe` 放入 `resources/ffmpeg/` 目錄，或確保 ffmpeg 在系統 PATH 中。

## 快捷鍵

| 快捷鍵 | 功能 |
|--------|------|
| Ctrl+N | 新增專案 |
| Ctrl+O | 開啟專案 |
| Ctrl+S | 儲存專案 |

## 使用流程

1. **新增專案** → 檔案 > 新增專案
2. **匯入文字** → 檔案 > 匯入文字（選擇 .txt 或 .docx）
3. **匯入素材** → 左側面板點「新增」匯入背景圖、立繪、音樂
4. **編輯場景** → 中央面板選擇場景，設定背景和 BGM，編輯對話
5. **預覽** → 右側面板即時預覽效果
6. **導出** → 導出 > 導出網頁 (ZIP) 或 導出影片 (MP4)
7. **儲存** → 檔案 > 儲存專案

## 技術架構

```
桌面應用：Python + PyQt6
預覽引擎：QtWebEngine（內嵌 WebView）
播放核心：HTML5 + Vanilla JS
素材處理：Pillow（圖片）
文件解析：python-docx（.docx 匯入）
影片導出：Pillow（幀合成）+ ffmpeg（編碼）
導出格式：ZIP（互動網頁）/ MP4（影片）
專案格式：JSON（.vnsproj）
```

## 專案結構

```
src/
├── core/           # 核心邏輯（模型、解析、導出）
│   ├── models.py
│   ├── text_parser.py
│   ├── project_io.py
│   ├── asset_manager.py
│   ├── exporter.py
│   └── exporter_video.py
├── ui/             # PyQt6 介面
│   ├── main_window.py
│   ├── center_panel.py
│   ├── left_panel.py
│   ├── right_panel.py
│   └── dialogs.py
└── engine/         # HTML/JS 播放引擎
    ├── index.html
    ├── engine.js
    └── style.css
```

## 授權

個人開發計畫。
