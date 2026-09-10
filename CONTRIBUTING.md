# 開發指南

## 分支與發布

- `main`：正式公開內容，不直接進行功能開發。
- `dev`：開發整合分支，包含尚待驗收的功能。統一使用小寫名稱。
- `feature/*`、`fix/*`：一律從 `dev` 建立，完成後合回 `dev`。
- `archive/*`：整理前的歷史備份，不作為新開發起點。

```bash
git switch dev
git switch -c feature/your-feature
# 開發、驗證並提交
git switch dev
git merge --no-ff feature/your-feature
```

正式發布前，確認預定發布內容全部成熟，完成測試、Windows 啟動與存讀檔操作、MP4／ZIP／HTML 驗收，再更新 README、CHANGELOG。skip、逾時、原生崩潰與未執行的人工檢查都必須如實記錄。

當 `dev` 的全部差異都屬於這次發布範圍時：

```bash
git switch main
git merge --squash dev
git diff --cached --check
# 核對暫存差異並驗證後，建立一個描述正式成果的發布提交
git commit
git switch dev
git merge --no-ff main
```

若 `dev` 混有未完成工作，先從 `main` 建立 `release/*`，只移入通過驗收的完整變更，完成後再以 squash 整合至 `main`，並將 `main` 合回 `dev`。檢查是否誤帶入開發計畫、私人測試素材或歷史紀錄。

2026-09-10 經專案擁有者授權，main 重建為單一公開基準提交；舊歷史保留於 dev 與 archive。後續不要反覆重寫公開歷史。以 `git log --first-parent --oneline main` 檢視發布紀錄，使用 [CHANGELOG](CHANGELOG.md) 閱讀產品摘要。

舊 feature 分支保留供追溯；新工作從 dev 重開。推送、版本標籤、變更儲存庫可見性與遠端保護規則需另行確認。

## 環境設定

使用 Python 3.12 以上，依賴安裝在專案 `.venv`。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe main.py
```

Linux / macOS（這次整理未驗證）：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install pytest
.venv/bin/python main.py
```

## 測試

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest tests/ -q -ra
```

Linux / macOS 使用 `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -q -ra`。

部分由 Conda Python 建立的 Windows venv 需註冊系統 DLL 路徑才能載入 Qt。可在單次測試程序使用：

```powershell
.\.venv\Scripts\python.exe -c "import os,pytest; dll=os.add_dll_directory(os.path.join(os.environ['SystemRoot'],'System32')); raise SystemExit(pytest.main(['tests/','-q','-ra']))"
```

`offscreen` 預設跳過多立繪畫面測試。實際桌面驗收時，清除 `QT_QPA_PLATFORM`，設定 `VNSTUDIO_E2E=1` 再執行 `tests/test_capture_multi_sprite.py`。另外實際導出 MP4，確認雙人物、特效、音樂與解析度；截圖測試會攔截編碼，不能取代完整 MP4 驗收。

## Windows 打包

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller vnstudio.spec --noconfirm
```

交付 `dist/VisualNovel Studio/` 完整資料夾，並在目標 Windows 環境測試啟動及導出。

FFmpeg 先從 `resources/ffmpeg/` 與系統 `PATH` 搜尋；Windows UI 可經使用者同意下載，其他平台需手動安裝。

## 文件分工

- `README.md`：使用者指南。
- `CHANGELOG.md`：產品成果，不放逐次修正紀錄。
- `docs/REPOSITORY_REVIEW.md`：功能分類、驗證與尚未完成的發布檢查。
- 開發計畫、待辦、歷史 ADR 與實驗 fixture 保留在 `dev`；歷史中的分支流程以本指南為準。
