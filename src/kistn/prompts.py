import questionary
import typer
from rich import print
from rich.panel import Panel

from kistn.storage_box_config import StorageBoxConfig
from kistn.validators import (validate_hostname, validate_nickname,
                              validate_port, validate_username)

SSH_KEY_GEN_HELP = Panel(
    "You are going to be asked for a passphrase for the SSH key. If you enter a passphrase, you'll be asked to type it in every time you use it to authenticate yourself in an SSH connection. This is more secure, but also more cumbersome. So pick your poision.\n",
    title="[bold blue]Interactive Steps Required[/bold blue]",
    border_style="white",
    expand=False,
)

SSH_KEY_UPLOAD_HELP = Panel(
    "SSH will now initiate a first-time connection to Hetzner:\n\n"
    "1. [bold white]Accept Fingerprint:[/bold white] Type [cyan]yes[/cyan] when prompted to trust the host key.\n"
    "[dim]  💡 NOTE: If you want to check the authenticity of the server, you can check if the fingerprint matches one of the fingerprints mentioned in the [cyan][link=https://docs.hetzner.com/storage/storage-box/general#ssh-host-keys]official Hetzner documentation[/link][/cyan].[/dim]\n\n"
    "2. [bold white]Enter Password:[/bold white] Type your Hetzner Storage Box password when asked.\n",
    title="[bold blue]Interactive Steps Required[/bold blue]",
    border_style="white",
    expand=False,
)
