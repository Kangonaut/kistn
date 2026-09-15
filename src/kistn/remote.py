from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from kistn import consts, utils
from kistn.borgmatic import BorgmaticRepository

console = Console()


class Remote(BaseModel):
    name: str
    description: str
    hostname: str
    port: int = Field(default=23, ge=1, le=65535)
    username: str

    @property
    def ssh_name(self) -> str:
        return f"kistn.{self.name}"

    @property
    def ssh_key_file(self) -> Path:
        return consts.SSH_DIR / f"kistn.{self.name}"

    @property
    def public_ssh_key_file(self) -> Path:
        return consts.SSH_DIR / f"kistn.{self.name}.pub"

    @property
    def ssh_config_file(self) -> Path:
        return consts.SSH_CONFIGS_DIR / f"kistn.{self.name}"

    def write_ssh_config(self):
        content = (
            f"Host {self.ssh_name}\n"
            f"  # {self.description}\n"
            f"  HostName {self.hostname}\n"
            f"  Port {self.port}\n"
            f"  User {self.username}\n"
            f"  IdentityFile {self.ssh_key_file}\n"
            f"  ServerAliveInterval {consts.SSH_SERVER_ALIVE_INTERVAL}\n"
            f"  ServerAliveCountMax {consts.SSH_SERVER_ALIVE_COUNT_MAX}\n"
            f"  IPQoS {consts.SSH_IPQOS}\n"
        )
        self.ssh_config_file.write_text(content)

    def create_ssh_key(self, passphrase: str):
        utils.ssh.gen_key(self.ssh_key_file, passphrase)

    def upload_ssh_key(self, passphrase: str):
        utils.ssh.upload_key(self.ssh_key_file, self.ssh_name, passphrase)

    def remove_files(self):
        self.ssh_key_file.unlink(missing_ok=True)
        self.public_ssh_key_file.unlink(missing_ok=True)
        self.ssh_config_file.unlink(missing_ok=True)

    def to_borgmatic_repo(self) -> BorgmaticRepository:
        return BorgmaticRepository(
            path=f"ssh://{self.ssh_name}/./kistn",
            label=self.name,
        )


def load(path: Path = consts.REMOTES_CACHE_FILE) -> dict[str, Remote]:
    if not path.exists():
        return dict()
    remotes = utils.io.load_pydantic_list_from_yaml(Remote, path)
    return {r.name: r for r in remotes}


def save(remotes: dict[str, Remote], path: Path = consts.REMOTES_CACHE_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    utils.io.save_pydantic_list_to_yaml(list(remotes.values()), Remote, path)


def print_remotes(remotes: list[Remote]):
    if not remotes:
        console.print(
            "No remote connections found. Create a profile using [cyan]`kistn remote create`[/cyan]."
        )
        return

    table = Table(box=None)

    table.add_column("Name", style="bold green")
    table.add_column("Hostname", style="white")
    table.add_column("Port", style="white")
    table.add_column("Username", style="white")
    table.add_column("Description", style="dim")

    for remote in remotes:
        table.add_row(
            remote.name,
            f"[link=https://{remote.hostname}]{remote.hostname}[/link]",
            str(remote.port),
            remote.username,
            remote.description or "-",
        )

    console.print(table)
