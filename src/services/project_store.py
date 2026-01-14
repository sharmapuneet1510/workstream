from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid

from core.settings import SETTINGS
from services.fsio import read_json, atomic_write_json, file_lock


LOCK = SETTINGS.storage_root / "locks" / "projects.lock"
FILE = SETTINGS.storage_root / "projects" / "projects.json"


def _load() -> Dict[str, Any]:
    return read_json(FILE, default={"projects": []}) or {"projects": []}


def _save(data: Dict[str, Any]) -> None:
    atomic_write_json(FILE, data)


def list_projects() -> List[Dict[str, Any]]:
    return _load().get("projects", [])


def create_project(name: str, application: str, description: str = "") -> Dict[str, Any]:
    with file_lock(LOCK):
        data = _load()
        pid = f"PRJ-{uuid.uuid4().hex[:8].upper()}"
        p = {
            "id": pid,
            "name": name,
            "application": application,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "tasks": []
        }
        data["projects"].append(p)
        _save(data)
        return p


def find_project(project_id: str) -> Optional[Dict[str, Any]]:
    for p in list_projects():
        if p["id"] == project_id:
            return p
    return None


def add_task(project_id: str, title: str, jira_ref: str, category: str, assignee: str, status: str = "TODO") -> Dict[str, Any]:
    with file_lock(LOCK):
        data = _load()
        for p in data["projects"]:
            if p["id"] != project_id:
                continue
            tid = f"T-{uuid.uuid4().hex[:8].upper()}"
            t = {
                "id": tid,
                "title": title,
                "jira_ref": jira_ref,
                "category": category,
                "assignee": assignee,
                "status": status,  # TODO | IN_PROGRESS | DONE
                "created_at": datetime.utcnow().isoformat(),
                "jira_synced": False
            }
            p["tasks"].append(t)
            _save(data)
            return t
        raise ValueError("Project not found")


def update_task_status(project_id: str, task_id: str, new_status: str) -> None:
    with file_lock(LOCK):
        data = _load()
        for p in data["projects"]:
            if p["id"] != project_id:
                continue
            for t in p["tasks"]:
                if t["id"] == task_id:
                    t["status"] = new_status
                    _save(data)
                    return
        raise ValueError("Task not found")


def project_completion(project: Dict[str, Any]) -> float:
    tasks = project.get("tasks", [])
    if not tasks:
        return 0.0
    done = sum(1 for t in tasks if t["status"] == "DONE")
    return round((done / len(tasks)) * 100.0, 1)


def category_completion(project: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    returns:
    { "QA": {"total": 10, "done": 6, "pct": 60.0}, ... }
    """
    tasks = project.get("tasks", [])
    out: Dict[str, Dict[str, Any]] = {}
    for t in tasks:
        c = (t.get("category") or "Uncategorized").strip() or "Uncategorized"
        out.setdefault(c, {"total": 0, "done": 0, "pct": 0.0})
        out[c]["total"] += 1
        if t["status"] == "DONE":
            out[c]["done"] += 1
    for c, v in out.items():
        v["pct"] = round((v["done"] / v["total"]) * 100.0, 1) if v["total"] else 0.0
    return out