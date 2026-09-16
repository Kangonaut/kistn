import questionary
import typer
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from typer.params import Argument

from kistn import consts, remote, utils, validators
from kistn.remote import Remote
from kistn.utils.console import abort_with_error

app = typer.Typer()

console = Console()


def create_ssh_key(r: Remote):
    r.create_ssh_key()
    path = r.ssh_key_file.resolve()
    utils.console.success(
        f"SSH key file created: [cyan][link={path.as_uri()}]{path}[/link][/cyan]"
    )


def create_ssh_config(r: Remote):
    r.write_ssh_config()
    path = r.ssh_config_file.resolve()
    utils.console.success(
        f"SSH config file created: [cyan][link={path.as_uri()}]{path}[/link][/cyan]"
    )


def run_ssh_key_upload(r: Remote, password: str):
    try:
        with console.status("Uploading SSH key...", spinner="dots"):
            r.upload_ssh_key(password)
    except Exception as ex:
        abort_with_error(f"SSH key upload failed. {ex}")

    utils.console.success(f"SSH key uploaded!")


def ensure_known_host(r: Remote) -> bool:
    with console.status("Checking if the remote host is known..."):
        is_known = utils.ssh.is_host_in_known_hosts(r.hostname)

    # if the host is known, done!
    if is_known:
        utils.console.success("Remote host is already known!")
        return True

    utils.console.info("Remote host is not yet known.")

    with console.status("Checking remote host's fingerprint..."):
        key_line = utils.ssh.verify_host_key(r.hostname)

    # if the host's fingerprint cannot be verified, done! (with warning message)
    if not key_line:
        utils.console.warn(
            f"The remote host's fingerprint could not be verified. If the remote host is NOT a Hetzner storage box, this is to to be expected. Either add the fingerprint to the [cyan]`trusted_ssh_fingerprints`[/cyan] in the config file or connect to the host via [cyan]`ssh {r.ssh_name}`[/cyan] to add the host's key to the known hosts. Then re-run this command to upload the SSH key."
        )
        return False

    utils.console.success("Verified host's fingerprint!")

    with console.status("Adding host to known hosts..."):
        utils.ssh.add_to_known_hosts(key_line)

    utils.console.success("Added host to known hosts.")
    return True


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
    skip_ssh_key_upload: bool = typer.Option(
        default=False,
    ),
):
    remotes = remote.load()
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

        utils.console.hint(
            "The hostname can be found in the Hetzner Console and should look something like this: uXXXXXX.your-storagebox.de (where X is a digit)."
        )
        if not hostname:
            hostname = questionary.text(
                message="Hostname:",
                validate=validators.validate_hostname,
                default="uXXXXXX.your-storagebox.de",
            ).unsafe_ask()

        utils.console.hint(
            "The SSH port can be found in the Hetzner Console. But it should almost definitely be port 23."
        )
        if not port:
            port = int(
                questionary.text(
                    message="Port:",
                    validate=validators.validate_port,
                    default="23",
                ).unsafe_ask()
            )

        utils.console.hint(
            "The username can be found in the Hetzner Console and should look something like this: uXXXXXX (where X is a digit)."
        )
        if not username:
            username = questionary.text(
                message="Username:",
                default="uXXXXXX",
                validate=validators.validate_username,
            ).unsafe_ask()
    except KeyboardInterrupt:
        utils.console.abort()

    r = Remote(
        name=name,  # type: ignore
        description=description,  # type: ignore
        hostname=hostname,  # type: ignore
        port=port,  # type: ignore
        username=username,  # type: ignore
    )

    # SSH init
    utils.ssh.init()

    # SSH key file
    create_ssh_key(r)  # type: ignore

    # SSH config file
    create_ssh_config(r)

    # add to remotes
    r.save()
    utils.console.success(f"Remote host added! Total count: {len(remotes)}")

    console.print(
        f"Please run the following command to initialize the remote host:",
    )
    utils.console.print_command(f"kistn remote init {r.name} <HOST-PASSWORD>")


@app.command("list")
@app.command()
def query():
    remotes = remote.load()
    remotes_list = list(remotes.values())
    remotes_list.sort(key=lambda r: r.name)

    remote.print_remotes(remotes_list)
    console.print(f"\nTotal: {len(remotes)}")


@app.command("delete")
@app.command()
def remove(
    name: str = Argument(),
):
    remotes = remote.load()

    if name not in remotes:
        utils.console.abort_with_message("Remote host doesn't exist.")

    r = remotes[name]
    r.delete()
    utils.console.success(f"Remote host removed! Total count: {len(remotes)}")


@app.command()
def init(
    name: str = Argument(),
    password: str = typer.Argument(),
):
    remotes = remote.load()

    if name not in remotes:
        utils.console.abort_with_message("Remote host doesn't exist.")

    r = remotes[name]

    if ensure_known_host(r):
        run_ssh_key_upload(r, password)
    else:
        utils.console.warn(
            "The SSH key has NOT been uploaded, because the host could not be verified. Ensure that the host can be verified and rerun this command to complete the initialization."
        )
