from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    storage_root: Path


def load_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[2]  # .../workstream
    storage_root = repo_root / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)

    # required storage folders
    for p in [
        storage_root / "config",
        storage_root / "projects",
        storage_root / "releases",
        storage_root / "locks",
    ]:
        p.mkdir(parents=True, exist_ok=True)

    return Settings(repo_root, storage_root)


SETTINGS = load_settings()