from __future__ import annotations

from typing import Any, Dict, List

from core.settings import SETTINGS
from services.fsio import read_json, atomic_write_json


# ✅ Your Settings uses storage_root (not storage_dir)
CFG_DIR = SETTINGS.storage_root / "config"
CFG_DIR.mkdir(parents=True, exist_ok=True)

APPS_FILE = CFG_DIR / "applications.json"
USERS_FILE = CFG_DIR / "users.json"
WORKFLOW_FILE = CFG_DIR / "checklists.json"  # contains workflow templates


def _ensure_defaults() -> None:
    if not APPS_FILE.exists():
        atomic_write_json(APPS_FILE, {"applications": ["Axel", "GTR", "DTCC", "Ruby"]})

    if not USERS_FILE.exists():
        atomic_write_json(USERS_FILE, {"users": ["me", "qa_lead", "release_mgr", "dev_lead"]})

    if not WORKFLOW_FILE.exists():
        atomic_write_json(
            WORKFLOW_FILE,
            {
                "templates": [
                    {
                        "name": "Standard Release Workflow",
                        "items": [
                            {"title": "Code freeze confirmation", "category": "Workflow"},
                            {"title": "Release notes prepared", "category": "Workflow"},
                            {"title": "Smoke test in staging", "category": "QA"},
                            {"title": "Rollback plan confirmed", "category": "Workflow"},
                        ],
                    },
                    {
                        "name": "Last Minute Add-ons",
                        "items": [
                            {"title": "Stakeholder notification: late release", "category": "Workflow"},
                            {"title": "Double-run sanity tests", "category": "QA"},
                            {"title": "Extended monitoring window agreed", "category": "Workflow"},
                        ],
                    },
                ],
                "last_minute_template_name": "Last Minute Add-ons",
                "last_minute_days_threshold": 4,
            },
        )


_ensure_defaults()


def list_applications() -> List[str]:
    return read_json(APPS_FILE, default={"applications": []}).get("applications", [])


def list_users() -> List[str]:
    return read_json(USERS_FILE, default={"users": []}).get("users", [])


def list_workflow_config() -> Dict[str, Any]:
    return read_json(
        WORKFLOW_FILE,
        default={"templates": [], "last_minute_template_name": "", "last_minute_days_threshold": 4},
    )