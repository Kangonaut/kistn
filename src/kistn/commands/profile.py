from pathlib import Path

import questionary
import typer
from questionary import question
from rich.console import Console
from rich.panel import Panel
from typer.params import Argument, Option

from kistn import consts, profile, remote, utils, validators
from kistn.borgmatic import (BorgmaticCheck, BorgmaticConfig,
                             BorgmaticRepository)
from kistn.profile import Profile
from kistn.remote import Remote

app = typer.Typer()

console = Console()


def check_path(path: Path) -> bool:
    if not path.exists():
        utils.console.warn(
            "The provided path does not currently exist, but added anyway."
        )
        return True

    if path.exists() and not path.is_dir():
        utils.console.error("The provided path is not a directory.")
        return False

    return True


def prompt_source_directories() -> list[Path]:
    directories: list[Path] = []

    utils.console.hint(
        "Source directories are directories on this machine that you want backed up. Press Enter without typing to finish."
    )
    while True:
        input = questionary.text(f"Add a source directory:").unsafe_ask()
        if not input or not input.strip():
            if not directories:
                utils.console.error("You must specify at least one directory.")
                continue
            break

        path = Path(input.strip()).expanduser().resolve()
        if not check_path(path):
            continue

        if path in directories:
            utils.console.error("Directory is already in the list.")
            continue

        directories.append(path)
        utils.console.success(
            f"Added directory: [link={path}][cyan]{path}[/cyan][link]"
        )

    return directories


def prompt_passphrase() -> str:
    utils.console.hint("The encryption passphrase protects your Borg repository key.")

    while True:
        passphrase = questionary.password(
            "Encryption passphrase:",
            validate=validators.validate_encryption_passphrase,
        ).unsafe_ask()

        confirm = questionary.password("Confirm encryption passphrase:").unsafe_ask()
        if passphrase != confirm:
            utils.console.warn("Passphrases do not match. Please try again.")
            continue

        return passphrase.strip()


@app.command("add")
@app.command()
def create(
    name: str | None = Option(
        default=None,
        callback=validators.validate_typer_param(validators.validate_name, "name"),
    ),
    description: str | None = Option(
        default=None,
    ),
    frequency: int | None = Option(
        default=None,
    ),
    automatic: bool | None = Option(
        default=None,
    ),
):
    profiles = profile.load()
    profile_names = set(profiles.keys())

    try:
        if not name:
            name = questionary.text(
                message="Name:",
                validate=validators.validate_unique_name(profile_names),
            ).unsafe_ask()
        elif name in profile_names:
            utils.console.abort_with_error("This name is already in use.")

        if not description:
            description = questionary.text(
                message="Description:",
            ).unsafe_ask()

        if not frequency:
            utils.console.hint(
                "How often do you want to run this backup? A frequency of [yellow]1[/yellow] means every day. A frequency of [yellow]7[/yellow] means every week."
            )
            frequency = int(
                questionary.text(
                    message="Frequency (in days):",
                    validate=validators.validate_int,
                ).unsafe_ask()
            )

        if not automatic:
            utils.console.hint("Should the backup be performed automatically?")
            utils.console.hint("NOTE: This setting is not recommended for laptops.")
            automatic = questionary.confirm(
                message="Automatic Backup?",
                default=False,
            ).unsafe_ask()
    except KeyboardInterrupt:
        utils.console.abort()

    p = Profile(
        name=name,  # type: ignore
        description=description,  # type: ignore
        frequency=frequency,  # type: ignore
        automatic=automatic,  # type: ignore
    )
    p.save()

    utils.console.success(f"Profile added! Total count: {len(profiles)}")


@app.command("list")
@app.command()
def query():
    profiles = profile.load()
    profiles_list = list(profiles.values())
    profiles_list.sort(key=lambda p: p.name)

    profile.print_profiles(profiles_list)
    console.print(f"\nTotal: {len(profiles)}")


@app.command("delete")
@app.command()
def remove(
    name: str = Argument(),
):
    profiles: dict[str, Profile] = profile.load()
    if name not in profiles:
        utils.console.abort_with_error("Profile doesn't exist.")

    p.delete()
    utils.console.success(f"Profile removed! Total count: {len(profiles)}")


@app.command("configure")
@app.command()
def setup(
    name: str = Argument(),
    selected_remote_names: list[str] = Option([], "--remote", "-r"),
    source_directories: list[Path] = Option([], "--source", "-s"),
    encryption_passphrase: str | None = Option(
        None,
        "--passphrase",
        "-p",
        callback=validators.validate_typer_param(
            validators.validate_encryption_passphrase, "passphrase"
        ),
    ),
    compression: str | None = Option(
        None,
        "--compression",
        "-c",
        callback=validators.validate_typer_param(
            validators.validate_compression_specifier, "compression"
        ),
    ),
    keep_daily: int | None = Option(
        None,
        "--daily",
        "-d",
        callback=validators.validate_typer_param(validators.validate_int, "keep_daily"),
    ),
    keep_weekly: int | None = Option(
        None,
        "--weekly",
        "-w",
        callback=validators.validate_typer_param(validators.validate_int, "keep_daily"),
    ),
    keep_monthly: int | None = Option(
        None,
        "--monthly",
        "-m",
        callback=validators.validate_typer_param(validators.validate_int, "keep_daily"),
    ),
):

    profiles = profile.load()
    remotes = remote.load()
    remote_names = sorted(list(remotes.keys()))

    # check if given profile exists
    if name not in profiles:
        utils.console.abort_with_error("Profile doesn't exist.")
    p = profiles[name]

    # check if at least one remote is configured
    if len(remotes) == 0:
        utils.console.abort_with_error(
            "You need a remote host to store your backup at. Please set one up first using the following command:\n"
        )
        utils.console.print_command("kistn remote create")

    try:
        # remote hosts
        if len(selected_remote_names) == 0:
            utils.console.hint(
                "Choose the remote hosts that the backup should be stored at. You can choose multiple."
            )
            selected_remote_names = questionary.checkbox(
                "Select remote hosts:",
                choices=remote_names,
                validate=validators.validate_at_least_one,
            ).unsafe_ask()
        else:
            for name in selected_remote_names:
                if name not in remote_names:
                    utils.console.abort_with_error(
                        f"Remote host [cyan]{name}[/cyan] doesn't exist."
                    )
        selected_remotes = [remotes[name] for name in selected_remote_names]

        # source directories
        if len(source_directories) == 0:
            source_directories = prompt_source_directories()
        else:
            for path in source_directories:
                if not check_path(path):
                    raise typer.Exit(code=1)

        # encryption passhprase
        if not encryption_passphrase:
            encryption_passphrase = prompt_passphrase()

        # compression specifier
        utils.console.hint(
            "This specifies how the backup is compressed before sending it to a remote host. If you are unsure about this, simply pick the given default. If you want to investigate the different compression options, see [link=https://manpages.debian.org/testing/borgbackup/borg-compression.1.en.html][cyan]https://manpages.debian.org/testing/borgbackup/borg-compression.1.en.html[/cyan][/link]"
        )
        if not compression:
            compression = questionary.text(
                "Compression specifier:",
                default=consts.BORGMATIC_DEFAULT_COMPRESSION,
                validate=validators.validate_compression_specifier,
            ).unsafe_ask()

        # keep_daily
        if not keep_daily:
            keep_daily = int(
                questionary.text(
                    "Number of daily archives to keep:",
                    default=str(consts.BORGMATIC_DEFAULT_KEEP_DAILY),
                    validate=validators.validate_int,
                ).unsafe_ask()
            )

        # keep_weekly
        if not keep_weekly:
            keep_weekly = int(
                questionary.text(
                    "Number of weekly archives to keep:",
                    default=str(consts.BORGMATIC_DEFAULT_KEEP_WEEKLY),
                    validate=validators.validate_int,
                ).unsafe_ask()
            )

        # keep_monthly
        if not keep_monthly:
            keep_monthly = int(
                questionary.text(
                    "Number of monthly archives to keep:",
                    default=str(consts.BORGMATIC_DEFAULT_KEEP_MONTHLY),
                    validate=validators.validate_int,
                ).unsafe_ask()
            )
    except KeyboardInterrupt:
        utils.console.abort()

    checks = [
        BorgmaticCheck(name="repository"),
        BorgmaticCheck(name="archives"),
    ]
    repositories = [r.to_borgmatic_repo() for r in selected_remotes]  # type: ignore

    config = BorgmaticConfig(
        source_directories=source_directories,
        exclude_patterns=consts.BORGMATIC_EXCLUDE_PATTERNS,
        repositories=repositories,
        encryption_passphrase=encryption_passphrase,  # type: ignore
        compression=compression,  # type: ignore
        archive_name_format=f"kistn.{p.name}-{{hostname}}-{{now}}",
        keep_daily=keep_daily,  # type: ignore
        keep_weekly=keep_weekly,  # type: ignore
        keep_monthly=keep_monthly,  # type: ignore
        checks=checks,
    )

    utils.borgmatic.create_skeleton()
    config.save(p.name)
    path = config.get_path(p.name).resolve()

    utils.console.success(
        f"The Borgmatic config has been saved: [link={path.as_uri()}][cyan]{path}[/cyan][/link]"
    )
    utils.console.success(
        "Setup complete! Run the following command to export the paper key:"
    )
    utils.console.print_command(f"kistn profile init {p.name}")


@app.command()
def init(
    name: str = Argument(),
):
    profiles = profile.load()

    # check if given profile exists
    if name not in profiles:
        utils.console.abort_with_error("Profile doesn't exist.")
    p = profiles[name]

    config_file = BorgmaticConfig.get_path(p.name)
    if not config_file.exists():
        utils.console.abort_with_error_and_command(
            "The backup profile is not yet configured. Please run the following command first:",
            f"kistn profile setup {p.name}",
        )

    utils.borgmatic.init_repo(config_file)
    utils.console.success("Profile initiated!")


@app.command()
def key(
    name: str = Argument(),
):
    profiles = profile.load()

    # check if given profile exists
    if name not in profiles:
        utils.console.abort_with_error("Profile doesn't exist.")
    p = profiles[name]

    config_file = BorgmaticConfig.get_path(p.name)
    if not config_file.exists():
        utils.console.abort_with_error_and_command(
            "The backup profile is not yet configured. Please run the following command first:",
            f"kistn profile setup {p.name}",
        )

    paper_key = utils.borgmatic.export_paper_key(config_file)

    key_file = Path.cwd() / f"kistn.{p.name}-paper-key.txt"
    key_file.touch(mode=0o600)
    key_file.write_text(paper_key)

    utils.console.hint(
        "Why do we need a paper key? The passphrase that you entered when setting up the backup profile isn't actually used to encrypt your backed up data. Instead a much more complex, random encryption key is generated and stored on your machine for encryption. The passphrase is only used to unlock that key. The problem is that when your machine is lost, the hard-drive is wiped, etc. you cannot access that key anymore. This is where the paper key comes in. It is a human-readable representation of the actual encryption key."
    )
    utils.console.hint(
        "In the case that you have connected the backup profile with multiple remote host's, there is a key for every such host. The keys are stored together in the .txt file. You can keep them together."
    )
    utils.console.important(
        "The paper key allows you to decrypt your data in case you loose the data on this machine. Thus, you need to keep it safe! Please print out the key and store it at a secure location. After you have printed the key, please permanently delete the .txt file."
    )

    utils.console.success(
        f"The paper key was saved at: {utils.console.format_path(key_file)}"
    )

    console.print(
        Panel(
            f"[bold white]{paper_key}[/bold white]",
            title="[bold yellow]📄 Emergency Paper Key[/bold yellow]",
            border_style="yellow",
            expand=True,
        )
    )
