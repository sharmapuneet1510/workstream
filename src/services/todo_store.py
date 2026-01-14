from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any, List

from core.settings import SETTINGS
from services.fsio import read_json, atomic_write_json, file_lock
from services.project_store import add_task, update_task_status

TODO_FILE = SETTINGS.storage_root / "todos" / "todos.json"
LOCK = SETTINGS.storage_root / "locks" / "todos.lock"


def _default():
    return {"todos": []}


def _load():
    return read_json(TODO_FILE, default=_default())


def _save(data):
    atomic_write_json(TODO_FILE, data)


def due_in(due_iso: str) -> str:
    try:
        due = datetime.fromisoformat(due_iso)
    except Exception:
        return "-"
    delta = due - datetime.now()
    sec = int(delta.total_seconds())
    if sec <= 0:
        return "Overdue"
    if sec >= 86400:
        return f"{sec//86400} days"
    if sec >= 3600:
        return f"{sec//3600} hrs"
    return f"{max(1, sec//60)} min"


def list_todos() -> List[Dict[str, Any]]:
    return _load()["todos"]


def create_todo(
    title: str,
    assignee: str,
    project_id: str,
    priority: str,
    due_date: str,
):
    with file_lock(LOCK):
        data = _load()
        tid = f"TD-{uuid.uuid4().hex[:8].upper()}"

        # Auto-link to project
        proj_task_id = add_task(
            project_id,
            title=title,
            jira_ref="",
            category="TODO",
            assignee=assignee,
            status="TODO",
        )

        data["todos"].append(
            {
                "id": tid,
                "title": title,
                "assignee": assignee,
                "project_id": project_id,
                "project_task_id": proj_task_id,
                "priority": priority,
                "due_date": due_date,
                "status": "TODO",
                "subtasks": [],
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        _save(data)


def add_subtask(todo_id: str, title: str):
    with file_lock(LOCK):
        data = _load()
        for t in data["todos"]:
            if t["id"] == todo_id:
                t["subtasks"].append(
                    {
                        "id": f"ST-{uuid.uuid4().hex[:6].upper()}",
                        "title": title,
                        "status": "TODO",
                    }
                )
                _save(data)
                return
        raise ValueError("Todo not found")


def update_todo_status(todo_id: str, status: str):
    with file_lock(LOCK):
        data = _load()
        for t in data["todos"]:
            if t["id"] == todo_id:
                t["status"] = status
                update_task_status(t["project_id"], t["project_task_id"], status)
                _save(data)
                return
        raise ValueError("Todo not found")


def update_subtask_status(todo_id: str, idx: int, status: str):
    with file_lock(LOCK):
        data = _load()
        for t in data["todos"]:
            if t["id"] == todo_id:
                t["subtasks"][idx]["status"] = status
                _sync_parent_status(t)
                _save(data)
                return
        raise ValueError("Todo not found")


def _sync_parent_status(todo: Dict[str, Any]):
    subs = todo["subtasks"]
    if not subs:
        return
    done = sum(1 for s in subs if s["status"] == "DONE")
    if done == len(subs):
        todo["status"] = "DONE"
    elif done > 0:
        todo["status"] = "IN_PROGRESS"
    else:
        todo["status"] = "TODO"


def todo_progress(todo: Dict[str, Any]) -> int:
    subs = todo.get("subtasks", [])
    if not subs:
        return 100 if todo["status"] == "DONE" else 0
    done = sum(1 for s in subs if s["status"] == "DONE")
    return int((done / len(subs)) * 100)