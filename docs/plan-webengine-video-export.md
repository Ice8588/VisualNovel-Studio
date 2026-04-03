# 計畫：Headless QtWebEngine 截幀影片導出（v2）

## Context

目前影片導出使用 Pillow 逐幀合成（v1），無法渲染 Canvas 特效（rain/snow/crt/pixel_dark）、CSS 動畫、Markdown 樣式。v2 改用 headless QtWebEngine 載入同一套播放引擎，截取真實畫面，達到 WYSIWYG。

**目標**：新增 WebEngine 截幀導出器，取代 Pillow 方案為預設影片導出方式。保留 v1 程式碼作為 fallback（不刪除）。

---

## 需要修改的檔案

| 檔案 | 動作 | 說明 |
|------|------|------|
| `src/engine/engine.js` | 修改 | 加入 Capture Mode API |
| `src/ui/webengine_capture.py` | **新增** | WebEngine 截幀導出器 |
| `src/ui/main_window.py` | 修改 | 改用 v2 導出器 |
| `src/ui/preview_widget.py` | 修改 | 補上遺漏的 effects.js 複製 |
| `tests/test_webengine_capture.py` | **新增** | v2 導出器測試 |

---

## 步驟 1：修改 `src/engine/engine.js` — 加入 Capture Mode

### 1.1 在 IIFE 內部頂端，緊接 `var SKIP_INTERVAL = 100;` 之後，插入：

```javascript
// ── Capture Mode（影片導出用，跳過動畫/音訊） ──
var CAPTURE_MODE = (typeof window.VN_CAPTURE_MODE !== 'undefined' && window.VN_CAPTURE_MODE);
if (CAPTURE_MODE) {
  TYPEWRITER_SPEED = 0;
  FADE_DURATION = 0;
}
```

**位置**：第 8 行（`var FADE_DURATION = 500;`）之後。

### 1.2 在 `enterScene` 函式的背景切換邏輯中，加入 `CAPTURE_MODE` 條件

找到這段（約第 148 行）：
```javascript
      if (isSkipping) {
```
改為：
```javascript
      if (isSkipping || CAPTURE_MODE) {
```

這讓 Capture Mode 跳過背景轉場動畫（直接切換，不用 setTimeout）。

### 1.3 在 `showDialogue` 函式中，讓 Capture Mode 跳過打字機效果

找到這段（約第 267 行）：
```javascript
    if (isSkipping) {
      els.dialogueText.innerHTML = mdToHtml(d.text);
      isTyping = false;
    } else {
```
改為：
```javascript
    if (isSkipping || CAPTURE_MODE) {
      els.dialogueText.innerHTML = mdToHtml(d.text);
      isTyping = false;
    } else {
```

### 1.4 在 `startNewBgm` 函式開頭，加入 Capture Mode 靜音

找到 `function startNewBgm(filename) {`（約第 518 行），在函式內第一行加入：
```javascript
    if (CAPTURE_MODE) return;
```

### 1.5 替換底部的 DOMContentLoaded 事件綁定

找到最後一行（約第 658 行）：
```javascript
  document.addEventListener("DOMContentLoaded", init);
```
替換為：
```javascript
  document.addEventListener("DOMContentLoaded", function () {
    init();
    if (CAPTURE_MODE) {
      // 暴露截幀控制 API 給 Python 端呼叫
      window.VNCaptureAPI = {
        /** 切換到指定場景（會觸發背景/特效切換 + 顯示第一句對話） */
        goToScene: function (sIdx) {
          sceneIndex = sIdx;
          dialogueIndex = 0;
          enterScene(sIdx);
        },
        /** 切換到當前場景的指定對話（不重設背景/特效） */
        goToDialogue: function (dIdx) {
          dialogueIndex = dIdx;
          showDialogue();
        },
        /** 查詢場景資訊 */
        getInfo: function () {
          if (!scriptData) return null;
          return {
            sceneCount: scriptData.scenes.length,
            scenes: scriptData.scenes.map(function (s) {
              return {
                dialogueCount: s.dialogues ? s.dialogues.length : 0,
                effect: s.effect || null,
                background: s.background || null,
                bgm: s.bgm || null
              };
            })
          };
        }
      };
    }
  });
```

**注意**：原本的 `init` 單獨作為 listener，現在改成包在匿名函式裡。非 CAPTURE_MODE 時行為完全不變。

### 1.6 驗證 engine.js 改動

- 用 `python main.py` 啟動應用，確認預覽播放**行為不變**（CAPTURE_MODE 未設定時不受影響）。
- 在瀏覽器 console 確認 `typeof VNCaptureAPI === 'undefined'`（非 capture mode 不暴露 API）。

---

## 步驟 2：修復 `src/ui/preview_widget.py` — 複製 effects.js

### 2.1 問題

目前 `preview_widget.py` 只複製 `engine.js` 和 `style.css`，遺漏了 `effects.js`。
`index.html` 第 49 行引用 `<script src="effects.js"></script>`，因此預覽沒有特效。

### 2.2 修改

找到第 53 行：
```python
        for filename in ("engine.js", "style.css"):
```
改為：
```python
        for filename in ("engine.js", "effects.js", "style.css"):
```

### 2.3 驗證

啟動應用，在場景屬性設定 effect 為 "rain"，重新整理預覽，應能看到雨滴粒子。

---

## 步驟 3：新增 `src/ui/webengine_capture.py` — WebEngine 截幀導出器

### 3.1 完整程式碼

建立 `src/ui/webengine_capture.py`，完整內容如下：

```python
"""影片導出 v2：Headless QtWebEngine 截幀 + ffmpeg 編碼。

復用前端播放引擎（engine.js + effects.js + style.css），
透過 VNCaptureAPI 驅動畫面，逐幀截取後交給 ffmpeg 編碼。
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from PyQt6.QtCore import QEventLoop, QSize, Qt, QTimer, QUrl
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

from src.core.models import Project

logger = logging.getLogger(__name__)

ENGINE_DIR = Path(__file__).parent.parent / "engine"


def _calc_duration(text: str) -> float:
    """依字數計算停留秒數，與前端 Auto 模式邏輯一致。"""
    duration = 1.0 + len(text) * 0.15
    return max(1.5, min(duration, 8.0))


class WebEngineVideoExporter:
    """使用 headless QtWebEngine 截幀的影片導出器。

    必須在主執行緒（有 QApplication 的執行緒）呼叫。
    """

    def __init__(
        self,
        project: Project,
        output_path: Path,
        resolution: tuple[int, int] = (1920, 1080),
        fps: int = 30,
    ):
        self._project = project
        self._output_path = Path(output_path)
        self._resolution = resolution
        self._fps = fps

        from src.core.ffmpeg_manager import ensure_ffmpeg_or_raise
        self._ffmpeg = ensure_ffmpeg_or_raise()

    # ── 公開介面 ──

    def export(self, progress_callback=None) -> None:
        """執行完整導出管線。

        Args:
            progress_callback: 可選，簽名 (current: int, total: int) -> None
        """
        scenes = self._project.scenes
        if not scenes:
            raise ValueError("專案中沒有場景，無法導出影片。")
        total_dialogues = sum(len(s.dialogues) for s in scenes)
        if total_dialogues == 0:
            raise ValueError("專案中沒有對話內容，無法導出影片。")

        temp_dir = Path(tempfile.mkdtemp(prefix="vnstudio_v2_"))
        view: QWebEngineView | None = None

        try:
            # 1. 準備引擎檔案
            self._prepare_engine_files(temp_dir)

            # 2. 建立離屏 WebEngineView
            view = self._create_offscreen_view()

            # 3. 載入 HTML 並等待完成
            self._load_and_wait(view, temp_dir / "index.html")

            # 4. 等待引擎初始化（DOMContentLoaded + JS 執行）
            self._sleep_ms(500)

            # 5. 逐場景、逐對話截幀
            concat_entries, audio_timeline = self._capture_all_frames(
                view, temp_dir, progress_callback, total_dialogues
            )

            # 6. 寫入 concat 文件
            concat_path = temp_dir / "concat.txt"
            self._write_concat_file(concat_path, concat_entries)

            # 7. ffmpeg 編碼
            self._encode_video(concat_path, audio_timeline, temp_dir)

        finally:
            if view is not None:
                view.close()
                view.deleteLater()
                # 讓 Qt 處理 deleteLater
                QApplication.processEvents()
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ── 引擎檔案準備 ──

    def _prepare_engine_files(self, temp_dir: Path) -> None:
        """複製引擎檔案到暫存目錄，注入 SCRIPT_DATA + VN_CAPTURE_MODE。"""
        script_data = self._project.to_script_json()

        # 複製 engine.js, effects.js, style.css
        for filename in ("engine.js", "effects.js", "style.css"):
            src = ENGINE_DIR / filename
            if src.exists():
                (temp_dir / filename).write_text(
                    src.read_text(encoding="utf-8"), encoding="utf-8"
                )

        # 複製 index.html 並注入 capture mode + script data
        index_src = ENGINE_DIR / "index.html"
        html = index_src.read_text(encoding="utf-8")
        inject = (
            "<script>"
            "var VN_CAPTURE_MODE = true; "
            "var SCRIPT_DATA = " + json.dumps(script_data, ensure_ascii=False) + ";"
            "</script>"
        )
        html = html.replace("</head>", inject + "\n</head>")
        (temp_dir / "index.html").write_text(html, encoding="utf-8")

        # 複製素材
        self._copy_assets(temp_dir)

    def _copy_assets(self, temp_dir: Path) -> None:
        """複製專案素材到暫存目錄的 assets/ 子目錄。"""
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        project_assets_dir = self._get_project_assets_dir()
        if not project_assets_dir:
            return
        src_assets = project_assets_dir / "assets"
        if not src_assets.exists():
            return

        for category in ("backgrounds", "sprites", "music"):
            for filename in self._project.assets.get(category, []):
                src_file = src_assets / filename
                if src_file.exists():
                    shutil.copy2(src_file, assets_dir / filename)

    def _get_project_assets_dir(self) -> Path | None:
        """取得專案素材所在目錄。"""
        if self._project.project_path:
            return self._project.project_path.parent
        unsaved_dir = Path(tempfile.gettempdir()) / "vnstudio_unsaved"
        if unsaved_dir.exists():
            return unsaved_dir
        return None

    # ── WebEngine 控制 ──

    def _create_offscreen_view(self) -> QWebEngineView:
        """建立固定尺寸的離屏 QWebEngineView。"""
        view = QWebEngineView()
        w, h = self._resolution
        view.setFixedSize(QSize(w, h))
        # WA_DontShowOnScreen：渲染但不顯示在螢幕上
        view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        view.show()  # 必須 show() 才能觸發渲染
        return view

    def _load_and_wait(self, view: QWebEngineView, html_path: Path) -> None:
        """載入 HTML 並同步等待 loadFinished 信號。"""
        loop = QEventLoop()
        load_ok = [False]

        def on_loaded(ok: bool) -> None:
            load_ok[0] = ok
            loop.quit()

        view.loadFinished.connect(on_loaded)
        view.setUrl(QUrl.fromLocalFile(str(html_path)))
        loop.exec()

        if not load_ok[0]:
            raise RuntimeError("WebEngine 載入引擎頁面失敗。")

    def _run_js(self, view: QWebEngineView, script: str):
        """同步執行 JavaScript 並回傳結果。"""
        loop = QEventLoop()
        result = [None]

        def callback(val):
            result[0] = val
            loop.quit()

        view.page().runJavaScript(script, callback)
        loop.exec()
        return result[0]

    def _grab_frame(self, view: QWebEngineView) -> "QPixmap":
        """截取當前 WebEngineView 畫面。"""
        return view.grab()

    @staticmethod
    def _sleep_ms(ms: int) -> None:
        """非阻塞等待指定毫秒，期間處理 Qt 事件。"""
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    # ── 截幀主迴圈 ──

    def _capture_all_frames(
        self,
        view: QWebEngineView,
        temp_dir: Path,
        progress_callback,
        total_dialogues: int,
    ) -> tuple[list[tuple[str, float]], list[tuple[Path, float, float]]]:
        """逐場景、逐對話截幀。

        Returns:
            (concat_entries, audio_timeline)
            concat_entries: [(filename, duration), ...]
            audio_timeline: [(bgm_path, start_time, end_time), ...]
        """
        concat_entries: list[tuple[str, float]] = []
        audio_timeline: list[tuple[Path, float, float]] = []
        frame_idx = 0
        current_time = 0.0
        progress_count = 0

        # 取得場景資訊
        info = self._run_js(view, "VNCaptureAPI.getInfo()")
        if not info:
            raise RuntimeError("無法取得引擎場景資訊，VNCaptureAPI 未初始化。")

        for si, scene in enumerate(self._project.scenes):
            if not scene.dialogues:
                continue

            has_effect = bool(scene.effect)

            # 切換場景（背景 + 特效）
            self._run_js(view, f"VNCaptureAPI.goToScene({si})")

            # 等待場景渲染 + 特效粒子散開
            warmup_ms = 500 if has_effect else 100
            self._sleep_ms(warmup_ms)

            # BGM 時間軸
            bgm_start = current_time
            bgm_path = self._resolve_asset(scene.bgm) if scene.bgm else None

            for di, dlg in enumerate(scene.dialogues):
                # 第一句已由 goToScene 顯示，後續需手動切換
                if di > 0:
                    self._run_js(view, f"VNCaptureAPI.goToDialogue({di})")
                    self._sleep_ms(50)  # 等待 DOM 更新

                duration = _calc_duration(dlg.text)

                if has_effect:
                    # 有特效：按 fps 截多幀（讓粒子動起來）
                    n_frames = max(1, int(duration * self._fps))
                    frame_interval = duration / n_frames
                    interval_ms = max(1, int(1000 / self._fps))

                    for fi in range(n_frames):
                        pixmap = self._grab_frame(view)
                        filename = f"frame_{frame_idx:06d}.png"
                        pixmap.save(str(temp_dir / filename), "PNG")
                        concat_entries.append((filename, frame_interval))
                        frame_idx += 1

                        # 等待下一個動畫幀（讓 requestAnimationFrame 推進特效）
                        if fi < n_frames - 1:
                            self._sleep_ms(interval_ms)
                else:
                    # 無特效：截 1 幀，concat 引用整段 duration
                    self._sleep_ms(50)  # 確保文字渲染完成
                    pixmap = self._grab_frame(view)
                    filename = f"frame_{frame_idx:06d}.png"
                    pixmap.save(str(temp_dir / filename), "PNG")
                    concat_entries.append((filename, duration))
                    frame_idx += 1

                current_time += duration
                progress_count += 1
                if progress_callback:
                    progress_callback(progress_count, total_dialogues)

            # BGM 時間軸結束
            if bgm_path and bgm_path.exists():
                audio_timeline.append((bgm_path, bgm_start, current_time))

        return concat_entries, audio_timeline

    # ── ffmpeg 編碼（與 v1 相同邏輯） ──

    def _write_concat_file(self, path: Path, entries: list[tuple[str, float]]) -> None:
        """寫入 ffmpeg concat demuxer 格式文件。"""
        lines = []
        for filename, duration in entries:
            lines.append(f"file '{filename}'")
            lines.append(f"duration {duration:.4f}")
        if entries:
            lines.append(f"file '{entries[-1][0]}'")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _encode_video(self, concat_path: Path, audio_timeline, temp_dir: Path) -> None:
        """用 ffmpeg 將幀序列 + 音訊編碼為 MP4。"""
        cmd = [
            str(self._ffmpeg),
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
        ]

        audio_path = None
        if audio_timeline:
            audio_path = self._build_audio_track(audio_timeline, temp_dir)
            if audio_path and audio_path.exists():
                cmd.extend(["-i", str(audio_path)])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-r", str(self._fps),
        ])

        if audio_path and audio_path.exists():
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
            ])

        cmd.append(str(self._output_path))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 編碼失敗：\n{result.stderr[-500:]}")

    def _build_audio_track(self, timeline, temp_dir: Path) -> Path | None:
        """將 BGM 時間軸合併為單一音訊檔案。"""
        if not timeline:
            return None
        if len(timeline) == 1:
            return timeline[0][0]

        total_duration = max(end for _, _, end in timeline)
        filter_parts = []
        inputs = []

        for i, (bgm_path, start, end) in enumerate(timeline):
            inputs.extend(["-i", str(bgm_path)])
            duration = end - start
            filter_parts.append(
                f"[{i}:a]atrim=0:{duration:.4f},asetpts=PTS-STARTPTS,"
                f"adelay={int(start * 1000)}|{int(start * 1000)}[a{i}]"
            )

        mix_inputs = "".join(f"[a{i}]" for i in range(len(timeline)))
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(timeline)}:duration=longest[aout]"
        )

        audio_out = temp_dir / "audio_mixed.wav"
        cmd = [str(self._ffmpeg), "-y"]
        cmd.extend(inputs)
        cmd.extend([
            "-filter_complex", ";".join(filter_parts),
            "-map", "[aout]",
            str(audio_out),
        ])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.warning("BGM 混合失敗，將導出無音訊影片：%s", result.stderr[-200:])
            return None
        return audio_out

    def _resolve_asset(self, filename: str | None) -> Path | None:
        """將素材檔名解析為完整路徑。"""
        if not filename:
            return None
        if self._project.project_path:
            path = self._project.project_path.parent / "assets" / filename
            if path.exists():
                return path
        unsaved = Path(tempfile.gettempdir()) / "vnstudio_unsaved" / "assets" / filename
        if unsaved.exists():
            return unsaved
        return None
```

### 3.2 設計說明（給實作者參考）

**為什麼放在 `src/ui/` 而不是 `src/core/`**：此模組依賴 `PyQt6.QtWebEngineWidgets`，屬於 UI 層技術。遵循「UI 和邏輯分離」原則，Qt 相關的程式碼放 `src/ui/`。

**`_sleep_ms()` 的作用**：使用 `QEventLoop` + `QTimer.singleShot` 實現非阻塞等待。等待期間 Qt 事件迴圈繼續運作，`requestAnimationFrame` 能正常觸發，特效粒子才會推進。

**`goToScene` vs `goToDialogue` 分離的原因**：如果每句對話都呼叫 `enterScene()`，會重設特效粒子（`VNEffects.setEffect()` 會先 `stop()` 再重啟）。分開後，同一場景內只切換對話內容，粒子動畫連續不中斷。

**無特效場景的優化**：截 1 幀 + concat 設長 duration，比逐幀截取快 30~90 倍。

---

## 步驟 4：修改 `src/ui/main_window.py` — 改用 v2 導出器

### 4.1 替換 `_VideoExportWorker` 為主執行緒導出

v2 導出器必須在主執行緒運行（QtWebEngine 限制），不能用 QThread。改為在主執行緒直接呼叫，用 `QProgressDialog` 顯示進度。

找到 `_on_export_video` 方法中建立 worker 的區段（第 483-494 行）：

```python
        self._video_worker = _VideoExportWorker(self._project, settings)
        self._video_worker.progress.connect(
            lambda c, t: progress.setValue(int(c / t * 100) if t > 0 else 0)
        )
        self._video_worker.finished.connect(
            lambda: self._on_video_export_done(progress, None)
        )
        self._video_worker.error.connect(
            lambda msg: self._on_video_export_done(progress, msg)
        )
        progress.canceled.connect(self._video_worker.requestInterruption)
        self._video_worker.start()
```

替換為：

```python
        # v2：WebEngine 截幀（主執行緒）
        from src.ui.webengine_capture import WebEngineVideoExporter

        def update_progress(current: int, total: int) -> None:
            if total > 0:
                progress.setValue(int(current / total * 100))
            QApplication.processEvents()

        try:
            exporter = WebEngineVideoExporter(
                self._project,
                settings["output_path"],
                resolution=settings["resolution"],
            )
            exporter.export(progress_callback=update_progress)
            self._on_video_export_done(progress, None)
        except Exception as e:
            self._on_video_export_done(progress, str(e))
```

### 4.2 處理取消按鈕

上面的替換移除了 `progress.canceled` 連接。因為 v2 在主執行緒同步運行，QProgressDialog 的取消按鈕透過 `QApplication.processEvents()` 仍能回應。加入取消檢查：

在 `webengine_capture.py` 的 `_capture_all_frames` 迴圈中（每次截幀後），加入：

```python
                # 檢查是否被取消
                QApplication.processEvents()
```

這行已經透過 `_sleep_ms` 間接呼叫了（QEventLoop.exec 會處理事件），所以不需要額外加。

但為了讓 `progress.wasCanceled()` 能被外部檢查，修改 `update_progress`：

```python
        def update_progress(current: int, total: int) -> None:
            if total > 0:
                progress.setValue(int(current / total * 100))
            QApplication.processEvents()
            if progress.wasCanceled():
                raise InterruptedError("使用者取消導出。")
```

然後在外層 `try/except` 加入 `InterruptedError` 處理：

```python
        try:
            exporter = WebEngineVideoExporter(
                self._project,
                settings["output_path"],
                resolution=settings["resolution"],
            )
            exporter.export(progress_callback=update_progress)
            self._on_video_export_done(progress, None)
        except InterruptedError:
            progress.close()
        except Exception as e:
            self._on_video_export_done(progress, str(e))
```

### 4.3 保留 v1 程式碼

**不要刪除** `_VideoExportWorker` class 和 `src/core/exporter_video.py`。它們作為 fallback 保留。只是不再從 `_on_export_video` 呼叫。

---

## 步驟 5：新增測試 `tests/test_webengine_capture.py`

### 5.1 測試限制

WebEngine 測試需要 `QApplication` 實例和 GUI 環境。在 CI 無頭環境可能無法運行。因此：
- 使用 `pytest.mark.skipif` 標記，當環境無法建立 QApplication 時跳過
- 將純邏輯函式（`_calc_duration`, `_write_concat_file`）抽出來獨立測試（不需要 Qt）

### 5.2 測試檔案內容

```python
"""測試 webengine_capture.py：截幀導出器。"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import Dialogue, Project, Scene


# ── 不需要 Qt 的純邏輯測試 ──

class TestCalcDuration:
    """_calc_duration 與 v1 使用同一公式。"""

    def test_short_text(self):
        from src.ui.webengine_capture import _calc_duration
        assert _calc_duration("短") == 1.5  # 1.0 + 1*0.15 = 1.15 → clamped to 1.5

    def test_medium_text(self):
        from src.ui.webengine_capture import _calc_duration
        d = _calc_duration("十個字的測試文字啊啊")  # 10 chars → 1.0 + 1.5 = 2.5
        assert d == 2.5

    def test_long_text_capped(self):
        from src.ui.webengine_capture import _calc_duration
        d = _calc_duration("字" * 100)  # 1.0 + 15.0 → capped to 8.0
        assert d == 8.0

    def test_empty_text(self):
        from src.ui.webengine_capture import _calc_duration
        assert _calc_duration("") == 1.5


class TestWriteConcatFile:
    def test_basic_format(self, tmp_path):
        from src.ui.webengine_capture import WebEngineVideoExporter

        # 用 mock 建立實例來測試私有方法
        with patch("src.ui.webengine_capture.WebEngineVideoExporter.__init__",
                    lambda self, *a, **kw: None):
            exporter = WebEngineVideoExporter.__new__(WebEngineVideoExporter)

        path = tmp_path / "concat.txt"
        entries = [("frame_000000.png", 2.5), ("frame_000001.png", 1.5)]
        exporter._write_concat_file(path, entries)

        content = path.read_text(encoding="utf-8")
        assert "file 'frame_000000.png'" in content
        assert "duration 2.5000" in content
        assert "file 'frame_000001.png'" in content
        # 最後一行應該是重複的 file 行（ffmpeg concat 規範）
        lines = content.strip().split("\n")
        assert lines[-1] == "file 'frame_000001.png'"

    def test_empty_entries(self, tmp_path):
        from src.ui.webengine_capture import WebEngineVideoExporter

        with patch("src.ui.webengine_capture.WebEngineVideoExporter.__init__",
                    lambda self, *a, **kw: None):
            exporter = WebEngineVideoExporter.__new__(WebEngineVideoExporter)

        path = tmp_path / "concat.txt"
        exporter._write_concat_file(path, [])
        assert path.read_text(encoding="utf-8") == ""


class TestPrepareEngineFiles:
    """測試引擎檔案準備邏輯（注入 SCRIPT_DATA + VN_CAPTURE_MODE）。"""

    def test_html_injection(self, tmp_path):
        from src.ui.webengine_capture import WebEngineVideoExporter, ENGINE_DIR

        project = Project(
            title="測試",
            scenes=[Scene(id="s1", dialogues=[Dialogue(type="narration", text="旁白")])],
        )

        with patch("src.ui.webengine_capture.WebEngineVideoExporter.__init__",
                    lambda self, *a, **kw: None):
            exporter = WebEngineVideoExporter.__new__(WebEngineVideoExporter)
            exporter._project = project
            exporter._resolution = (640, 360)

        exporter._prepare_engine_files(tmp_path)

        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "VN_CAPTURE_MODE = true" in html
        assert "SCRIPT_DATA" in html
        # engine.js 和 effects.js 應該都被複製
        assert (tmp_path / "engine.js").exists()
        assert (tmp_path / "effects.js").exists()
        assert (tmp_path / "style.css").exists()


class TestExportValidation:
    """測試導出前的驗證邏輯。"""

    def test_empty_project_raises(self):
        project = Project(title="空")
        with patch("src.core.ffmpeg_manager.ensure_ffmpeg_or_raise",
                    return_value=Path("ffmpeg")):
            exporter = WebEngineVideoExporter(project, Path("out.mp4"))
            with pytest.raises(ValueError, match="沒有場景"):
                exporter.export()

    def test_no_dialogues_raises(self):
        project = Project(title="空場景", scenes=[Scene(id="s1")])
        with patch("src.core.ffmpeg_manager.ensure_ffmpeg_or_raise",
                    return_value=Path("ffmpeg")):
            exporter = WebEngineVideoExporter(project, Path("out.mp4"))
            with pytest.raises(ValueError, match="沒有對話"):
                exporter.export()
```

### 5.3 執行測試

```bash
# 只跑 v2 導出器測試
pytest tests/test_webengine_capture.py -v

# 確認 v1 測試未被破壞
pytest tests/test_exporter_video.py -v

# 全部測試
pytest tests/ -v
```

---

## 步驟 6：端到端驗證

### 6.1 引擎行為驗證（非 Capture Mode）

```
1. 執行 python main.py
2. 匯入任意 .txt 檔案
3. 在場景屬性設定特效為 "rain"
4. 點擊預覽 → 確認有雨滴粒子（步驟 2 的 effects.js 修復）
5. 確認打字機效果、背景轉場、BGM 播放皆正常
```

### 6.2 影片導出驗證

```
1. 確認已安裝 FFmpeg（resources/ffmpeg/ffmpeg.exe 或系統 PATH）
2. 建立測試專案：
   - 至少 2 個場景
   - 場景 1 設定特效 "rain"
   - 場景 2 設定特效 "snow" 或 null
   - 各場景至少 2 句對話
   - 指定背景圖和角色立繪
3. 導出 → 選擇 1280×720 (HD)
4. 檢查輸出 MP4：
   - [x] 能正常播放
   - [x] 場景 1 有雨滴粒子效果
   - [x] 場景 2 有雪花/無特效（取決於設定）
   - [x] 角色名牌顏色正確
   - [x] 文字使用 Markdown 渲染（若有粗體/斜體）
   - [x] 對話框半透明樣式正確
   - [x] 立繪位置（left/center/right）正確
   - [x] 場景之間有正確切換
5. 導出 → 選擇 1920×1080 (Full HD) 再確認一次
```

### 6.3 效能基準

以 10 句對話、2 個場景（1 個有 rain 特效）、720p、30fps 為基準：
- 預期導出時間：30-120 秒（取決於機器效能）
- 若超過 5 分鐘，檢查 `_sleep_ms` 和 `_grab_frame` 是否有瓶頸

### 6.4 邊界條件測試

```
- 空專案（0 場景）→ 應報錯「沒有場景」
- 場景無對話 → 應報錯「沒有對話」
- 所有場景都無特效 → 應走快速路徑（1 幀/對話）
- 所有場景都有特效 → 應走慢速路徑（N 幀/對話）
- 角色為 null（旁白）→ 不顯示名牌
- 素材檔案不存在 → 使用預設深靛色背景，不 crash
- 使用者按取消 → 中止導出，不殘留暫存檔
```

---

## 已知風險與回退方案

| 風險 | 症狀 | 回退方案 |
|------|------|---------|
| `WA_DontShowOnScreen` 在某些 GPU 驅動下 `grab()` 回傳空白 | 輸出 MP4 全黑 | 改用 `view.move(-10000, -10000)` 移到螢幕外 |
| QEventLoop 嵌套導致事件處理異常 | GUI 凍結或 crash | 改用 QTimer 驅動狀態機（參見備註） |
| 首幀特效粒子不足 | 第一句對話畫面特效稀疏 | 增加 warmup_ms（從 500 改為 1000） |
| 記憶體不足（4K + 30fps） | OOM crash | 在 4K 時降低到 15fps 或只截關鍵幀 |

### QTimer 狀態機備選方案（如果 QEventLoop 有問題）

如果嵌套 QEventLoop 導致問題，改為 QTimer 驅動：
- 將 `export()` 改為非同步（回傳 None，透過 signal 通知完成）
- 用 `QTimer.singleShot(interval, self._capture_next_step)` 逐步推進
- 每一步：設定對話 → 截幀 → 排程下一步
- 完成後 emit `finished` signal

這會大幅改變 API 設計，建議先嘗試 QEventLoop 方案。
