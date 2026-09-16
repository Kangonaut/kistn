import enum
from functools import total_ordering
from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from kistn import consts, utils
from kistn.borgmatic import BorgmaticRepository

console = Console()


@total_ordering
class RemoteState(str, enum.Enum):
    CREATED = "created"
    READY = "ready"

    def get_console_color(self) -> str:
        match self:
            case RemoteState.CREATED:
                return "bold white"
            case RemoteState.READY:
                return "bold green"

    def __repr__(self) -> str:
        color = self.get_console_color()
        return f"[{color}]{self.name}[/{color}]"

    @property
    def rank(self) -> int:
        return list(self.__class__).index(self)

    def __lt__(self, other):
        if isinstance(other, RemoteState):
            return self.rank < other.rank
        return NotImplemented


class Remote(BaseModel):
    name: str
    description: str
    hostname: str
    port: int = Field(default=23, ge=1, le=65535)
    username: str
    state: RemoteState = Field(default=RemoteState.CREATED)

    @property
    def config_file(self) -> Path:
        return consts.REMOTES_CACHE_DIR / self.name

    @classmethod
    def load(cls, path: Path):
        return utils.io.load_pydantic_from_yaml(Remote, path)

    def save(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        utils.io.save_pydantic_to_yaml(self, self.config_file)

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

    def create_ssh_key(self):
        utils.ssh.gen_key(self.ssh_key_file)

    def upload_ssh_key(self, passphrase: str):
        utils.ssh.upload_key(self.ssh_key_file, self.ssh_name, passphrase)

    def delete(self):
        self.remove_files()

    def remove_files(self):
        self.ssh_key_file.unlink(missing_ok=True)
        self.public_ssh_key_file.unlink(missing_ok=True)
        self.ssh_config_file.unlink(missing_ok=True)
        self.config_file.unlink(missing_ok=True)

    def to_borgmatic_repo(self) -> BorgmaticRepository:
        return BorgmaticRepository(
            path=f"ssh://{self.ssh_name}/./kistn",
            label=self.name,
        )


def load(state: None | RemoteState = None) -> dict[str, Remote]:
    dir = consts.REMOTES_CACHE_DIR
    if not dir.exists():
        return dict()
    remotes = [Remote.load(f) for f in dir.iterdir()]
    if state:
        remotes = filter(lambda r: r.state == state, remotes)
    return {r.name: r for r in remotes}


def save(remotes: dict[str, Remote]):
    for r in remotes.values():
        r.save()


def print_remotes(remotes: list[Remote]):
    if not remotes:
        console.print(
            "No remote connections found. Create a profile using [cyan]`kistn remote create`[/cyan]."
        )
        return

    table = Table(box=None)

    table.add_column("Name", style="bold green")
    table.add_column("State", style="white")
    table.add_column("Hostname", style="white")
    table.add_column("Port", style="white")
    table.add_column("Username", style="white")
    table.add_column("Description", style="dim")

    for remote in remotes:
        table.add_row(
            remote.name,
            remote.state,
            f"[link=https://{remote.hostname}]{remote.hostname}[/link]",
            str(remote.port),
            remote.username,
            remote.description or "-",
        )

    console.print(table)


def get_remote_by_name_ensured(
    name: str,
    remotes: dict[str, Remote] | None = None,
) -> Remote:
    return get_remote_by_name(name, remotes, check=True)  # type: ignore


def get_remote_by_name(
    name: str,
    remotes: dict[str, Remote] | None = None,
    check=True,
) -> Remote | None:
    if not remotes:
        remotes = load()
    if name not in remotes:
        if check:
            utils.console.abort_with_message("Remote host doesn't exist.")
        else:
            return None
    return remotes[name]
