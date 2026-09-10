# 專案檢視與分支整理

日期：2026-09-10。範圍：本機 Git 所有分支關係、原始碼與測試結構、存檔與導出流程、文件、打包設定及追蹤資產。這是功能與發布範圍檢視，未完成逐行安全稽核或完整人工操作驗收。

## 分流依據

| 範圍 | 判定與處置 |
|---|---|
| 原公開 main：e45d3f3 | 作為既有功能基準；保留文字／素材／角色／舞台／特效／預覽／導出及已合併修正 |
| 本機 main 多出的 13 個提交，結束於 f7a32a3 | 多影片、角色匯入、v2 存檔及配套 UI；保留在 dev 待驗收 |
| 未提交 main.py 修改 | Windows 系統 DLL 搜尋修正，逐字保存於 dev 的 57d7591；未直接提升正式版 |
| 未追蹤的多影片計畫 | 保存於同一 dev 提交 |
| 舊計畫、工程歷程、實驗 fixture、私人小說與立繪 | 保留在 dev，移出 main；測試程式與打包設定未引用被移出的檔案 |
| 舊功能分支 | 全部保留；除 timeline POC 有一個獨立提交，其餘本機分支內容已納入原 main 歷史；POC 由舊分支保存，不重新併入產品 |

原 main 指標另保留在 `archive/main-before-release-cleanup-20260910`。main 經使用者授權重建為單一無父提交的公開基準，dev 保留開發歷史，並建立與新 main 的共同祖先關係以支援後續發布。

## 驗證結果

環境：Windows、現有 .venv、QT_QPA_PLATFORM=offscreen，先在測試程序註冊 System32 DLL 目錄。不安裝新依賴。

- **正式基準：259 passed、1 skipped，程序 exit 0。**
- 跳過 `test_capture_multi_sprite.py`：offscreen 下預設不執行 QtWebEngine 畫面截取。
- **dev 全套：** 接近結尾出現 Windows `access violation`，無正常完成摘要；已停止該測試程序。
- **dev 分檔：** 31 個測試檔完成（30 個有通過測試，1 個僅 skip），2 個 UI 測試檔各在 25 秒逾時：`test_character_import.py`、`test_main_window_episodes.py`。分檔結果不能取代整套通過，也尚未確認逾時與整套原生崩潰是否同一原因。
- 單元測試包含存讀檔、文字解析、場景／區段同步、舞台、UI 邏輯與導出命令；不代表實際影片畫面及打包產物均已驗收。

## 尚待發布驗收

1. Windows 實際啟動與互動操作，含圖片、BGM、存檔重開。
2. 多立繪、特效、音樂時序與 DPI 的 MP4 端到端驗收，以及 ZIP／HTML 的瀏覽器操作。
3. 新打包 exe 的乾淨環境啟動；Linux／macOS 未驗證。
4. dev UI 測試逾時及整套原生崩潰調查；v2 存檔不可當作 main 能回讀的格式，使用專案副本驗收。
5. 根目錄未有 LICENSE；公開授權方式需由專案擁有者決定。這次未代選授權，也未完成依賴／素材授權稽核。

## 遠端狀態與公開範圍

這次僅整理本機，沒有 fetch、push、建立遠端 release 或變更儲存庫可見性。origin/main 的判定來自本機 remote-tracking ref，正式推送前必須重新 fetch 並核對。

main 現在與舊遠端歷史不同，正式更新需在確認遠端 SHA 後使用有明確預期 SHA 的 force-with-lease，不能直接 force。不要使用 push --all 把 archive 與私人開發資料一起公開。

**乾淨的 main 不等於整個儲存庫已清除歷史內容。** dev、archive 與既有遠端 feature 分支仍保留舊歷史和測試素材；若把整個既有儲存庫轉公開，這些資料可能一起可見。公開前需決定使用新的公開儲存庫僅承載 main，或另行整理所有遠端分支。這次未刪除任何舊分支。
