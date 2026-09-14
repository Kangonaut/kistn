from pathlib import Path
from typing import DefaultDict

import questionary
from rich.panel import Panel

from kistn import constants, utils
from kistn.models import BackupConfig, RemoteConfig


def prompt_key_generation(key_path: Path) -> bool:
    if not key_path.exists():
        gen_ssh_key = questionary.confirm(
            "Generate dedicated SSH key? (recommended)",
            default=False,
        ).ask()
        return gen_ssh_key
    return False


def prompt_key_upload() -> bool:
    return questionary.confirm(
        "Upload SSH key to Storage Box? (recommended)",
        default=False,
    ).ask()


def run_key_generation(key_path: Path):
    print("\n")
    print(Rule("[bold cyan]SSH Key Generation[/bold cyan]", align="left"))
    print(
        Panel(
            "You are going to be asked for a passphrase for the SSH key. If you enter a passphrase, you'll be asked to type it in every time you use it to authenticate yourself in an SSH connection. This is more secure, but also more cumbersome. So pick your poision.\n",
            title="[bold blue]Interactive Steps Required[/bold blue]",
            border_style="white",
            expand=False,
        )
    )
    utils.ssh.gen_key(key_path)
    print("[green]✓ SSH key generated.[/green]")


def run_config_update(config: BackupConfig, key_path: Path):
    print("\n")
    print(Rule("[bold cyan]Updating SSH Config[/bold cyan]", align="left"))
    added = utils.ssh.add_host_entry(
        nickname=config.name,
        hostname=config.remote.hostname,
        port=config.remote.port,
        user=config.remote.username,
        key_path=str(key_path),
    )
    if added:
        print(f"[green]✓ Added Host entry to {constants.SSH_CONFIG_PATH}[/green]")
    else:
        print("[blue]i SSH host entry already exists. Skipping.[/blue]")
    print()


def run_key_upload(config: BackupConfig, key_path: Path):
    print("\n")
    print(Rule("[bold cyan]Uploading SSH Key[/bold cyan]", align="left"))
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
    utils.ssh.upload_key(key_path, config.remote.name)
    print("[green]✓ SSH key uploaded.[/green]")
