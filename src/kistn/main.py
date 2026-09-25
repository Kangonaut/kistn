from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from typer.params import Argument

from kistn import commands, consts, profile, settings, utils
from kistn.borgmatic import BorgmaticConfig
from kistn.profile import Profile, ProfileState
from kistn.settings import Settings
from kistn.utils.network import is_host_reachable
from kistn.utils.system import check_system_dependency, send_notification

app = typer.Typer(
    help="📦 **kistn**: A CLI manager for Borgmatic and Hetzner Storage Box backups.",
    rich_markup_mode="markdown",
)
app.add_typer(commands.profile.app, name="profile")
app.add_typer(commands.remote.app, name="remote")
app.add_typer(commands.system.app, name="system")


def setup():
    if not consts.CONFIG_FILE.exists():
        new = Settings.from_default()
        settings.save(new)


def print_profiles_status(profiles: list[Profile]):
    if not profiles:
        utils.console.print(
            "No profiles found. Create a profile using [cyan]`kistn profile create`[/cyan]."
        )
        return

    table = Table(box=None)
    table.add_column("Profile", style="bold green")
    table.add_column("Last Backup", style="white")
    table.add_column("Due Date", style="white")
    # table.add_column("Repository State", style="white")

    for p in profiles:
        config_file = BorgmaticConfig.get_path(p.name)
        table.add_row(
            p.name,
            p.format_days_since_backup(),
            p.format_due_date(),
        )

    utils.console.print(table)


@app.command()
def doctor():
    with utils.console.status("Checking system dependencies..."):
        all_good = all(
            [
                utils.system.check_system_dependency(command="borg"),
                utils.system.check_system_dependency(
                    command="borgmatic", min_version="1.8.0"
                ),
                utils.system.check_system_dependency(command="ssh"),
                utils.system.check_system_dependency(command="sshpass"),
                utils.system.check_system_dependency(command="ssh-keygen"),
                utils.system.check_system_dependency(command="ssh-copy-id"),
            ]
        )

    if all_good:
        utils.console.success("All system dependencies are installed and up to date!")
    else:
        utils.console.abort_with_error(
            "Please install or upgrade the missing dependencies."
        )


@app.command()
def status():
    profiles = profile.load()
    profile_list = list(profiles.values())
    profile_list.sort(key=lambda p: p.name)

    print_profiles_status(profile_list)


@app.command()
def run(
    name: str = Argument(),
):
    p = profile.get_profile_by_name_ensured(name)

    if p.state != ProfileState.READY:
        utils.console.abort_with_error(
            "The profile must be [cyan]READY[/cyan] in order to create a backup."
        )

    try:
        with utils.console.status("Checking remote hosts..."):
            utils.borgmatic.check_repositories(p.borgmatic_config_file)
            utils.console.success("Remote hosts are reachable and ready for backup.")
        utils.borgmatic.create_backup(p.borgmatic_config_file)
    except RuntimeError as e:
        utils.system.send_notification(
            title=f"{p.name} - Backup Failed",
            message=str(e),
            urgency="critical",
            icon="dialog-error",
        )
        raise e

    send_notification(
        title=f"{p.name} - Backup Successful",
        message="Your Borgmatic backup completed successfully.",
        urgency="normal",
        icon="emblem-default",
    )
    utils.console.success("Backup completed!")

    p.last_backup = datetime.now(timezone.utc)
    p.save()


@app.command(name="check-overdue")
def check_overdue(
    notification: bool = typer.Option(
        False,
        help="Send a desktop popup if overdue.",
        is_flag=True,
    ),
    quiet: bool = typer.Option(
        False,
        is_flag=True,
    ),
):
    """Fast, silent check for .zshrc or .bashrc integration. Prints banner and optional popup if overdue."""
    due_profiles = profile.get_due()
    for p in due_profiles:
        if not quiet:
            utils.console.warn(
                f"{p.name}: Your last backup was {p.format_days_since_backup()}. Run [cyan]`kistn run {p.name}`[/cyan] to start the backup."
            )

        if notification:
            send_notification(
                title=f"{p.name} - Backup Overdue",
                message=f"Your last backup was {p.format_days_since_backup()}. Run `kistn run {p.name}` to start the backup.",
                urgency="critical",
                icon="dialog-warning",
            )


# @app.command()
# def mount(mount_point: Path = typer.Argument(..., help="Empty directory to mount to")):
#     """Mount the Borg repository to a local directory for easy file browsing."""
#     # Use borgmatic mount --mount-point <mount_point>
#     pass


def main():
    setup()
    app()


if __name__ == "__main__":
    main()
