from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from typer.params import Argument

from kistn import commands, consts, profile, settings, utils
from kistn.borgmatic import BorgmaticConfig
from kistn.profile import Profile
from kistn.settings import Settings
from kistn.utils.network import is_host_reachable
from kistn.utils.system import send_notification

app = typer.Typer(
    help="📦 **kistn**: A CLI manager for Borgmatic and Hetzner Storage Box backups.",
    rich_markup_mode="markdown",
)
app.add_typer(commands.profile.app, name="profile")
app.add_typer(commands.remote.app, name="remote")

console = Console()


def setup():
    if not consts.CONFIG_FILE.exists():
        new = Settings.from_default()
        settings.save(new)


def print_profiles_status(profiles: list[Profile]):
    if not profiles:
        console.print(
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

    console.print(table)


@app.command("run")
@app.command()
def backup(
    name: str = Argument(),
):
    profiles = profile.load()

    # check if given profile exists
    if name not in profiles:
        utils.console.abort_with_error("Profile doesn't exist.")
    p = profiles[name]

    config = BorgmaticConfig.load(p.name)
    config_file = config.get_path(p.name)
    if not config_file.exists():
        utils.console.abort_with_error_and_command(
            "The backup profile is not yet configured. Please run the following command first:",
            f"kistn profile setup {p.name}",
        )

    try:
        with console.status("Checking remote hosts..."):
            utils.borgmatic.check_repositories(config_file)
            utils.console.success("Remote hosts are reachable and ready for backup.")
        utils.borgmatic.create_backup(config_file)
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


@app.command()
def status():
    profiles = profile.load()
    profile_list = list(profiles.values())
    profile_list.sort(key=lambda p: p.name)

    print_profiles_status(profile_list)


def main():
    setup()
    app()


if __name__ == "__main__":
    main()

# @app.command(name="check-shell")
# def check_shell(
#     threshold: int = 7,
#     desktop_notify: bool = typer.Option(True, help="Send a desktop popup if overdue"),
# ):
#     """Fast, silent check for .zshrc integration. Prints banner and optional popup if overdue."""
#     profiles = get_backup_profiles()
#     for profile in profiles:
#         days = get_days_since_last_backup(profile)
#         if days is not None and days > threshold:
#             msg = f"{profile}: Your last backup was {days} days ago. Run 'kistn run' to sync."
#
#             # Terminal output
#             print(f"[bold yellow]⚠️  Backup Warning:[/bold yellow] {msg}")
#
#             # Desktop notification
#             if desktop_notify:
#                 send_notification(
#                     title="Backup Overdue",
#                     message=msg,
#                     urgency="critical",
#                     icon="dialog-warning",
#                 )
#
#
#
#
# @app.command(name="test-restore")
# def test_restore():
#     """Extracts latest archive metadata or canary files to test restore capability."""
#     console.print("[blue]Testing repository extraction readiness...[/blue]")
#     result = subprocess.run(["borgmatic", "list"], capture_output=True, text=True)
#
#     if result.returncode == 0:
#         console.print(
#             "[bold green]✔ Archive index accessible and verified.[/bold green]"
#         )
#     else:
#         console.print("[bold red]✖ Failed to read archive list.[/bold red]")
#
#
# @app.command()
# def mount(mount_point: Path = typer.Argument(..., help="Empty directory to mount to")):
#     """Mount the Borg repository to a local directory for easy file browsing."""
#     # Use borgmatic mount --mount-point <mount_point>
#     pass
#
#
# @app.command()
# def restore(
#     profile: str = typer.Option(
#         None, "--profile", "-p", help="Bypass prompt and use specific profile"
#     )
# ):
#     """
#     Interactively select and restore a backup archive.
#     """
#     profiles = get_backup_profiles()
#     if not profiles:
#         console.print(
#             "[bold red]No backup profiles found. Please run `kistn setup` first.[/bold red]"
#         )
#         raise typer.Exit(code=1)
#
#     # 1. Select the profile
#     selected_profile = profile
#     if not selected_profile:
#         selected_profile = questionary.select(
#             "Select a backup profile to restore from:", choices=profiles
#         ).ask()
#
#         if not selected_profile:
#             raise typer.Exit(code=1)
#
#     config_path = CONFIG_DIR / f"{selected_profile}.yaml"
#
#     # 2. Fetch archives from Borgmatic in JSON format
#     with console.status(
#         "[blue]Fetching archives from storage box...[/blue]", spinner="dots"
#     ):
#         result = subprocess.run(
#             ["borgmatic", "--config", str(config_path), "list", "--json"],
#             capture_output=True,
#             text=True,
#         )
#
#     if result.returncode != 0:
#         console.print(
#             "[bold red]✖ Failed to connect to repository or read archives.[/bold red]"
#         )
#         console.print(result.stderr)
#         raise typer.Exit(code=1)
#
#     # 3. Parse the JSON output to build a list of choices
#     try:
#         data = json.loads(result.stdout)
#
#         # borgmatic outputs a list of repositories, each containing an 'archives' list
#         archives = []
#         for repo in data:
#             if "archives" in repo:
#                 archives.extend(repo["archives"])
#
#         if not archives:
#             console.print("[yellow]No archives found in this repository.[/yellow]")
#             raise typer.Exit(0)
#
#     except json.JSONDecodeError:
#         console.print(
#             "[bold red]✖ Failed to parse JSON output from Borgmatic.[/bold red]"
#         )
#         raise typer.Exit(code=1)
#
#     # Sort archives by start time (newest first) for better UX
#     archives.sort(key=lambda x: x.get("start", ""), reverse=True)
#
#     # Map nicely formatted strings to their actual archive names
#     choices = {
#         f"{a['archive']} ({a.get('start', 'Unknown Date')})": a["archive"]
#         for a in archives
#     }
#
#     # 4. Prompt the user to select an archive
#     selected_choice = questionary.select(
#         "Select the archive you want to restore:", choices=list(choices.keys())
#     ).ask()
#
#     if not selected_choice:
#         raise typer.Exit(code=1)
#
#     target_archive = choices[selected_choice]
#
#     # 5. Prompt for a safe destination directory
#     dest_str = questionary.path(
#         "Where should the files be extracted to?",
#         default=str(Path.cwd() / "restore_output"),
#         only_directories=True,
#     ).ask()
#
#     if not dest_str:
#         raise typer.Exit(code=1)
#
#     dest_path = Path(dest_str)
#     dest_path.mkdir(parents=True, exist_ok=True)
#
#     # 6. Execute the extraction
#     console.print(
#         f"\n[blue]Restoring [bold]{target_archive}[/bold] into [bold]{dest_path}[/bold]...[/blue]"
#     )
#
#     extract_result = subprocess.run(
#         [
#             "borgmatic",
#             "--config",
#             str(config_path),
#             "extract",
#             "--archive",
#             target_archive,
#             "--destination",
#             str(dest_path),
#             "--verbosity",
#             "1",
#             "--progress",
#         ]
#     )
#
#     if extract_result.returncode == 0:
#         console.print("\n[bold green]✔ Restore completed successfully![/bold green]")
#         send_notification(
#             title="Restore Successful",
#             message=f"Archive {target_archive} restored to {dest_path.name}",
#             urgency="normal",
#             icon="emblem-default",
#         )
#     else:
#         console.print("\n[bold red]✖ Restore failed. Check logs above.[/bold red]")
