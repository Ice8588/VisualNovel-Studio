"""導出功能：將專案打包為可獨立運行的 ZIP 檔案。"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

from src.core.asset_manager import get_project_assets_dir
from src.core.models import Project


def _get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent


ENGINE_DIR = _get_base_path() / "src" / "engine"

_README_TXT = """\
=== VisualNovel Studio 導出說明 ===

請先解壓縮此 ZIP 檔案，再用瀏覽器開啟 index.html。
請勿直接在 ZIP 內開啟 index.html，否則可能無法正常運作。

若使用 Chrome 或 Edge，建議以本機伺服器開啟（如 VS Code Live Server）。
"""


def export_zip(project: Project, output_path: Path) -> None:
    """打包 index.html（內嵌 CSS）+ engine.js + data.js + assets/ 為 ZIP。

    使用 data.js（var SCRIPT_DATA = ...）取代 script.json，
    避免 file:// 協定下的 CORS fetch 限制。
    """
    output_path = Path(output_path)

    # 驗證 engine 檔案存在
    required_files = ["index.html", "engine.js", "style.css"]
    for filename in required_files:
        if not (ENGINE_DIR / filename).exists():
            raise FileNotFoundError(f"缺少引擎檔案：{ENGINE_DIR / filename}")

    # 讀取 engine 檔案
    index_html = (ENGINE_DIR / "index.html").read_text(encoding="utf-8")
    engine_js = (ENGINE_DIR / "engine.js").read_text(encoding="utf-8")
    style_css = (ENGINE_DIR / "style.css").read_text(encoding="utf-8")

    # 移除 qrc:// QWebChannel 腳本（僅在 PyQt6 WebEngine 預覽環境有效，瀏覽器不可用）
    index_html = index_html.replace(
        '  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>\n', ""
    )

    # 將 CSS 內嵌至 index.html（取代 <link> 標籤）
    index_html = index_html.replace(
        '<link rel="stylesheet" href="style.css">',
        f"<style>\n{style_css}\n</style>",
    )

    # 產生 data.js（取代 script.json）
    script_data = project.to_script_json()
    data_js = "var SCRIPT_DATA = " + json.dumps(
        script_data, ensure_ascii=False, indent=2
    ) + ";"

    # 注入 data.js 引用到 index.html
    index_html = index_html.replace(
        "</head>", '<script src="data.js"></script>\n</head>'
    )

    # 若有 effects.js，一併包含
    effects_js = None
    effects_path = ENGINE_DIR / "effects.js"
    if effects_path.exists():
        effects_js = effects_path.read_text(encoding="utf-8")

    # 找出素材來源目錄
    assets_source = get_project_assets_dir(project)

    # 寫入 ZIP
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", index_html)
        zf.writestr("engine.js", engine_js)
        zf.writestr("data.js", data_js)
        zf.writestr("README.txt", _README_TXT)

        if effects_js:
            zf.writestr("effects.js", effects_js)

        # 打包素材
        if assets_source:
            for category in ("backgrounds", "sprites", "music"):
                for filename in project.assets.get(category, []):
                    src_file = assets_source / filename
                    if src_file.exists():
                        zf.write(src_file, f"assets/{filename}")
