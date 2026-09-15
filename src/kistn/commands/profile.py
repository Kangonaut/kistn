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
            utils.console.hint("How often do you want to run this backup?")
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

    profiles[p.name] = p
    profile.save(profiles)

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

    del profiles[name]  # type: ignore

    profile.save(profiles)
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
        exclude_patterns=consts.BORGMATIC_EXCLUDE_PATH,
        repositories=repositories,
        encryption_passphrase=encryption_passphrase,  # type: ignore
        compression=compression,  # type: ignore
        archive_name_format=f"kistn.{p.name}-{{hostname}}-{{now}}",
        keep_daily=keep_daily,  # type: ignore
        keep_weekly=keep_weekly,  # type: ignore
        keep_monthly=keep_monthly,  # type: ignore
        checks=checks,
    )

    config.save(p.name)
    path = config.get_path(p.name).resolve()

    utils.console.success(
        f"The Borgmatic config has been saved: [link={path.as_uri()}][cyan]{path}[/cyan][/link]"
    )
    utils.console.success(
        "Setup complete! Run the following command to start the first backup:"
    )
    utils.console.print_command(f"kistn profile backup {p.name}")
