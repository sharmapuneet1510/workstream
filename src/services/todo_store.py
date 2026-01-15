from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.settings import SETTINGS
from services.fsio import read_json, atomic_write_json, file_lock

TODOS_FILE = SETTINGS.storage_root / "todos" / "todos.json"
LOCK = SETTINGS.storage_root / "locks" / "todos.lock"


def _default_data() -> Dict[str, Any]:
    return {"tasks": []}


def _load() -> Dict[str, Any]:
    return read_json(TODOS_FILE, default=_default_data())


def _save(data: Dict[str, Any]) -> None:
    atomic_write_json(TODOS_FILE, data)


def _now_utc_iso() -> str:
    return datetime.utcnow().isoformat()


def _parse_iso(dt_iso: str) -> Optional[datetime]:
    if not dt_iso:
        return None
    try:
        return datetime.fromisoformat(dt_iso.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def due_in_str(due_iso: str) -> str:
    """
    days if >= 1 day, hours if >= 1 hour, else minutes.
    If past: "Overdue"
    """
    due = _parse_iso(due_iso)
    if not due:
        return "-"
    now = datetime.now()
    secs = int((due - now).total_seconds())
    if secs <= 0:
        return "Overdue"
    days = secs // 86400
    if days >= 1:
        return f"{days} days"
    hours = secs // 3600
    if hours >= 1:
        return f"{hours} hours"
    mins = max(1, secs // 60)
    return f"{mins} min"


def compute_task_pct(task: Dict[str, Any]) -> int:
    subs = task.get("subtasks") or []
    if subs:
        total = len(subs)
        done = sum(1 for s in subs if s.get("done") is True)
        return int((done / total) * 100) if total else 0

    st = (task.get("status") or "TODO").upper()
    if st == "DONE":
        return 100
    if st == "IN_PROGRESS":
        return 50
    return 0


def list_todos() -> List[Dict[str, Any]]:
    return _load().get("tasks", [])


def create_todo(
    project_id: str,
    project_name: str,
    assignee: str,
    description: str,
    priority: str,
    due_iso: str,
    status: str = "TODO",
) -> Dict[str, Any]:
    with file_lock(LOCK):
        data = _load()
        tid = f"TD-{uuid.uuid4().hex[:8].upper()}"
        t = {
            "id": tid,
            "project_id": project_id,
            "project_name": project_name,
            "assignee": assignee,
            "description": description,
            "priority": priority,
            "due_time": due_iso,
            "status": status,
            "subtasks": [],
            "created_at": _now_utc_iso(),
            "updated_at": _now_utc_iso(),
        }
        data["tasks"].append(t)
        _save(data)
        return t


def update_todo(task_id: str, patch: Dict[str, Any]) -> None:
    """
    Patch fields: project_id, project_name, assignee, description, priority, due_time, status
    """
    with file_lock(LOCK):
        data = _load()
        for t in data["tasks"]:
            if t.get("id") == task_id:
                for k in [
                    "project_id",
                    "project_name",
                    "assignee",
                    "description",
                    "priority",
                    "due_time",
                    "status",
                ]:
                    if k in patch:
                        t[k] = patch[k]
                t["updated_at"] = _now_utc_iso()
                _save(data)
                return
        raise ValueError("Todo task not found")


# optional compatibility helper
def update_todo_status(task_id: str, status: str) -> None:
    update_todo(task_id, {"status": status})


def add_subtask(task_id: str, title: str) -> None:
    title = (title or "").strip()
    if not title:
        return

    with file_lock(LOCK):
        data = _load()
        for t in data["tasks"]:
            if t.get("id") == task_id:
                t.setdefault("subtasks", [])
                t["subtasks"].append(
                    {
                        "id": f"ST-{uuid.uuid4().hex[:6].upper()}",
                        "title": title,
                        "done": False,
                        "created_at": _now_utc_iso(),
                    }
                )
                t["updated_at"] = _now_utc_iso()
                _save(data)
                return
        raise ValueError("Todo task not found")


def toggle_subtask(task_id: str, sub_id: str, done: bool) -> None:
    with file_lock(LOCK):
        data = _load()
        for t in data["tasks"]:
            if t.get("id") == task_id:
                for s in (t.get("subtasks") or []):
                    if s.get("id") == sub_id:
                        s["done"] = bool(done)
                        t["updated_at"] = _now_utc_iso()
                        _save(data)
                        return
                raise ValueError("Subtask not found")
        raise ValueError("Todo task not found")