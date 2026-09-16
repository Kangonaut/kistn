import questionary
import typer
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from typer.params import Argument

from kistn import consts, remote, utils, validators
from kistn.remote import Remote, RemoteState
from kistn.utils.console import abort_with_error

app = typer.Typer()


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
        with utils.console.status("Uploading SSH key...", spinner="dots"):
            r.upload_ssh_key(password)
    except Exception as ex:
        abort_with_error(f"SSH key upload failed. {ex}")

    utils.console.success(f"SSH key uploaded!")


def ensure_known_host(r: Remote) -> bool:
    with utils.console.status("Checking if the remote host is known..."):
        is_known = utils.ssh.is_host_in_known_hosts(r.hostname)

    # if the host is known, done!
    if is_known:
        utils.console.success("Remote host is already known!")
        return True

    utils.console.info("Remote host is not yet known.")

    with utils.console.status("Checking remote host's fingerprint..."):
        key_line = utils.ssh.verify_host_key(r.hostname)

    # if the host's fingerprint cannot be verified, done! (with warning message)
    if not key_line:
        utils.console.warn(
            f"The remote host's fingerprint could not be verified. If the remote host is NOT a Hetzner storage box, this is to to be expected. Either add the fingerprint to the [cyan]`trusted_ssh_fingerprints`[/cyan] in the config file or connect to the host via [cyan]`ssh {r.ssh_name}`[/cyan] to add the host's key to the known hosts. Then re-run this command to upload the SSH key."
        )
        return False

    utils.console.success("Verified host's fingerprint!")

    with utils.console.status("Adding host to known hosts..."):
        utils.ssh.add_to_known_hosts(key_line)

    utils.console.success("Added host to known hosts.")
    return True


def run_init(
    r: Remote,
    password: str | None = None,
):
    try:
        if not password:
            password = questionary.password("Password:").unsafe_ask()
    except KeyboardInterrupt:
        utils.console.abort()

    if not ensure_known_host(r):
        utils.console.abort_with_error(
            "The SSH key has NOT been uploaded, because the host could not be verified. Ensure that the host can be verified and rerun this command to complete the initialization."
        )

    run_ssh_key_upload(r, password)  # type: ignore

    r.state = RemoteState.READY
    r.save()


def run_create(
    name: str | None = None,
    description: str | None = None,
    hostname: str | None = None,
    port: int | None = None,
    username: str | None = None,
) -> Remote:
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

    return r


@app.command()
def wizard(
    name: str = Argument(
        callback=validators.validate_typer_param(validators.validate_name, "name"),
    ),
):
    r = remote.get_remote_by_name(name)

    # STEP 1: create
    if r is None:
        utils.console.print_step_header(
            1,
            "CREATE REMOTE HOST",
            "Define connection details like the hostname and username, and generate the necessary SSH keys.",
        )
        r = run_create(name)
    else:
        utils.console.info("Skipping already completed steps.")

        if r.state == RemoteState.READY:
            utils.console.info("Nothing left to do. Profile is ready to use.")

    # STEP 2: initialize
    if r.state < RemoteState.READY:
        utils.console.print_step_header(
            2,
            "INITIALIZE REMOTE HOST",
            "Verify the remote host's identity and upload your SSH key to enable secure, passwordless access.",
        )
        run_init(r)


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
    run_create(name, description, hostname, port, username)


@app.command()
def init(
    name: str = Argument(),
    password: str | None = typer.Argument(None),
):

    r = remote.get_remote_by_name_ensured(name)
    run_init(r, password)


@app.command("list")
def query():
    remotes = remote.load()
    remotes_list = list(remotes.values())
    remotes_list.sort(key=lambda r: r.name)

    remote.print_remotes(remotes_list)
    utils.console.print(f"\nTotal: {len(remotes)}")


@app.command()
def delete(
    name: str = Argument(),
):
    remotes = remote.load()

    if name not in remotes:
        utils.console.abort_with_message("Remote host doesn't exist.")

    r = remotes[name]
    r.delete()
    utils.console.success(f"Remote host removed! Total count: {len(remotes)}")
