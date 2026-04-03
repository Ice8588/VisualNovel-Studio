# ffmpeg 設定說明

VisualNovel Studio 的「導出影片 (MP4)」功能需要 ffmpeg。

## 下載方式

1. 前往 https://github.com/BtbN/FFmpeg-Builds/releases
2. 下載 `ffmpeg-master-latest-win64-gpl.zip`
3. 解壓縮後，將 `ffmpeg.exe` 放入此目錄（`resources/ffmpeg/`）

## 目錄結構

```
resources/
  ffmpeg/
    ffmpeg.exe    <-- 放在這裡
    README.md     <-- 本檔案
```

## 替代方案

也可以將 ffmpeg 加入系統 PATH 環境變數，程式會自動偵測。

## 注意事項

- 僅需要 `ffmpeg.exe`，不需要 `ffprobe.exe` 或其他檔案
- 建議使用 GPL 版本（包含所有編碼器）
- Windows 64-bit 版本即可
