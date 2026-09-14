import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .models import Project

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PROJECTS_FILE = DATA_DIR / "projects.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_FILE.exists():
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _load_projects_dict() -> Dict[str, dict]:
    _ensure_data_dir()
    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_projects_dict(data: Dict[str, dict]) -> None:
    _ensure_data_dir()
    temp_file = PROJECTS_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.replace(PROJECTS_FILE)


class ProjectStorage:
    @staticmethod
    def get_all() -> List[Project]:
        raw = _load_projects_dict()
        projects = []
        for item in raw.values():
            try:
                projects.append(Project.model_validate(item))
            except Exception:
                continue
        # Sort descending by created_at
        return sorted(projects, key=lambda p: p.created_at, reverse=True)

    @staticmethod
    def get_by_id(project_id: str) -> Optional[Project]:
        raw = _load_projects_dict()
        data = raw.get(project_id)
        if not data:
            return None
        return Project.model_validate(data)

    @staticmethod
    def save(project: Project) -> Project:
        project.updated_at = datetime.now(timezone.utc).isoformat()
        raw = _load_projects_dict()
        raw[project.id] = project.model_dump()
        _save_projects_dict(raw)
        return project

    @staticmethod
    def delete(project_id: str) -> bool:
        raw = _load_projects_dict()
        if project_id in raw:
            del raw[project_id]
            _save_projects_dict(raw)
            return True
        return False
