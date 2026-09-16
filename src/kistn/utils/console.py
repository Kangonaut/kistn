from pathlib import Path

import typer
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def hint(message: str):
    # Italicizing hints helps separate them from standard text
    console.print(f"[dim italic]💡 {message}[/dim italic]")


def info(message: str):
    console.print(f"[bold blue]ℹ INFO:[/bold blue] {message}")


def success(message: str):
    console.print(f"[bold green]✔ SUCCUESS:[/bold green] {message}")


def important(message: str):
    console.print(
        f"📢 [bold black on magenta] IMPORTANT: [/bold black on magenta] [bold]{message}[/bold]"
    )


def warn(message: str):
    console.print(f"[bold yellow]⚠ WARN:[/bold yellow] {message}")


def error(message: str):
    console.print(f"[bold red]✖ ERROR:[/bold red] {message}")


def abort_with_error(message: str) -> None:
    error(message)
    raise typer.Exit(code=1)


def abort_with_error_and_command(message: str, command: str):
    error(message)
    command_panel = Panel(
        f"[bold magenta]$ {command}[/bold magenta]",
        expand=True,
        border_style="red",
        padding=(0, 3),
    )
    console.print(command_panel)
    raise typer.Exit(code=1)


def abort():
    console.print("\nAborted.")
    raise typer.Exit(code=0)


def abort_with_message(message: str):
    console.print(message)
    raise typer.Exit(code=0)


def print_command(command: str):
    command_panel = Panel(
        f"[bold cyan]$ {command}[/bold cyan]",
        expand=True,
        border_style="blue",
        padding=(0, 3),
    )
    console.print(command_panel)


def format_path(path: Path) -> str:
    return f"[link={path.resolve().as_uri()}][cyan]{path.resolve()}[/cyan][/link]"


def status(*args, **kwargs):
    return console.status(*args, **kwargs)


def print(message=None):
    return console.print(message or "")


def print_step_header(number: int, title: str, description: str):
    panel = Panel(
        f"[dim]{description}[/dim]",
        title=f"[bold cyan]STEP {number}[/bold cyan] [white]|[/white] [bold green]{title}[/bold green]",
        title_align="center",
        expand=False,
        border_style="blue",
        padding=(1, 3),
    )
    print()
    print(Align.center(panel))
    print()
