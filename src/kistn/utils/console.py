import typer
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


def warn(message: str):
    console.print(f"[bold yellow]⚠ WARN:[/bold yellow] {message}")


def error(message: str):
    console.print(f"[bold red]✖ ERROR:[/bold red] {message}")


def abort_with_error(message: str) -> None:
    error(message)
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
