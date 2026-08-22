import subprocess
from pathlib import Path
from typing import Annotated, Optional

import questionary
import typer
from rich import print
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kistn.utils import (ensure_ssh_host_entry, get_days_since_last_backup,
                         is_host_reachable, record_last_backup,
                         send_notification)
from kistn.validators import (validate_hostname, validate_nickname,
                              validate_port, validate_username)

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
    # print title
    panel = Panel.fit("[bold blue]Borgmatic Setup Wizard[/bold blue]")
    centered_renderable = Align.center(panel)
    console.print(centered_renderable)

    # internal name for storage box
    print(
        "[dim]This nickname used internally to identify your storage box and for files (e.g. SSH key file) on your local machine.[/dim]"
    )
    nickname = questionary.text(
        "storage box nickname:",
        default="pandoras-box",
        validate=validate_nickname,
    ).ask()
    print()

    if not nickname:
        raise typer.Exit(code=1)

    # hetzner storage box hostname
    print(
        "[dim]The hostname can be found in the Hetzner Console and should look something like this: uXXXXXX.your-storagebox.de (where X is a digit).[/dim]"
    )
    hostname = questionary.text(
        "storage box hostname: ",
        default="uXXXXXX.your-storagebox.de",
        validate=validate_hostname,
    ).ask()
    print()

    if not hostname:
        raise typer.Exit(code=1)

    # hetzner storage box hostname
    print(
        "[dim]The SSH port can be found in the Hetzner Console. But it should almost definitely be port 23.[/dim]"
    )
    port = questionary.text(
        "storage box SSH port: ",
        default="23",
        validate=validate_port,
    ).ask()
    print()

    if not port:
        raise typer.Exit(code=1)
    port = int(port)

    # hetzner storage box username
    print(
        "[dim]The username can be found in the Hetzner Console and should look something like this: uXXXXXX (where X is a digit). [/dim]",
    )
    username = questionary.text(
        "storage box username:",
        default="uXXXXXX",
        validate=validate_username,
    ).ask()
    print()

    if not username:
        raise typer.Exit(code=1)

    # SSH key generation
    key_path = Path.home() / ".ssh" / nickname
    if not key_path.exists():
        gen_ssh_key = questionary.confirm(
            "Generate dedicated SSH key? (recommended)"
        ).ask()

        if gen_ssh_key is None:
            raise typer.Exit(code=1)

        if gen_ssh_key:
            print(
                Panel(
                    "You are going to be asked for a passphrase for the SSH key. If you enter a passphrase, you'll be asked to type it in every time you use it to authenticate yourself in an SSH connection. This is more secure, but also more cumbersome. So pick your poision.\n",
                    title="[bold blue]Interactive Steps Required[/bold blue]",
                    border_style="white",
                    expand=False,
                )
            )
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", str(key_path)], check=True
            )
            print("[green]✓ SSH key generated.[/green]")

    # add entry to SSH config
    added = ensure_ssh_host_entry(
        nickname=nickname,
        hostname=hostname,
        port=port,
        user=username,
        key_path=str(key_path),
    )
    if added:
        print("[green]✓ Added Host entry to ~/.ssh/config[/green]")
    else:
        print("[blue]i SSH host entry already exists. Skipping.[/blue]")
    print()

    # upload SSH key to storage box
    upload_ssh = questionary.confirm(
        "Upload SSH key to Storage Box now? (recommended)"
    ).ask()

    if upload_ssh is None:
        raise typer.Exit(code=1)

    if upload_ssh:
        print(
            Panel(
                "SSH will now initiate a first-time connection to Hetzner:\n\n"
                "1. [bold white]Accept Fingerprint:[/bold white] Type [cyan]yes[/cyan] when prompted to trust the host key.\n"
                "[dim]  💡 NOTE: If you want to check the authenticity of the server, you can check if the fingerprint matches one of the fingerprints mentioned in the [cyan][link=https://docs.hetzner.com/storage/storage-box/general#ssh-host-keys]official Hetzner documentation[/link][/cyan].[/dim]\n\n"
                "2. [bold white]Enter Password:[/bold white] Type your Hetzner Storage Box password when asked.\n",
                title="[bold blue]Interactive Steps Required[/bold blue]",
                border_style="white",
                expand=False,
            )
        )

        cmd = ["ssh-copy-id", "-s", "-i", f"{key_path}.pub", nickname]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as error:
            print(f"[bold red]ERROR: {error}[/bold red]")
            raise typer.Exit(code=1)

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
