"""預覽元件：QtWebEngine 即時預覽，從 right_panel.py 提取。"""

import json
import shutil
import tempfile
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.core.models import Project

ENGINE_DIR = Path(__file__).parent.parent / "engine"


class PreviewWidget(QWidget):
    """QtWebEngine 預覽元件，可內嵌於任何佈局。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._temp_dir: tempfile.TemporaryDirectory | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.setHtml(self._placeholder_html())
        layout.addWidget(self.web_view)

        self.setLayout(layout)

    def reload_preview(self, project: Project) -> None:
        """將 engine 檔案 + script data + assets 寫入暫存目錄並載入預覽。"""
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

        # 複製 index.html 並注入 SCRIPT_DATA（解決 file:// fetch 限制）
        index_src = ENGINE_DIR / "index.html"
        if index_src.exists():
            html = index_src.read_text(encoding="utf-8")
            inline_script = (
                "<script>var SCRIPT_DATA = "
                + json.dumps(script_data, ensure_ascii=False)
                + ";</script>"
            )
            html = html.replace("</head>", inline_script + "\n</head>")
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
