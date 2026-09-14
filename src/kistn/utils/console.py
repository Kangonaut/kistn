import typer
from rich.console import Console
from rich.table import Table

from kistn.models import Profile, Remote

console = Console()


def hint(message: str):
    console.print(f"[dim]{message}[/dim]")


def info(message: str):
    console.print(f"[bold blue]INFO:[/bold blue] {message}")


def warn(message: str):
    console.print(f"[bold yellow]WARN:[/bold yellow] {message}")


def error(message: str):
    console.print(f"[bold red]ERROR:[/bold red] {message}")


def abort_with_error(message: str) -> None:
    error(message)
    raise typer.Exit(code=1)


def abort():
    console.print("\nAborted.")
    raise typer.Exit(code=0)


def abort_with_message(message: str):
    console.print(message)
    raise typer.Exit(code=0)


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


def print_remotes(remotes: list[Remote]):
    if not remotes:
        console.print(
            "No remote connections found. Create a profile using [cyan]`kistn remote create`[/cyan]."
        )
        return

    table = Table(box=None)

    table.add_column("Name", style="bold green")
    table.add_column("Hostname", style="white")
    table.add_column("Port", style="white")
    table.add_column("Username", style="white")
    table.add_column("Description", style="dim")

    for remote in remotes:
        table.add_row(
            remote.name,
            remote.hostname,
            str(remote.port),
            remote.username,
            remote.description or "-",
        )

    console.print(table)
