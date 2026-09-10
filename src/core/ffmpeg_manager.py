"""FFmpeg 自動偵測與下載管理。"""

from __future__ import annotations

import logging
import platform
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

logger = logging.getLogger(__name__)

# BtbN 維護的靜態 FFmpeg builds
_DOWNLOAD_URLS = {
    "Windows": (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
        "latest/ffmpeg-master-latest-win64-gpl.zip"
    ),
}


def _get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent


def _get_install_dir() -> Path:
    return _get_base_path() / "resources" / "ffmpeg"


def find_ffmpeg() -> Path | None:
    """搜尋 ffmpeg，依序：resources/ffmpeg/ → 系統 PATH。找不到回傳 None。"""
    bundled = _get_install_dir() / "ffmpeg.exe"
    if bundled.exists():
        return bundled
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)
    return None


def is_available() -> bool:
    """快速檢查 ffmpeg 是否可用。"""
    return find_ffmpeg() is not None


def download_ffmpeg(progress_callback=None) -> Path:
    """下載 FFmpeg 並解壓到 resources/ffmpeg/，回傳 ffmpeg.exe 路徑。

    progress_callback(downloaded_bytes, total_bytes) 用於更新進度。
    total_bytes 可能為 -1（伺服器未提供 Content-Length）。
    """
    os_name = platform.system()
    url = _DOWNLOAD_URLS.get(os_name)
    if not url:
        raise RuntimeError(f"不支援自動下載 FFmpeg：{os_name}。請手動安裝。")

    install_dir = _get_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    zip_path = install_dir / "_ffmpeg_download.zip"

    def _reporthook(block_num, block_size, total_size):
        if progress_callback:
            downloaded = block_num * block_size
            progress_callback(downloaded, total_size)

    try:
        logger.info("開始下載 FFmpeg: %s", url)
        urlretrieve(url, str(zip_path), reporthook=_reporthook)
    except (URLError, OSError) as e:
        zip_path.unlink(missing_ok=True)
        raise RuntimeError(f"下載 FFmpeg 失敗：{e}") from e

    # 從 ZIP 中找到 ffmpeg.exe 並解壓
    target = install_dir / "ffmpeg.exe"
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # ZIP 內結構通常是 ffmpeg-master-.../bin/ffmpeg.exe
            ffmpeg_entry = None
            for name in zf.namelist():
                if name.endswith("bin/ffmpeg.exe"):
                    ffmpeg_entry = name
                    break
            if not ffmpeg_entry:
                raise RuntimeError("ZIP 中找不到 ffmpeg.exe")

            with zf.open(ffmpeg_entry) as src, open(target, "wb") as dst:
                dst.write(src.read())
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"FFmpeg ZIP 檔案損壞：{e}") from e
    finally:
        zip_path.unlink(missing_ok=True)

    logger.info("FFmpeg 已安裝至 %s", target)
    return target


def ensure_ffmpeg_or_raise() -> Path:
    """回傳 ffmpeg 路徑，找不到則 raise FileNotFoundError。

    此函式不會觸發下載，適合在非 GUI 環境使用。
    """
    path = find_ffmpeg()
    if path:
        return path
    raise FileNotFoundError(
        "找不到 ffmpeg。請將 ffmpeg.exe 放入 resources/ffmpeg/ 或加入系統 PATH。"
    )
