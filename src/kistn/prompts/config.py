import shutil
from pathlib import Path

import questionary
from rich.panel import Panel
from rich.syntax import Syntax

from kistn import utils
from kistn.models import BorgmaticConfig


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
