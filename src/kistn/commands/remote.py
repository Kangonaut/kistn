import questionary
import typer
from questionary import question
from rich.console import Console
from typer.params import Argument

from kistn import utils, validators
from kistn.models import Remote

app = typer.Typer()

console = Console()


@app.command("add")
@app.command()
def create(
    name: str | None = typer.Option(
        default=None,
        callback=validators.validate_typer_param(validators.validate_name, "name"),
    ),
    description: str | None = typer.Option(default=None),
    hostname: str | None = typer.Option(
        default=None,
        callback=validators.validate_typer_param(
            validators.validate_hostname, "hostname"
        ),
    ),
    port: int | None = typer.Option(
        default=None,
        callback=validators.validate_typer_param(validators.validate_port, "port"),
    ),
    username: str | None = typer.Option(
        default=None,
        callback=validators.validate_typer_param(
            validators.validate_username, "username"
        ),
    ),
):
    remotes = utils.remote.load()
    remote_names = set(remotes.keys())

    try:
        if not name:
            name = questionary.text(
                message="Name:",
                validate=validators.validate_unique_name(remote_names),
            ).unsafe_ask()
        elif name in remote_names:
            utils.console.abort_with_error("Name is already in use.")

        if not description:
            description = questionary.text(message="Description:").unsafe_ask()

        if not hostname:
            hostname = questionary.text(
                message="Hostname:", validate=validators.validate_hostname
            ).unsafe_ask()

        if not port:
            port = int(
                questionary.text(
                    message="Port:", validate=validators.validate_port
                ).unsafe_ask()
            )

        if not username:
            username = questionary.text(
                message="Username:",
                validate=validators.validate_username,
            ).unsafe_ask()
    except KeyboardInterrupt:
        utils.console.abort()

    remote = Remote(
        name=name,  # type: ignore
        description=description,  # type: ignore
        hostname=hostname,  # type: ignore
        port=port,  # type: ignore
        username=username,  # type: ignore
    )

    remotes[remote.name] = remote
    utils.remote.save(remotes)

    utils.console.info(f"Remote connection added! Total count: {len(remotes)}")


@app.command("list")
@app.command()
def query():
    remotes = utils.remote.load()
    remotes_list = list(remotes.values())
    remotes_list.sort(key=lambda r: r.name)

    utils.console.print_remotes(remotes_list)
    console.print(f"Total: {len(remotes)}")


@app.command("delete")
@app.command()
def remove(
    name: str | None = Argument(
        callback=validators.validate_typer_param(validators.validate_name, "name"),
    ),
):
    remotes = utils.remote.load()

    try:
        if not name:
            name = questionary.text(
                message="Name:",
                validate=validators.validate_name,
            ).unsafe_ask()

    except KeyboardInterrupt:
        utils.console.abort()

    if name not in remotes:
        utils.console.abort_with_message("Remote connection doesn't exist.")

    del remotes[name]  # type: ignore

    utils.remote.save(remotes)
    utils.console.info(f"Remote connection removed! Total count: {len(remotes)}")
