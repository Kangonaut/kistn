from rich import print
from rich.table import Table

from kistn.utils import system


def run_system_dependency_check():
    table = Table(title="Checking System Dependencies", show_header=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="bold")

    missing = system.check_system_dependecies()

    for package in system.SYSTEM_DEPS:
        if package in missing:
            table.add_row(package, "[red]✖ Missing[/red]")
        else:
            table.add_row(package, "[green]✔ Installed[/green]")

    print(table)
    print()

    if missing:
        print(
            f"[bold red]✖ Missing required tools:[/bold red] {', '.join(missing)}\n"
            "[yellow]Please install missing dependencies via your package manager before continuing.[/yellow]\n"
        )
        raise typer.Exit(code=1)
