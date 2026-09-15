import typer
from rich.console import Console
from rich.table import Table

console = Console()


def hint(message: str):
    console.print(f"[dim]{message}[/dim]")


def info(message: str):
    console.print(f"[bold blue]INFO:[/bold blue] {message}")


def success(message: str):
    console.print(f"[bold green]SUCCESS:[/bold green] {message}")


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
