# VisualNovel Studio

給台灣文字創作者的視覺小說製作工具。
匯入文字和圖片，零學習門檻產出可分享的視覺小說。

## 功能

- **匯入文字** — 支援 `.txt` / `.docx`，自動辨識台詞（「」）與旁白
- **素材管理** — 匯入背景圖、角色立繪（PNG/JPG）、背景音樂（MP3/WAV）
- **角色系統** — 多服裝、多表情差分，名牌顏色自訂
- **舞台控制** — 每句台詞可獨立設定左/中/右三槽位立繪，說話者與畫面人物分離
- **場景編輯** — 拖拉排序場景與對話、指定背景、BGM、視覺特效（雨/雪/CRT/像素）
- **批次操作** — 多選對話列一次指定角色或設置舞台
- **即時預覽** — 內嵌 WebView 16:9 即時呈現播放效果
- **導出網頁 (ZIP)** — 打包為 HTML + JS，可上傳至 itch.io 或 Netlify
- **導出影片 (MP4)** — WYSIWYG 截幀導出，完整保留特效與樣式，透過 ffmpeg 編碼
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
5. **設置舞台** → 預覽畫面點 `+` 槽位，為每句台詞指定左/中/右立繪
6. **預覽** → 中央上方即時預覽效果
7. **導出** → 導出 > 導出網頁 (ZIP) 或 導出影片 (MP4)
8. **儲存** → 檔案 > 儲存專案

## 技術架構

```
桌面應用：Python + PyQt6 + PyQt6-Fluent-Widgets
預覽引擎：QtWebEngine（內嵌 WebView，16:9 Letterbox）
播放核心：HTML5 + Vanilla JS（無框架）
素材處理：Pillow
文件解析：python-docx
影片導出：QtWebEngine WYSIWYG 截幀 + ffmpeg 編碼
導出格式：ZIP（互動網頁）/ 單一 HTML（Base64）/ MP4
專案格式：JSON（.vnsproj）
```

## 授權

個人開發計畫。
