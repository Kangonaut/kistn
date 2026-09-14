from pathlib import Path

from kistn import consts
from kistn.models import Remote

from . import io


def load(path: Path = consts.REMOTES_CACHE_FILE) -> dict[str, Remote]:
    if not path.exists():
        return dict()
    remotes = io.load_pydantic_list_from_yaml(Remote, path)
    return {r.name: r for r in remotes}


def save(remotes: dict[str, Remote], path: Path = consts.REMOTES_CACHE_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    io.save_pydantic_list_to_yaml(list(remotes.values()), Remote, path)
