from pathlib import Path

import questionary
import typer
from questionary import question
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from typer.params import Argument, Option

from kistn import consts, profile, remote, utils, validators
from kistn.borgmatic import (BorgmaticCheck, BorgmaticConfig,
                             BorgmaticRepository)
from kistn.profile import Profile, ProfileState
from kistn.remote import Remote

app = typer.Typer()


def ensure_state(p: Profile, state: ProfileState):
    if p.state >= state:
        return

    if p.state == ProfileState.CREATED:
        utils.console.abort_with_error(
            f"Profile needs to be configured first. Please run: [cyan]`kistn profile configure {p.name}`[/cyan]"
        )
    if p.state == ProfileState.CONFIGURED:
        utils.console.abort_with_error(
            f"Profile needs to be initialized first. Please run: [cyan]`kistn profile init {p.name}`[/cyan]"
        )
    if p.state == ProfileState.INITIALIZED:
        utils.console.abort_with_error(
            f"You need to export the encryption key first. Please run: [cyan]`kistn profile key {p.name}`[/cyan]"
        )


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


def run_create(
    name: str | None = None,
    description: str | None = None,
    frequency: int | None = None,
    automatic: bool | None = None,
) -> Profile:
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
        state=ProfileState.CREATED,
    )
    p.save()

    utils.console.success(f"Profile added! Total count: {len(profiles)}")

    return p


def run_configure(
    p: Profile,
    selected_remote_names: list[str] = [],
    source_directories: list[Path] = [],
    encryption_passphrase: str | None = None,
    compression: str | None = None,
    keep_daily: int | None = None,
    keep_weekly: int | None = None,
    keep_monthly: int | None = None,
):
    remotes = remote.load()
    remote_names = sorted(list(remotes.keys()))

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

    utils.console.info(
        f"The Borgmatic config has been saved: [link={path.as_uri()}][cyan]{path}[/cyan][/link]"
    )

    p.state = ProfileState.CONFIGURED
    p.save()
    utils.console.success("Setup complete!")


def run_init(p: Profile):
    with utils.console.status("Initializing profile..."):
        utils.borgmatic.init_repo(p.borgmatic_config_file)

    p.state = ProfileState.INITIALIZED
    p.save()
    utils.console.success("Profile initiated!")


def run_key(p: Profile):
    paper_key = utils.borgmatic.export_paper_key(p.borgmatic_config_file)

    key_file = Path.cwd() / f"kistn.{p.name}-paper-key.txt"
    key_file.touch(mode=0o600)
    key_file.write_text(paper_key)

    p.state = ProfileState.READY
    p.save()

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

    utils.console.print(
        Panel(
            f"[bold white]{paper_key}[/bold white]",
            title="[bold yellow]📄 Emergency Paper Key[/bold yellow]",
            border_style="yellow",
            expand=True,
        )
    )


@app.command()
def wizard(
    name: str = Argument(
        callback=validators.validate_typer_param(validators.validate_name, "name"),
    ),
):
    p = profile.get_profile_by_name(name)

    # STEP 1: create
    if p is None or True:
        utils.console.print_step_header(
            1,
            "CREATE BACKUP PROFILE",
            "Define the name, schedule, and basic details for your new backup.",
        )
        p = run_create(name)
    else:
        utils.console.info("Skipping already completed steps.")

        if p.state == ProfileState.READY:
            utils.console.info("Nothing left to do. Profile is ready to use.")

    # STEP 2: configure
    if p.state < ProfileState.CONFIGURED:
        utils.console.print_step_header(
            2,
            "CONFIGURE BACKUP AND REMOTE HOSTS",
            "Select your source directories, destination hosts, and encryption settings.",
        )
        run_configure(p)

    # STEP 3: initialize
    if p.state < ProfileState.INITIALIZED:
        utils.console.print_step_header(
            3,
            "INITIALIZE REMOTE REPOSITORIES",
            "Prepare and initialize the secure repositories on your remote destinations.",
        )
        run_init(p)

    # STEP 4: export encryption key
    if p.state < ProfileState.READY:
        utils.console.print_step_header(
            4,
            "EXPORT ENCRYPTION KEY",
            "Generate your emergency paper key to ensure you can always recover your data.",
        )
        run_key(p)


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
    run_create(
        name=name,
        description=description,
        frequency=frequency,
        automatic=automatic,
    )


@app.command()
def configure(
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

    p = profile.get_profile_by_name_ensured(name)
    ensure_state(p, ProfileState.CREATED)
    run_configure(
        p,
        selected_remote_names,
        source_directories,
        encryption_passphrase,
        compression,
        keep_daily,
        keep_weekly,
        keep_monthly,
    )


@app.command()
def init(
    name: str = Argument(),
):
    p = profile.get_profile_by_name_ensured(name)
    ensure_state(p, ProfileState.CONFIGURED)
    run_init(p)


@app.command()
def key(
    name: str = Argument(),
):
    p = profile.get_profile_by_name_ensured(name)
    ensure_state(p, ProfileState.INITIALIZED)
    run_key(p)

    p.state = ProfileState.READY
    p.save()


@app.command("list")
def query():
    profiles = profile.load()
    profiles_list = list(profiles.values())
    profiles_list.sort(key=lambda p: p.name)

    profile.print_profiles(profiles_list)
    utils.console.print(f"\nTotal: {len(profiles)}")


@app.command()
def delete(
    name: str = Argument(),
):
    profiles = profile.load()
    p = profile.get_profile_by_name_ensured(name, profiles)
    p.delete()
    utils.console.success(f"Profile removed! Total count: {len(profiles)}")
