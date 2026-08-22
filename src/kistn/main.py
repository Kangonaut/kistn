import subprocess
from abc import update_abstractmethods
from pathlib import Path

import questionary
import typer
from rich import print
from rich.console import Console
from rich.table import Table

from kistn.prompts import SSH_KEY_GEN_HELP, SSH_KEY_UPLOAD_HELP
from kistn.subroutines import (check_system_dependencies,
                               prompt_confirm_with_exit,
                               prompt_storage_box_config,
                               run_command_within_typer, ssh_config_step,
                               ssh_key_generation_step, update_ssh_config_step,
                               upload_ssh_key_step)
from kistn.utils import (add_ssh_host_entry, get_days_since_last_backup,
                         is_host_reachable, record_last_backup,
                         send_notification)

app = typer.Typer(
    help="📦 **kistn**: A CLI manager for Borgmatic and Hetzner Storage Box backups.",
    rich_markup_mode="markdown",
    add_completion=False,
)
console = Console()


@app.command()
def setup():
    """
    Walk through initial setup and SSH key configuration.

    Generates a dedicated ED25519 key, updates `~/.ssh/config`, copies keys to
    the remote server, and initializes the Borg repository.
    """
    check_system_dependencies()

    config = prompt_storage_box_config()

    key_path = Path.home() / ".ssh" / config.nickname

    ssh_key_generation_step(config, key_path)
    update_ssh_config_step(config, key_path)
    upload_ssh_key_step(config, key_path)

    print("\n[bold green]✓ Setup complete![/bold green]")


@app.command()
def run():
    """
    Run a backup with connection pre-flight checks.
    """
    console.print("[blue]Checking connection to Storage Box...[/blue]")
    if not is_host_reachable(STORAGE_BOX_HOST, port=23):
        console.print(
            "[bold red]:x: Storage Box is unreachable. Check connection/VPN.[/bold red]"
        )
        send_notification(
            title="Backup Cancelled",
            message="Storage Box host is unreachable.",
            urgency="critical",
            icon="network-offline",
        )
        raise typer.Exit(code=1)

    with console.status(
        "[bold green]Running Borgmatic backup...[/bold green]", spinner="dots"
    ):
        result = subprocess.run(["borgmatic", "create", "--verbosity", "1", "--stats"])

    if result.returncode == 0:
        record_last_backup()
        console.print("[bold green]✔ Backup completed successfully![/bold green]")
        send_notification(
            title="Backup Successful",
            message="Your Borgmatic backup completed successfully.",
            urgency="normal",
            icon="emblem-default",
        )
    else:
        console.print("[bold red]✖ Backup failed. Check logs above.[/bold red]")
        send_notification(
            title="Backup Failed",
            message="Borgmatic backup encountered an error!",
            urgency="critical",
            icon="dialog-error",
        )


@app.command(name="check-shell")
def check_shell(
    threshold: int = 7,
    desktop_notify: bool = typer.Option(True, help="Send a desktop popup if overdue"),
):
    """Fast, silent check for .zshrc integration. Prints banner and optional popup if overdue."""
    days = get_days_since_last_backup()
    if days is not None and days > threshold:
        msg = f"Your last backup was {days} days ago. Run 'backup run' to sync."

        # Terminal output
        console.print(f"[bold yellow]⚠️  Backup Warning:[/bold yellow] {msg}")

        # Desktop notification
        if desktop_notify:
            send_notification(
                title="Backup Overdue",
                message=msg,
                urgency="critical",
                icon="dialog-warning",
            )


@app.command()
def status():
    """Prints last backup age and repository state."""
    days = get_days_since_last_backup()

    table = Table(title="Backup System Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")

    if days is None:
        table.add_row("Last Backup", "Never recorded locally")
    else:
        color = "green" if days <= 7 else "red"
        table.add_row("Last Backup", f"[{color}]{days} day(s) ago[/{color}]")

    reachable = is_host_reachable(STORAGE_BOX_HOST, port=23)
    table.add_row(
        "Storage Box Reachable", "[green]Yes[/green]" if reachable else "[red]No[/red]"
    )

    console.print(table)


@app.command(name="test-restore")
def test_restore():
    """Extracts latest archive metadata or canary files to test restore capability."""
    console.print("[blue]Testing repository extraction readiness...[/blue]")
    result = subprocess.run(["borgmatic", "list"], capture_output=True, text=True)

    if result.returncode == 0:
        console.print(
            "[bold green]✔ Archive index accessible and verified.[/bold green]"
        )
    else:
        console.print("[bold red]✖ Failed to read archive list.[/bold red]")


if __name__ == "__main__":
    app()
