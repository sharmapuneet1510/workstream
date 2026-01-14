from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from dateutil import parser as dtparser

from core.settings import SETTINGS
from services.fsio import read_json, atomic_write_json, file_lock


# ✅ Your Settings uses storage_root (not storage_dir)
RELEASES_FILE = SETTINGS.storage_root / "releases" / "releases.json"
LOCK = SETTINGS.storage_root / "locks" / "releases.lock"


def _default_data() -> Dict[str, Any]:
    return {"releases": []}


def _load() -> Dict[str, Any]:
    return read_json(RELEASES_FILE, default=_default_data())


def _save(data: Dict[str, Any]) -> None:
    atomic_write_json(RELEASES_FILE, data)


def countdown_str(window_start_iso: str) -> str:
    now = datetime.now()
    try:
        target = dtparser.isoparse(window_start_iso).replace(tzinfo=None)
    except Exception:
        return "-"

    delta = target - now
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "In progress / Past"

    days = total_seconds // 86400
    if days >= 1:
        return f"{days} days"

    hours = total_seconds // 3600
    if hours >= 1:
        return f"{hours} hours"

    mins = max(1, total_seconds // 60)
    return f"{mins} min"


def list_releases() -> List[Dict[str, Any]]:
    return _load().get("releases", [])


def get_release(release_id: str) -> Dict[str, Any] | None:
    for r in list_releases():
        if r["id"] == release_id:
            return r
    return None


def _template_items_to_tasks(
    items: List[Dict[str, str]],
    default_assignee: str,
    default_due_time_iso: str,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        out.append(
            {
                "id": f"RT-{uuid.uuid4().hex[:8].upper()}",
                "title": title,
                "category": (it.get("category") or "Workflow").strip() or "Workflow",
                "assignee": default_assignee,
                "status": "TODO",
                "due_time": default_due_time_iso,
                "created_at": datetime.utcnow().isoformat(),
                "deleted": False,
                "delete_comment": "",
                "deleted_at": "",
            }
        )
    return out


def create_release(
    name: str,
    description: str,
    window_start_iso: str,
    window_end_iso: str,
    release_manager: str,
    project_ids: List[str],
    template_name: str,
    template_items: List[Dict[str, str]],
    last_minute_items: List[Dict[str, str]],
    last_minute_days_threshold: int = 4,
    notes: str = "",
) -> Dict[str, Any]:
    with file_lock(LOCK):
        data = _load()
        rid = f"REL-{uuid.uuid4().hex[:8].upper()}"

        start_dt = dtparser.isoparse(window_start_iso).replace(tzinfo=None)
        now = datetime.now()
        is_last_minute = (start_dt - now) <= timedelta(days=last_minute_days_threshold)

        tasks: List[Dict[str, Any]] = []
        tasks.extend(_template_items_to_tasks(template_items, release_manager, window_start_iso))

        if is_last_minute and last_minute_items:
            tasks.extend(_template_items_to_tasks(last_minute_items, release_manager, window_start_iso))

        rel = {
            "id": rid,
            "name": name,
            "description": description,
            "notes": notes or "",
            "window_start": window_start_iso,
            "window_end": window_end_iso,
            "release_manager": release_manager,
            "project_ids": project_ids,
            "workflow_template": template_name,
            "is_last_minute": is_last_minute,
            "created_at": datetime.utcnow().isoformat(),
            "tasks": tasks,
        }

        data["releases"].append(rel)
        _save(data)
        return rel


def update_release(release_id: str, patch: Dict[str, Any]) -> None:
    with file_lock(LOCK):
        data = _load()
        for r in data["releases"]:
            if r["id"] == release_id:
                for k in ["name", "description", "notes", "window_start", "window_end", "release_manager", "project_ids"]:
                    if k in patch:
                        r[k] = patch[k]
                _save(data)
                return
        raise ValueError("Release not found")


def add_release_task(release_id: str, title: str, assignee: str, category: str, due_time_iso: str) -> None:
    with file_lock(LOCK):
        data = _load()
        for r in data["releases"]:
            if r["id"] == release_id:
                r.setdefault("tasks", [])
                r["tasks"].append(
                    {
                        "id": f"RT-{uuid.uuid4().hex[:8].upper()}",
                        "title": title.strip(),
                        "assignee": assignee,
                        "category": category.strip() or "Workflow",
                        "status": "TODO",
                        "due_time": due_time_iso.strip(),
                        "created_at": datetime.utcnow().isoformat(),
                        "deleted": False,
                        "delete_comment": "",
                        "deleted_at": "",
                    }
                )
                _save(data)
                return
        raise ValueError("Release not found")


def update_release_task(release_id: str, idx: int, patch: Dict[str, Any]) -> None:
    with file_lock(LOCK):
        data = _load()
        for r in data["releases"]:
            if r["id"] != release_id:
                continue
            tasks = r.get("tasks", [])
            if idx < 0 or idx >= len(tasks):
                raise IndexError("Release task index out of range")
            t = tasks[idx]
            for k in ["title", "assignee", "category", "status", "due_time"]:
                if k in patch:
                    t[k] = patch[k]
            _save(data)
            return
        raise ValueError("Release not found")


def soft_delete_release_task(release_id: str, idx: int, comment: str) -> None:
    with file_lock(LOCK):
        data = _load()
        for r in data["releases"]:
            if r["id"] != release_id:
                continue
            tasks = r.get("tasks", [])
            if idx < 0 or idx >= len(tasks):
                raise IndexError("Release task index out of range")
            t = tasks[idx]
            t["deleted"] = True
            t["delete_comment"] = (comment or "").strip()
            t["deleted_at"] = datetime.utcnow().isoformat()
            _save(data)
            return
        raise ValueError("Release not found")