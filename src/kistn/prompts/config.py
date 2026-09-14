import shutil
from pathlib import Path

import questionary
from rich.panel import Panel
from rich.syntax import Syntax

from kistn import utils
from kistn.models import BorgmaticConfig


def prompt_profile_name() -> str:
    print("[dim]This is the name of your backup profile.[/dim]")
    return questionary.text(
        "profile name:",
        default="pandoras-box",
        validate=utils.validators.validate_filename,
    ).ask()


def prompt_remote_hostname() -> str:
    print(
        "[dim]The hostname can be found in the Hetzner Console and should look something like this: uXXXXXX.your-storagebox.de (where X is a digit).[/dim]"
    )
    return questionary.text(
        "storage box hostname: ",
        default="uXXXXXX.your-storagebox.de",
        validate=utils.validators.validate_hostname,
    ).ask()


def prompt_remote_port() -> int:
    print(
        "[dim]The SSH port can be found in the Hetzner Console. But it should almost definitely be port 23.[/dim]"
    )
    port = questionary.text(
        "storage box SSH port: ",
        default="23",
        validate=utils.validators.validate_port,
    ).ask()
    return int(port)


def prompt_remote_username() -> str:
    print(
        "[dim]The username can be found in the Hetzner Console and should look something like this: uXXXXXX (where X is a digit). [/dim]",
    )
    return questionary.text(
        "storage box username:",
        default="uXXXXXX",
        validate=utils.validators.validate_username,
    ).ask()


def prompt_remote_name() -> str:
    print(
        "[dim]Under what name do you want to store your backup on the storage box?[/dim]",
    )
    return questionary.text(
        "remote name:",
        default="pandoras-box",
        validate=utils.validators.validate_filename,
    ).ask()


def prompt_source_directories() -> list[str]:
    """Loop to collect source directories until the user inputs an empty line."""
    directories: list[str] = []

    print("\n[bold cyan]Source Directories[/bold cyan]")
    print(
        "[dim]Enter directories you want to back up. Press Enter without typing to finish.[/dim]\n"
    )

    while True:
        prompt_text = f"Add directory:"

        path_input = questionary.text(prompt_text).ask()

        # Stop loop if empty input
        if not path_input or not path_input.strip():
            if not directories:
                print("[yellow]⚠️ You must specify at least one directory.[/yellow]")
                continue
            break

        resolved_path = Path(path_input.strip()).expanduser().resolve()

        if not resolved_path.exists():
            print(
                f"[yellow]⚠️ Warning: '{resolved_path}' does not currently exist, but added anyway.[/yellow]"
            )

        path_str = str(resolved_path)
        if path_str in directories:
            print("[yellow]⚠️ Directory already in list.[/yellow]")
            continue

        directories.append(path_str)
        print(f"[green]✔ Added:[/green] {path_str}")

    return directories


def prompt_passphrase() -> str:
    """Prompt for a Borg encryption passphrase with confirmation."""
    print("\n[bold cyan]Repository Encryption[/bold cyan]")
    print("[dim]This passphrase protects your Borg repository key.[/dim]\n")

    while True:
        passphrase = questionary.password("Enter encryption passphrase:").ask()
        if not passphrase or not passphrase.strip():
            print("[red]✖ Passphrase cannot be empty.[/red]")
            continue

        confirm = questionary.password("Confirm encryption passphrase:").ask()
        if passphrase != confirm:
            print("[red]✖ Passphrases do not match. Please try again.[/red]")
            continue

        return passphrase.strip()


def prompt_borgmatic_config_overwrite() -> bool:
    path = constants.BORGMATIC_CONFIG_PATH

    if path.exists():
        print(f"[yellow]Found existing config file at:[/yellow] {path}\n")

        existing_yaml = path.read_text()
        syntax_preview = Syntax(
            existing_yaml, "yaml", theme="ansi_dark", line_numbers=True
        )
        print(Panel(syntax_preview, title="Current config.yaml", border_style="yellow"))
        return questionary.confirm(
            "Do you want to overwrite this existing configuration?",
            default=True,
        ).ask()
    return True


def run_borgmatic_config_update(config: BorgmaticConfig, overwrite: bool) -> None:
    """Check for existing config, print/backup if found, and write new config."""
    path = constants.BORGMATIC_CONFIG_PATH

    # ensure target directory exists with restricted access (0700)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)

    # create backup copy
    if overwrite and path.exists():
        backup_path = path.with_name("config.yaml.back")
        shutil.copy(path, backup_path)
        print(f"[green]✔ Old configuration backed up to:[/green] {backup_path}")

    # write new configuration
    utils.config.save_config(path, config)

    # restrict permissions
    path.chmod(0o600)

    print(f"[bold green]✔ Saved new configuration to:[/bold green] {path}")
