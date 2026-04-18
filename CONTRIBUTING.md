# Contributing to VisualNovel Studio

## 分支工作流程

- **新功能或 Bug 修復** 一律開新分支（e.g., `feature/inspector-panel`、`fix/drag-reorder`）
- 在分支上開發完成後，執行 `pytest tests/` 確認所有測試通過
- 測試全綠後才能合回 `main`

```bash
git checkout -b feature/your-feature-name
# ... 開發 ...
pytest tests/
git checkout main
git merge feature/your-feature-name
```

## 測試

```bash
pytest tests/
```

## 執行應用程式

```bash
python main.py
```

## 相依套件

```bash
pip install -r requirements.txt
```

## FFmpeg

影片導出功能需要 FFmpeg。應用程式會在首次導出時自動下載，無需手動安裝。
