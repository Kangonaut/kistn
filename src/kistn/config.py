from pathlib import Path

from pydantic import BaseModel, Field

from kistn import utils


class RemoteConfig(BaseModel):
    hostname: str
    port: int = Field(default=23, ge=1, le=65535)
    username: str
    name: str


class BorgmaticRepository(BaseModel):
    path: str
    label: str


class BorgmaticCheck(BaseModel):
    name: str


class BorgmaticConfig(BaseModel):
    source_directories: list[Path]
    exclude_patterns: list[str] = Field(default_factory=list)
    repositories: list[BorgmaticRepository]

    # storage and encryption
    encryption_passphrase: str
    compression: str
    archive_name_format: str  # prefix-{hostname}-{now}

    # retention policy
    keep_daily: int
    keep_weekly: int
    keep_monthly: int

    # consistency checks
    checks: list[BorgmaticCheck]


class BackupProfile(BaseModel):
    name: str
    description: str
    frequency: int
    automatic: bool


class Settings(BaseModel):
    pass


_settings = None


def __getattr__(name: str):
    # lazy load settings
    global _settings
    if name == "settings":
        if _settings is None:
            _settings = utils.config.load()
        return _settings
    raise AttributeError(f"Module {__name__!r} has no attribute {name}.")
