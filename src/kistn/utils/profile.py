from pathlib import Path

from kistn import consts
from kistn.models import Profile

from . import io


def load(path: Path = consts.PROFILES_CACHE_FILE) -> dict[str, Profile]:
    if not path.exists():
        return dict()
    profiles = io.load_pydantic_list_from_yaml(Profile, path)
    return {p.name: p for p in profiles}


def save(profiles: dict[str, Profile], path: Path = consts.PROFILES_CACHE_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    io.save_pydantic_list_to_yaml(list(profiles.values()), Profile, path)
