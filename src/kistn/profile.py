from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from kistn import consts, utils

console = Console()


class Profile(BaseModel):
    name: str
    description: str
    frequency: int
    automatic: bool
    last_backup: datetime | None = None

    def days_since_backup_str(self) -> str:
        if not self.last_backup:
            return "never"
        delta = datetime.now(timezone.utc) - self.last_backup
        days = delta.days
        if days == 0:
            return "today"
        if days == 1:
            return "yesterday"
        else:
            return f"{days} days ago"

    @property
    def config_file(self) -> Path:
        return consts.PROFILES_CACHE_DIR / self.name

    @classmethod
    def load(cls, path: Path):
        return utils.io.load_pydantic_from_yaml(Profile, path)

    def save(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        utils.io.save_pydantic_to_yaml(self, self.config_file)

    def delete(self):
        self.remove_files()

    def remove_files(self):
        self.config_file.unlink(missing_ok=True)


def load() -> dict[str, Profile]:
    dir = consts.PROFILES_CACHE_DIR
    if not dir.exists():
        return dict()
    profiles = [Profile.load(f) for f in dir.iterdir()]
    return {p.name: p for p in profiles}


def save(profiles: dict[str, Profile]):
    for p in profiles.values():
        p.save()


def print_profiles(profiles: list[Profile]):
    if not profiles:
        console.print(
            "No profiles found. Create a profile using [cyan]`kistn profile create`[/cyan]."
        )
        return

    table = Table(box=None)

    table.add_column("Name", style="bold green")
    table.add_column("Frequency", style="white")
    table.add_column("Automatic", style="white")
    table.add_column("Description", style="dim")

    for profile in profiles:
        table.add_row(
            profile.name,
            str(profile.frequency),
            "Yes" if profile.automatic else "No",
            profile.description or "-",
        )

    console.print(table)
