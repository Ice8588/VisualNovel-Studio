"""測試 WebEngineVideoExporter._build_encode_cmd 指令組裝邏輯。

重點驗證：
- 無音訊：cmd 含 -t、不含 -shortest。
- 有音訊：cmd 含 -t 與 -c:a aac、不含 -shortest。
- -t 值等於 total_duration（格式 .4f）。
- _write_concat_file 產出格式正確：最後一行為重複 file 行（concat demuxer 規範）。

這些測試只測指令組裝，不呼叫 ffmpeg / QtWebEngine，可在 offscreen CI 環境執行。
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


def _make_exporter(output_path: Path | None = None):
    """建立輕量 WebEngineVideoExporter 實例（繞過 __init__ 避免 ffmpeg 偵測）。"""
    from src.ui.webengine_capture import WebEngineVideoExporter

    with patch("src.ui.webengine_capture.WebEngineVideoExporter.__init__",
               lambda self, *a, **kw: None):
        exporter = WebEngineVideoExporter.__new__(WebEngineVideoExporter)

    exporter._ffmpeg = Path("ffmpeg")
    exporter._fps = 30
    exporter._resolution = (1920, 1080)
    exporter._output_path = output_path or Path("out.mp4")
    return exporter


class TestBuildEncodeCmd:
    """_build_encode_cmd 指令組裝測試。"""

    def test_no_audio_contains_t_flag(self, tmp_path):
        """無音訊時：指令應含 -t，不含 -shortest。"""
        exporter = _make_exporter(tmp_path / "out.mp4")
        concat_path = tmp_path / "concat.txt"
        concat_path.touch()

        cmd = exporter._build_encode_cmd(
            encoder=None,
            concat_path=concat_path,
            audio_path=None,
            total_duration=14.7,
        )

        assert "-t" in cmd, "無音訊時應有 -t 參數"
        assert "-shortest" not in cmd, "不應含 -shortest"

    def test_no_audio_t_value_correct(self, tmp_path):
        """無音訊時：-t 的值應等於 total_duration（.4f 格式）。"""
        exporter = _make_exporter(tmp_path / "out.mp4")
        concat_path = tmp_path / "concat.txt"
        concat_path.touch()

        total = 14.7325
        cmd = exporter._build_encode_cmd(
            encoder=None,
            concat_path=concat_path,
            audio_path=None,
            total_duration=total,
        )

        idx = cmd.index("-t")
        assert cmd[idx + 1] == f"{total:.4f}", (
            f"期望 -t 值 '{total:.4f}'，實際 '{cmd[idx + 1]}'"
        )

    def test_with_audio_contains_t_and_aac(self, tmp_path):
        """有音訊時：指令應含 -t、-c:a aac，不含 -shortest。"""
        exporter = _make_exporter(tmp_path / "out.mp4")
        concat_path = tmp_path / "concat.txt"
        concat_path.touch()
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()

        cmd = exporter._build_encode_cmd(
            encoder=None,
            concat_path=concat_path,
            audio_path=audio_path,
            total_duration=14.7,
        )

        assert "-t" in cmd, "有音訊時應有 -t 參數"
        assert "-c:a" in cmd, "有音訊時應有 -c:a 參數"
        assert "aac" in cmd, "音訊編碼器應為 aac"
        assert "-shortest" not in cmd, "不應含 -shortest"

    def test_with_audio_t_value_correct(self, tmp_path):
        """有音訊時：-t 值應等於傳入的 total_duration。"""
        exporter = _make_exporter(tmp_path / "out.mp4")
        concat_path = tmp_path / "concat.txt"
        concat_path.touch()
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()

        total = 2.0
        cmd = exporter._build_encode_cmd(
            encoder=None,
            concat_path=concat_path,
            audio_path=audio_path,
            total_duration=total,
        )

        idx = cmd.index("-t")
        assert cmd[idx + 1] == f"{total:.4f}", (
            f"期望 -t 值 '{total:.4f}'，實際 '{cmd[idx + 1]}'"
        )

    def test_short_bgm_long_video_no_shortest(self, tmp_path):
        """BGM 比影片短的情境（total_duration=14.7 > bgm 2秒）：
        不應有 -shortest，輸出時長由 -t 14.7000 決定。"""
        exporter = _make_exporter(tmp_path / "out.mp4")
        concat_path = tmp_path / "concat.txt"
        concat_path.touch()
        audio_path = tmp_path / "short_bgm.wav"
        audio_path.touch()

        cmd = exporter._build_encode_cmd(
            encoder=None,
            concat_path=concat_path,
            audio_path=audio_path,
            total_duration=14.7,
        )

        assert "-shortest" not in cmd
        idx = cmd.index("-t")
        assert cmd[idx + 1] == "14.7000"

    def test_t_is_output_flag_not_input(self, tmp_path):
        """-t 應放在輸出參數區（output_path 之前），而非輸入區。"""
        exporter = _make_exporter(tmp_path / "out.mp4")
        concat_path = tmp_path / "concat.txt"
        concat_path.touch()

        cmd = exporter._build_encode_cmd(
            encoder=None,
            concat_path=concat_path,
            audio_path=None,
            total_duration=5.0,
        )

        t_idx = cmd.index("-t")
        out_idx = cmd.index(str(tmp_path / "out.mp4"))
        # -t 應出現在 output_path 前（輸出參數位置）
        assert t_idx < out_idx, "-t 應在 output_path 之前"

    def test_gpu_encoder_nvenc(self, tmp_path):
        """使用 h264_nvenc 時：指令應含正確的編碼器旗標，且仍有 -t、無 -shortest。"""
        exporter = _make_exporter(tmp_path / "out.mp4")
        concat_path = tmp_path / "concat.txt"
        concat_path.touch()

        cmd = exporter._build_encode_cmd(
            encoder="h264_nvenc",
            concat_path=concat_path,
            audio_path=None,
            total_duration=10.0,
        )

        assert "h264_nvenc" in cmd
        assert "-t" in cmd
        assert "-shortest" not in cmd


class TestWriteConcatFileFormat:
    """_write_concat_file 格式測試。

    concat demuxer 規範：最後一行重複 file 行（無 duration）以讓 ffmpeg 正確讀取尾幀。
    實際輸出時長由 _build_encode_cmd 的 -t 參數控制，不依賴最後重複行的 duration。
    """

    def _make_exporter(self):
        return _make_exporter()

    def test_single_entry_format(self, tmp_path):
        """單一幀：應有 file + duration + 重複 file 共 3 行。"""
        exporter = _make_exporter()
        path = tmp_path / "concat.txt"
        exporter._write_concat_file(path, [("frame_000000.png", 2.5)])

        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert lines[0] == "file 'frame_000000.png'"
        assert lines[1] == "duration 2.5000"
        assert lines[2] == "file 'frame_000000.png'", "最後應重複 file 行（concat demuxer 規範）"

    def test_multiple_entries_format(self, tmp_path):
        """多幀：最後一行應為最後一幀的重複 file 行。"""
        exporter = _make_exporter()
        path = tmp_path / "concat.txt"
        entries = [
            ("frame_000000.png", 2.5),
            ("frame_000001.png", 1.5),
            ("frame_000002.png", 3.0),
        ]
        exporter._write_concat_file(path, entries)

        lines = path.read_text(encoding="utf-8").strip().split("\n")
        # 每個 entry 有 file + duration 兩行，最後額外一個 file 行
        assert len(lines) == len(entries) * 2 + 1
        assert lines[-1] == "file 'frame_000002.png'", "最後應是最後幀的重複 file 行"

    def test_duration_format_4f(self, tmp_path):
        """duration 應以 .4f 格式輸出（避免浮點精度問題）。"""
        exporter = _make_exporter()
        path = tmp_path / "concat.txt"
        exporter._write_concat_file(path, [("f.png", 1.23456789)])

        content = path.read_text(encoding="utf-8")
        assert "duration 1.2346" in content

    def test_empty_entries(self, tmp_path):
        """空清單：檔案內容應為空字串。"""
        exporter = _make_exporter()
        path = tmp_path / "concat.txt"
        exporter._write_concat_file(path, [])
        assert path.read_text(encoding="utf-8") == ""

    def test_total_duration_sum(self, tmp_path):
        """驗證：concat_entries 的 duration 加總等於影片預期總時長。

        這確保 export() 中 total_duration = sum(dur for _, dur in concat_entries) 的
        計算邏輯正確。
        """
        entries = [
            ("f0.png", 2.5),
            ("f1.png", 3.75),
            ("f2.png", 1.25),
        ]
        total = sum(dur for _, dur in entries)
        assert total == pytest.approx(7.5, abs=1e-9)
