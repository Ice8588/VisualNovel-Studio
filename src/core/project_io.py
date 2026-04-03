"""專案存讀：將 Project 序列化為 .vnsproj（JSON）並反序列化。"""

from __future__ import annotations

import json
from pathlib import Path

from src.core.models import Project


def save_project(project: Project, path: Path) -> None:
    """將 Project 序列化為 JSON 並寫入 .vnsproj 檔案。"""
    path = Path(path)
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
