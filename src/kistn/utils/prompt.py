import subprocess

import questionary
import typer


def run_command_within_typer(cmd: subprocess._CMD) -> None:
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as error:
        print(f"[bold red]ERROR: {error}[/bold red]")
        raise typer.Exit(code=1)
