"""VisualNovel Studio v1.0.0 應用程式入口。"""

import logging
import logging.handlers
import sys
from pathlib import Path

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.theme import apply_theme, load_preference

__version__ = "1.0.0"

logger = logging.getLogger(__name__)


def get_base_path() -> Path:
    """取得應用程式根目錄（支援 PyInstaller 打包模式）。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def setup_logging() -> None:
    """設定 RotatingFileHandler + StreamHandler。"""
    log_dir = Path.home() / ".vnstudio" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "vnstudio.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            ),
            logging.StreamHandler(),
        ],
    )

    def exception_handler(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("未捕捉的例外", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = exception_handler
    logger.info("VisualNovel Studio v%s 啟動", __version__)


def load_bundled_fonts() -> None:
    """載入 assets/fonts/ 內的 Noto Sans TC 字型；缺檔不致命，僅 warning。"""
    fonts_dir = get_base_path() / "assets" / "fonts"
    if not fonts_dir.is_dir():
        logger.warning("字型資料夾不存在：%s（將回退至系統字型）", fonts_dir)
        return
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(ttf)) < 0:
            logger.warning("字型載入失敗：%s", ttf.name)


def main():
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("VisualNovel Studio")
    app.setApplicationVersion(__version__)

    load_bundled_fonts()

    # 載入並套用主題偏好
    theme_name, font_size = load_preference()
    apply_theme(app, theme_name, font_size)

    window = MainWindow()
    window.show()
    logger.info("主視窗已顯示")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
