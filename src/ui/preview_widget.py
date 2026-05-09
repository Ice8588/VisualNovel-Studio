"""預覽元件：QtWebEngine 即時預覽，含 16:9 Letterbox。"""

import json
import shutil
import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.core.models import Project
from src.ui import palette

ENGINE_DIR = Path(__file__).parent.parent / "engine"

_TARGET_RATIO = 16 / 9
_QRC_WEBCHANNEL = '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'


class PreviewBridge(QObject):
    """Python←JS 橋接：Preview 推進文字時通知 Python 端。"""

    dialogue_advanced = pyqtSignal(int, int)  # (scene_index, dialogue_index)
    stage_slot_clicked = pyqtSignal(int, int, str, str)  # (scene_idx, dlg_idx, position, action)

    @pyqtSlot(int, int)
    def on_dialogue_shown(self, scene_index: int, dialogue_index: int) -> None:
        self.dialogue_advanced.emit(scene_index, dialogue_index)

    @pyqtSlot(int, int, str, str)
    def on_stage_slot_clicked(self, scene_idx: int, dlg_idx: int, position: str, action: str) -> None:
        self.stage_slot_clicked.emit(scene_idx, dlg_idx, position, action)


class _LoggingPage(QWebEnginePage):
    """將 JS console.log / warning / error 轉至 Python stderr，方便除錯。"""

    _LEVEL_NAMES = {
        QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
        QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARN",
        QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR",
    }

    def javaScriptConsoleMessage(self, level, message, line, source):
        import sys
        name = self._LEVEL_NAMES.get(level, "LOG")
        src = source.rsplit("/", 1)[-1] if source else "?"
        print(f"[WebEngine {name}] {src}:{line} {message}", file=sys.stderr)


class LetterboxContainer(QWidget):
    """將 WebView 以 16:9 等比居中顯示，四周填黑邊。"""

    def __init__(self, web_view: QWebEngineView, parent: QWidget | None = None):
        super().__init__(parent)
        self._web_view = web_view
        self._web_view.setParent(self)
        # 預覽四周邊框跟主題（深色保留接近黑、淺色用 surface 不破視覺）
        palette.register_themed(
            self,
            lambda p: f"background-color: {p.bg.name()};",
        )

    def resizeEvent(self, event) -> None:
        self._refit()
        super().resizeEvent(event)

    def _refit(self) -> None:
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        if w / h > _TARGET_RATIO:
            # 容器較寬 → 以高度為準，左右黑邊
            new_h = h
            new_w = int(h * _TARGET_RATIO)
            x = (w - new_w) // 2
            y = 0
        else:
            # 容器較窄 → 以寬度為準，上下黑邊
            new_w = w
            new_h = int(w / _TARGET_RATIO)
            x = 0
            y = (h - new_h) // 2
        self._web_view.setGeometry(x, y, new_w, new_h)


class PreviewWidget(QWidget):
    """QtWebEngine 預覽元件，可內嵌於任何佈局。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._temp_dir: tempfile.TemporaryDirectory | None = None
        self._theme_name: str = "dark"  # 影響 body class（preview-{theme_name}）
        self._last_project: Project | None = None
        self._setup_ui()

    # 已知主題 key；engine.css 目前只實作 preview-dark / preview-light，
    # 其他 key 會注入對應 body class 但 css 沒對應規則時 no-op（待設計補完）
    _KNOWN_THEMES = ("dark", "light", "parchment", "midnight", "figma-dark", "ivory")

    def set_theme(self, theme_name: str) -> None:
        """設定預覽主題，若已載入 project 會觸發重繪。"""
        if theme_name not in self._KNOWN_THEMES:
            theme_name = "dark"
        if theme_name == self._theme_name:
            return
        self._theme_name = theme_name
        if self._last_project is not None:
            self.reload_preview(self._last_project)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.setPage(_LoggingPage(self.web_view))
        self.web_view.setHtml(self._placeholder_html())

        # QWebChannel：Python←JS 雙向通訊
        self.bridge = PreviewBridge()
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self.bridge)
        self.web_view.page().setWebChannel(self._channel)

        self.letterbox = LetterboxContainer(self.web_view)
        layout.addWidget(self.letterbox)

        self.setLayout(layout)

    def reload_preview(self, project: Project) -> None:
        """將 engine 檔案 + script data + assets 寫入暫存目錄並載入預覽。"""
        self._last_project = project
        # 清理前一次的暫存目錄
        if self._temp_dir:
            self._temp_dir.cleanup()
        self._temp_dir = tempfile.TemporaryDirectory(prefix="vnstudio_preview_")
        temp_path = Path(self._temp_dir.name)

        # 產生 script 資料
        script_data = project.to_script_json()

        # 寫入 script.json
        (temp_path / "script.json").write_text(
            json.dumps(script_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 複製 engine 檔案
        for filename in ("engine.js", "effects.js", "style.css"):
            src = ENGINE_DIR / filename
            if src.exists():
                (temp_path / filename).write_text(
                    src.read_text(encoding="utf-8"), encoding="utf-8"
                )

        # 複製 index.html 並注入 SCRIPT_DATA（解決 file:// fetch 限制）+ preview 主題 class
        index_src = ENGINE_DIR / "index.html"
        if index_src.exists():
            html = index_src.read_text(encoding="utf-8")
            inline_script = (
                "<script>var SCRIPT_DATA = "
                + json.dumps(script_data, ensure_ascii=False)
                + ";</script>"
            )
            html = html.replace("</head>", inline_script + "\n</head>")
            # B4：注入 preview-dark / preview-light class 到 <body>
            preview_class = f"preview-{self._theme_name}"
            html = html.replace("<body>", f'<body class="{preview_class}">')
            (temp_path / "index.html").write_text(html, encoding="utf-8")

        # 複製素材
        self._copy_assets(project, temp_path)

        # 載入 index.html
        index_path = temp_path / "index.html"
        if index_path.exists():
            self.web_view.setUrl(QUrl.fromLocalFile(str(index_path)))
        else:
            self.web_view.setHtml(self._placeholder_html())

    def _copy_assets(self, project: Project, temp_path: Path) -> None:
        """複製專案素材到暫存目錄的 assets/ 子目錄。"""
        assets_dir = temp_path / "assets"
        assets_dir.mkdir(exist_ok=True)

        project_assets_dir = self._get_project_assets_dir(project)
        if not project_assets_dir:
            return

        src_assets = project_assets_dir / "assets"
        if not src_assets.exists():
            return

        for category in ("backgrounds", "sprites", "music"):
            for filename in project.assets.get(category, []):
                src_file = src_assets / filename
                if src_file.exists():
                    shutil.copy2(src_file, assets_dir / filename)

        # 複製角色立繪（可能未列入 project.assets["sprites"]）
        for char in project.characters:
            for sv in char.sprites:
                if sv.filename:
                    dest = assets_dir / sv.filename
                    if not dest.exists():
                        src_file = src_assets / sv.filename
                        if src_file.exists():
                            shutil.copy2(src_file, dest)

    @staticmethod
    def _get_project_assets_dir(project: Project) -> Path | None:
        """取得專案素材所在目錄。"""
        if project.project_path:
            return project.project_path.parent
        unsaved_dir = Path(tempfile.gettempdir()) / "vnstudio_unsaved"
        if unsaved_dir.exists():
            return unsaved_dir
        return None

    @staticmethod
    def _placeholder_html() -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="display:flex;align-items:center;justify-content:center;
                     height:100vh;margin:0;background:#2a2a3e;color:#aaa;
                     font-family:sans-serif;">
            <div style="text-align:center;">
                <p style="font-size:24px;">VisualNovel Studio</p>
                <p>匯入文字並新增場景後，預覽將在此顯示</p>
            </div>
        </body>
        </html>
        """

    def jump_to_dialogue(self, scene_index: int, dialogue_index: int) -> None:
        """透過 VNPreviewAPI 跳轉到指定場景與台詞。"""
        js = (
            f"if(window.VNPreviewAPI){{"
            f"VNPreviewAPI.goToScene({scene_index});"
            f"VNPreviewAPI.goToDialogue({dialogue_index});"
            f"}}"
        )
        self.web_view.page().runJavaScript(js)

    def cleanup(self) -> None:
        """清理暫存目錄。"""
        if self._temp_dir:
            self._temp_dir.cleanup()
            self._temp_dir = None
