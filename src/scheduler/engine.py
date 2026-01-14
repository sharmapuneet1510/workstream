from __future__ import annotations

import threading
import time
from datetime import date

from services.tasks import list_tasks
from services.notifications import push_notification


class SchedulerEngine:
    """
    Standalone scheduler loop (no message queue).
    Runs lightweight checks every N seconds.
    """

    def __init__(self, interval_s: int = 60):
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                # keep scheduler alive even if a rule fails
                pass
            self._stop.wait(self.interval_s)

    def _tick(self) -> None:
        today = date.today()

        # Due today (excluding DONE)
        due_today = [
            t for t in list_tasks()
            if t.due_date == today and t.status != "DONE"
        ]
        for t in due_today:
            push_notification(
                owner=t.assignee,
                notif_type="DUE_TODAY",
                title=f"Due today: {t.title}",
                body=f"Task {t.id} in {t.project_id} is due today.",
                link=f"/tasks/{t.project_id}/{t.id}",
                task_ref=f"{t.project_id}/{t.id}",
            )

        # Overdue (excluding DONE)
        overdue = [
            t for t in list_tasks(overdue_only=True)
        ]
        for t in overdue:
            push_notification(
                owner=t.assignee,
                notif_type="OVERDUE",
                title=f"Overdue: {t.title}",
                body=f"Task {t.id} in {t.project_id} is overdue (due {t.due_date}).",
                link=f"/tasks/{t.project_id}/{t.id}",
                task_ref=f"{t.project_id}/{t.id}",
            )