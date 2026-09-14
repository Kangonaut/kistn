from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from kistn import consts
from kistn.config import Settings

from . import io

T = TypeVar("T", bound=BaseModel)


def load(path: Path = consts.CONFIG_FILE) -> Settings:
    if not path.exists():
        print("Config file does not exist. Please run `kistn setup` first.")
        raise SystemExit(1)

    return io.load_pydantic_from_yaml(Settings, path)


def save(config: Settings, path: Path = consts.CONFIG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    io.save_pydantic_to_yaml(config, path)
