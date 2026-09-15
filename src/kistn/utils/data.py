import os
import time
from pathlib import Path

from kistn import consts


def get_backup_profiles() -> list[str]:
    return [file.name for file in consts.CONFIG_DIR.iterdir()]


def record_last_backup(profile: str) -> None:
    path = consts.CACHE_DIR / profile
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(int(time.time())))


def get_days_since_last_backup(profile: str) -> int | None:
    path = consts.CACHE_DIR / profile

    if not path.exists():
        return None
    try:
        last_time = int(path.read_text().strip())
        return int((time.time() - last_time) / 86400)
    except ValueError:
        return None
