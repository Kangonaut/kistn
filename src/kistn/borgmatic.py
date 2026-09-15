from pathlib import Path

from pydantic import BaseModel, Field


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
