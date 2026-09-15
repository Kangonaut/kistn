from pathlib import Path

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from kistn import consts, utils

console = Console()


class Profile(BaseModel):
    name: str
    description: str
    frequency: int
    automatic: bool


def load(path: Path = consts.PROFILES_CACHE_FILE) -> dict[str, Profile]:
    if not path.exists():
        return dict()
    profiles = utils.io.load_pydantic_list_from_yaml(Profile, path)
    return {p.name: p for p in profiles}


def save(profiles: dict[str, Profile], path: Path = consts.PROFILES_CACHE_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    utils.io.save_pydantic_list_to_yaml(list(profiles.values()), Profile, path)


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
