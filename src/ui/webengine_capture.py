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
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

from src.core.exporter_video import calc_auto_duration
from src.core.models import Project

logger = logging.getLogger(__name__)

ENGINE_DIR = Path(__file__).parent.parent / "engine"

# Module-level GPU encoder 快取（False = 尚未偵測，None = 無可用 GPU）
_GPU_ENCODER_CACHE: str | None | bool = False


def _detect_gpu_encoder(ffmpeg_path: Path) -> str | None:
    """偵測可用的 GPU 硬體編碼器。回傳編碼器名稱或 None。"""
    try:
        result = subprocess.run(
            [str(ffmpeg_path), "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        # 優先順序：NVENC (NVIDIA) > AMF (AMD) > QSV (Intel)
        for encoder in ("h264_nvenc", "h264_amf", "h264_qsv"):
            if encoder in output:
                # 驗證編碼器是否真的可用（nullsrc 測試渲染）
                test = subprocess.run(
                    [str(ffmpeg_path), "-hide_banner", "-f", "lavfi",
                     "-i", "nullsrc=s=256x256:d=1", "-c:v", encoder,
                     "-f", "null", "-"],
                    capture_output=True, text=True, timeout=15
                )
                if test.returncode == 0:
                    return encoder
    except Exception:
        pass
    return None


def _get_gpu_encoder(ffmpeg_path: Path) -> str | None:
    """取得 GPU 編碼器（快取偵測結果，避免每次導出重新偵測）。"""
    global _GPU_ENCODER_CACHE
    if _GPU_ENCODER_CACHE is False:
        _GPU_ENCODER_CACHE = _detect_gpu_encoder(ffmpeg_path)
    return _GPU_ENCODER_CACHE  # type: ignore[return-value]


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

            # 4. 輪詢等待 VNCaptureAPI 初始化（取代固定 sleep）
            self._wait_for_capture_api(view)

            # 5. 逐場景、逐對話截幀
            concat_entries, audio_timeline = self._capture_all_frames(
                view, temp_dir, progress_callback, total_dialogues
            )

            # 6. 計算影片總時長（所有對話 duration 加總）
            total_duration = sum(dur for _, dur in concat_entries)

            # 7. 寫入 concat 文件
            concat_path = temp_dir / "concat.txt"
            self._write_concat_file(concat_path, concat_entries)

            # 8. ffmpeg 編碼
            self._encode_video(concat_path, audio_timeline, temp_dir, total_duration)

        finally:
            if view is not None:
                # 先導航到空白頁，釋放對 temp_dir 檔案的鎖定
                view.page().setUrl(QUrl("about:blank"))
                QApplication.processEvents()
                self._sleep_ms(200)
                view.close()
                view.deleteLater()
                # 多次處理事件確保 deleteLater 完成
                for _ in range(5):
                    QApplication.processEvents()
                    self._sleep_ms(50)
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

        # 複製角色立繪（可能未列入 project.assets["sprites"]）
        for char in self._project.characters:
            for sv in char.sprites:
                if sv.filename:
                    dest = assets_dir / sv.filename
                    if not dest.exists():
                        src_file = src_assets / sv.filename
                        if src_file.exists():
                            shutil.copy2(src_file, dest)

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
        # 明確設定字體大小，防止 QFont::setPointSize <= 0 錯誤
        font = QFont()
        font.setPointSize(max(12, font.pointSize() if font.pointSize() > 0 else 12))
        view.setFont(font)
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

    def _wait_for_images_loaded(self, view: QWebEngineView, timeout_ms: int = 800) -> None:
        """輪詢直到所有 <img> 都 complete=True，避免截到 opacity-0 / 半載入的立繪。

        Phase 4 修 #4：renderStageSlot 在新 src 時走 opacity 0 → onload → 1 的 dance；
        若截幀時機落在 onload 之前，會抓到「沒立繪」的幀，於 MP4 看起來像閃爍。
        此 poll 確保截幀時所有 image 都已完成載入。
        """
        interval = 20
        elapsed = 0
        js = "Array.from(document.images).every(function(img){return img.complete;})"
        while elapsed < timeout_ms:
            if self._run_js(view, js):
                return
            self._sleep_ms(interval)
            elapsed += interval
        # 逾時：不擲例外，盡力輸出當前狀態
        logger.warning("等待 images.complete 逾時（%dms）；可能截到未完全載入的立繪。", timeout_ms)

    def _wait_for_capture_api(self, view: QWebEngineView, timeout_ms: int = 8000) -> None:
        """輪詢直到 VNCaptureAPI 初始化完成，或逾時拋出例外。"""
        interval = 100
        elapsed = 0
        while elapsed < timeout_ms:
            ready = self._run_js(view, "typeof window.VNCaptureAPI !== 'undefined'")
            if ready:
                return
            self._sleep_ms(interval)
            elapsed += interval
        # 逾時：嘗試取得 JS 錯誤訊息輔助診斷
        raise RuntimeError(
            "VNCaptureAPI 初始化逾時（超過 8 秒）。\n"
            "可能原因：index.html 缺少必要的 DOM 元素，或 engine.js 載入失敗。"
        )

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

            # Phase 2：scene-wide effect 已改為 effect_tracks；這裡僅用於 warm-up 時長判斷。
            # Phase 3 會把 engine.js 改為真正依 EffectSegment 生效。
            has_effect = any(t.segments for t in scene.effect_tracks)

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
                    self._sleep_ms(100)  # 等待 DOM 完全穩定

                # Phase 4 修 #4：截第一幀前，先確保所有 <img> 載完，避免 opacity 0 閃爍
                self._wait_for_images_loaded(view)

                duration = calc_auto_duration(dlg.text)

                if has_effect:
                    # 有特效：按 fps 截多幀（讓粒子動起來、screen_shake/text shake 顯示）
                    n_frames = max(1, int(duration * self._fps))
                    frame_interval = duration / n_frames
                    interval_ms = max(1, int(1000 / self._fps))

                    for fi in range(n_frames):
                        pixmap = self._grab_frame(view)
                        filename = f"frame_{frame_idx:06d}.png"
                        pixmap.save(str(temp_dir / filename), "PNG")
                        concat_entries.append((filename, frame_interval))
                        frame_idx += 1

                        # 等待下一個動畫幀（讓 requestAnimationFrame / CSS animation 推進）
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

    def _build_encode_cmd(
        self,
        encoder: str | None,
        concat_path: Path,
        audio_path: Path | None,
        total_duration: float,
    ) -> list[str]:
        """組裝 ffmpeg 編碼指令。

        使用 ``-t {total_duration}`` 精確控制輸出長度，不使用 ``-shortest``：
        - BGM 比內容短時：影片維持完整長度，BGM 播完後無聲（不循環，保守行為）。
        - BGM 比內容長時：在 total_duration 處切斷。
        - 無 BGM 時：精確剪裁，消除 concat demuxer 最後一幀重複可能帶來的誤差。

        Args:
            encoder: GPU 編碼器名稱，或 None 表示使用 libx264 CPU 編碼。
            concat_path: ffmpeg concat demuxer 清單檔路徑。
            audio_path: 混合後的音訊檔路徑，無音訊時為 None。
            total_duration: 影片目標總時長（秒）。
        """
        cmd = [
            str(self._ffmpeg), "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_path),
        ]
        if audio_path and audio_path.exists():
            cmd.extend(["-i", str(audio_path)])

        if encoder == "h264_nvenc":
            cmd.extend(["-c:v", "h264_nvenc", "-preset", "p4",
                         "-rc:v", "vbr", "-cq:v", "19", "-b:v", "0"])
        elif encoder == "h264_amf":
            cmd.extend(["-c:v", "h264_amf", "-quality", "balanced",
                         "-rc", "cqp", "-qp_i", "20"])
        elif encoder == "h264_qsv":
            cmd.extend(["-c:v", "h264_qsv", "-preset", "medium",
                         "-global_quality", "20"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23"])

        cmd.extend(["-pix_fmt", "yuv420p", "-r", str(self._fps)])

        if audio_path and audio_path.exists():
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        # -t 一律加在輸出前：精確控制影片時長
        # BGM 不足時補靜音（ffmpeg 預設行為），不強制 -shortest 截斷
        cmd.extend(["-t", f"{total_duration:.4f}"])
        cmd.append(str(self._output_path))
        return cmd

    def _encode_video(
        self, concat_path: Path, audio_timeline, temp_dir: Path, total_duration: float
    ) -> None:
        """用 ffmpeg 將幀序列 + 音訊編碼為 MP4。支援 GPU 加速，自動回退到 CPU。"""
        gpu_encoder = _get_gpu_encoder(self._ffmpeg)

        audio_path = None
        if audio_timeline:
            audio_path = self._build_audio_track(audio_timeline, temp_dir)

        if gpu_encoder:
            logger.info("使用 GPU 編碼器：%s", gpu_encoder)
            result = subprocess.run(
                self._build_encode_cmd(gpu_encoder, concat_path, audio_path, total_duration),
                capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                logger.warning("GPU 編碼失敗，回退到 CPU：%s", result.stderr[-200:])
                result = subprocess.run(
                    self._build_encode_cmd(None, concat_path, audio_path, total_duration),
                    capture_output=True, text=True, timeout=600
                )
        else:
            logger.info("使用 CPU 編碼器：libx264")
            result = subprocess.run(
                self._build_encode_cmd(None, concat_path, audio_path, total_duration),
                capture_output=True, text=True, timeout=600
            )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 編碼失敗：\n{result.stderr[-500:]}")

    def _build_audio_track(self, timeline, temp_dir: Path) -> Path | None:
        """將 BGM 時間軸合併為單一音訊檔案。"""
        if not timeline:
            return None
        if len(timeline) == 1 and timeline[0][1] == 0:
            # 單一 BGM 且從影片開頭（start==0）播放：直接回傳原始路徑，
            # 不做任何裁剪或延遲處理。輸出長度由 _build_encode_cmd 以 -t 控制：
            #   - BGM 比影片短時，ffmpeg 自動補靜音至 -t 指定時長（不循環）；
            #   - BGM 比影片長時，在 -t 處截斷。
            # start≠0 的情況（第一個場景無 BGM）落入下方 filter_complex 路徑，
            # 由 atrim+adelay 在正確時間點插入 BGM。
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
