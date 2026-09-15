from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from kistn import consts, utils

DEFAULT_VALUE_REGISTRY: dict[str, Any] = {
    "trusted_ssh_fingerprints": consts.SSH_DEFAULT_TRUSTED_FINGERPRINTS,
}


class Settings(BaseModel):
    trusted_ssh_fingerprints: list[str]

    @classmethod
    def from_default(cls, **args):
        # replace missing fields with defaults
        for field, value in DEFAULT_VALUE_REGISTRY.items():
            if field not in args:
                args[field] = value

        return Settings(**args)


def load(path: Path = consts.CONFIG_FILE) -> Settings:
    if not path.exists():
        utils.console.error(
            "Config file does not exist. Please run [cyan]`kistn setup`[/cyan] first."
        )
        raise SystemExit(1)

    return utils.io.load_pydantic_from_yaml(Settings, path)


def save(config: Settings, path: Path = consts.CONFIG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    utils.io.save_pydantic_to_yaml(config, path)


_settings = None


def __getattr__(name: str):
    # lazy load settings
    global _settings
    if name == "active":
        if _settings is None:
            _settings = load()
        return _settings
    raise AttributeError(f"Module {__name__!r} has no attribute {name}.")
