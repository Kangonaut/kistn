from pathlib import Path

from pydantic import BaseModel, Field

from kistn import consts, utils


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

    @classmethod
    def get_path(cls, name: str) -> Path:
        return consts.BORGMATIC_CONFIG_DIR / f"kistn.{name}"

    @classmethod
    def load(cls, name: str) -> BorgmaticConfig:
        return utils.io.load_pydantic_from_yaml(BorgmaticConfig, cls.get_path(name))

    def save(self, name: str):
        path = consts.BORGMATIC_CONFIG_DIR / f"kistn.{name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        utils.io.save_pydantic_to_yaml(self, self.get_path(name))
