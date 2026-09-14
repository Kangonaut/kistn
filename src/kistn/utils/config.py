from pathlib import Path
from typing import ClassVar, TypeVar

import yaml
from pydantic import BaseModel

from kistn.models import BorgmaticConfig


def save_config(path: Path, config: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as file:
        yaml.safe_dump(
            config.model_dump(mode="json"),
            file,
            sort_keys=False,
            default_flow_style=False,
        )


T = TypeVar("T", bound=BaseModel)


def load_config(path: Path, model_class: type[T]) -> T:
    with open(path, "r") as file:
        raw_config = yaml.safe_load(file)
    return model_class.model_validate(raw_config)
