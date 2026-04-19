"""專案存讀：將 Project 序列化為 .vnsproj（JSON）並反序列化。"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from src.core.models import Project


def save_project(project: Project, path: Path) -> None:
    """將 Project 序列化為 JSON 並寫入 .vnsproj；同時把 assets/ 從原來源目錄搬到目標目錄。

    來源目錄判定：
    - 已有 project_path → 其 parent（既存專案另存到別處）
    - 尚未存檔 → 暫存的 ``%TEMP%/vnstudio_unsaved``（首次存檔）

    來源 == 目的時跳過搬移（同位置 save 不做事）。
    """
    path = Path(path)
    target_dir = path.parent

    if project.project_path:
        source_dir = Path(project.project_path).parent
    else:
        source_dir = Path(tempfile.gettempdir()) / "vnstudio_unsaved"

    src_assets = source_dir / "assets"
    dst_assets = target_dir / "assets"
    try:
        same = src_assets.resolve() == dst_assets.resolve()
    except (OSError, RuntimeError):
        same = src_assets == dst_assets
    if (not same) and src_assets.exists():
        shutil.copytree(src_assets, dst_assets, dirs_exist_ok=True)

    project.project_path = path
    data = project.to_dict()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_project(path: Path) -> Project:
    """從 .vnsproj 檔案讀取並還原為 Project 物件。"""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    project = Project.from_dict(data)
    project.project_path = path
    return project
