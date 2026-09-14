from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, TypeAdapter

T = TypeVar("T", bound=BaseModel)


def load_pydantic_from_yaml(
    model_class: type[T],
    path: Path,
) -> T:
    with open(path, "r") as file:
        raw = yaml.safe_load(file)
    return model_class.model_validate(raw)


def load_pydantic_list_from_yaml(
    model_class: type[T],
    path: Path,
) -> list[T]:
    with open(path, "r") as file:
        raw = yaml.safe_load(file)
    return TypeAdapter(list[model_class]).validate_python(raw)


def save_pydantic_to_yaml(model: BaseModel, path: Path) -> None:
    with open(path, "w") as file:
        yaml.safe_dump(
            model.model_dump(mode="json"),
            file,
            sort_keys=False,
        )


def save_pydantic_list_to_yaml(
    model: list[T],
    model_class: type[T],
    path: Path,
) -> None:
    data = TypeAdapter(list[model_class]).dump_python(model, mode="json")
    with open(path, "w") as file:
        yaml.safe_dump(
            data,
            file,
            sort_keys=False,
        )
