import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

import questionary
import typer
from rich import print
from rich.table import Table

from kistn.prompts import SSH_KEY_GEN_HELP, SSH_KEY_UPLOAD_HELP
from kistn.storage_box_config import StorageBoxConfig
from kistn.utils import add_ssh_host_entry
from kistn.validators import (validate_hostname, validate_nickname,
                              validate_port, validate_username)

REQUIRED_TOOLS = {
    "borg": "BorgBackup core",
    "borgmatic": "Borgmatic wrapper",
    "ssh": "OpenSSH client",
    "ssh-keygen": "OpenSSH key generator",
    "ssh-copy-id": "OpenSSH key installer",
}


def check_system_dependencies() -> None:
    """Checks if all required system tools are installed in PATH."""
    table = Table(title="Checking System Dependencies", show_header=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Info", style="dim")

    missing_tools = []

    for tool, info in REQUIRED_TOOLS.items():
        if shutil.which(tool) is not None:
            table.add_row(tool, "[green]✔ Installed[/green]", info)
        else:
            table.add_row(tool, "[red]✖ Missing[/red]", info)
            missing_tools.append(tool)

    print(table)
    print()

    if missing_tools:
        print(
            f"[bold red]✖ Missing required tools:[/bold red] {', '.join(missing_tools)}\n"
            "[yellow]Please install missing dependencies via your package manager before continuing.[/yellow]\n"
        )
        raise typer.Exit(code=1)


def prompt_confirm_with_exit(message: str) -> bool:
    result = questionary.confirm(message).ask()

    if result is None:
        raise typer.Exit(code=1)

    return result


def prompt_storage_box_config() -> StorageBoxConfig:
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

    return StorageBoxConfig(nickname, hostname, port, username)


def run_command_within_typer(cmd: subprocess._CMD) -> None:
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as error:
        print(f"[bold red]ERROR: {error}[/bold red]")
        raise typer.Exit(code=1)


def ssh_key_generation_step(config: StorageBoxConfig, key_path: Path):
    if not key_path.exists():
        gen_ssh_key = prompt_confirm_with_exit(
            "Generate dedicated SSH key? (recommended)"
        )
        if gen_ssh_key:
            print(SSH_KEY_GEN_HELP)
            run_command_within_typer(
                ["ssh-keygen", "-t", "ed25519", "-f", str(key_path)]
            )
            print("[green]✓ SSH key generated.[/green]")


def update_ssh_config_step(config: StorageBoxConfig, key_path: Path):
    added = add_ssh_host_entry(
        nickname=config.nickname,
        hostname=config.hostname,
        port=config.port,
        user=config.username,
        key_path=str(key_path),
    )
    if added:
        print("[green]✓ Added Host entry to ~/.ssh/config[/green]")
    else:
        print("[blue]i SSH host entry already exists. Skipping.[/blue]")
    print()


def upload_ssh_key_step(config: StorageBoxConfig, key_path: Path):
    upload_ssh = questionary.confirm(
        "Upload SSH key to Storage Box now? (recommended)"
    ).ask()

    if upload_ssh is None:
        raise typer.Exit(code=1)

    if upload_ssh:
        print(SSH_KEY_UPLOAD_HELP)
        run_command_within_typer(
            ["ssh-copy-id", "-s", "-i", f"{key_path}.pub", config.nickname]
        )
