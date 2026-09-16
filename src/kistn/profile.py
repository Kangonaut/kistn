import enum
from datetime import datetime, timezone
from functools import total_ordering
from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from kistn import consts, utils
from kistn.borgmatic import BorgmaticConfig

console = Console()


@total_ordering
class ProfileState(str, enum.Enum):
    CREATED = "created"
    CONFIGURED = "configured"
    INITIALIZED = "initialized"
    READY = "ready"

    def get_console_color(self) -> str:
        match self:
            case ProfileState.CREATED:
                return "bold white"
            case ProfileState.CONFIGURED:
                return "bold cyan"
            case ProfileState.INITIALIZED:
                return "bold yellow"
            case ProfileState.READY:
                return "bold green"

    def __repr__(self) -> str:
        color = self.get_console_color()
        return f"[{color}]{self.name}[/{color}]"

    @property
    def rank(self) -> int:
        return list(self.__class__).index(self)

    def __lt__(self, other) -> bool:
        if isinstance(other, ProfileState):
            return self.rank < other.rank
        return NotImplemented


class Profile(BaseModel):
    name: str
    description: str
    frequency: int
    automatic: bool
    last_backup: datetime | None = Field(default=None)
    state: ProfileState = Field(default=ProfileState.CREATED)

    @property
    def borgmatic_config_file(self) -> Path:
        return BorgmaticConfig.get_path(self.name)

    def format_due_date(self) -> str:
        if not self.last_backup:
            return "[bold green]today[/bold green]"

        delta = datetime.now(timezone.utc) - self.last_backup
        days = self.frequency - delta.days

        if days == 0:
            return "[bold green]today[/bold green]"
        if days == 1:
            return "[bold blue]tomorrow[/bold blue]"
        if days == -1:
            return "[bold red]yesterday[/bold red]"
        if days > 1:
            return f"[bold blue]in {days} days[/bold blue]"
        else:
            return f"[bold red]{days} days ago[/bold red]"

    def format_days_since_backup(self) -> str:
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

    table.add_column("Name", style="bold white")
    table.add_column("State", style="white")
    table.add_column("Frequency", style="white")
    table.add_column("Automatic", style="white")
    table.add_column("Description", style="dim")

    for profile in profiles:
        table.add_row(
            profile.name,
            repr(profile.state),
            str(profile.frequency),
            "Yes" if profile.automatic else "No",
            profile.description or "-",
        )

    console.print(table)


def get_profile_by_name_ensured(
    name: str, profiles: dict[str, Profile] | None = None
) -> Profile:
    return get_profile_by_name(name, profiles, check=True)  # type: ignore


def get_profile_by_name(
    name: str,
    profiles: dict[str, Profile] | None = None,
    check: bool = False,
) -> Profile | None:
    if not profiles:
        profiles = load()
    if name not in profiles:
        if check:
            utils.console.abort_with_error("Profile doesn't exist.")
        else:
            return None
    return profiles[name]
