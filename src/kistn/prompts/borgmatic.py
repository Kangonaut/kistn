import subprocess
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.panel import Panel

from kistn import constants

console = Console()


def run_repo_init(config_path: Path) -> None:
    """Initialize the Borg repository via borgmatic."""
    print("\n[bold cyan]Initializing Borg Repository[/bold cyan]")

    cmd = [
        "borgmatic",
        "rcreate",
        "--config",
        str(config_path),
        "--encryption",
        "repokey-blake2",
    ]

    with console.status("[bold green]Creating repository on Storage Box..."):
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("[bold green]✔ Repository initialized successfully![/bold green]")
    else:
        # Check if error is because repo already exists
        if "already exists" in result.stderr.lower():
            print(
                "[yellow]⚠️ Repository is already initialized. Skipping creation.[/yellow]"
            )
        else:
            print(
                Panel(
                    f"[bold red]Failed to initialize repository:[/bold red]\n\n{result.stderr}",
                    border_style="red",
                    title="Error",
                )
            )
            raise typer.Exit(code=1)


def confirm_paper_key_generation() -> bool:
    print("\n[bold cyan]Emergency Key Export[/bold cyan]")
    print(
        "[dim]If you lose access to your machine, you will need this paper key "
        "and your passphrase to recover your data.[/dim]\n"
    )
    return questionary.confirm(
        "Export paper key now? (recommended)",
        default=True,
    ).ask()


def confirm_paper_key_storage() -> bool:
    return questionary.confirm(f"Save paper key to file?", default=True).ask()


def run_paper_key_export(
    config_path: Path,
) -> str | None:
    """Export the Borg key formatted for physical paper backup."""

    cmd = ["borgmatic", "key", "export", "--paper", "--config", str(config_path)]

    with console.status("[bold green]Exporting paper key..."):
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[bold red]✖ Failed to export key:[/bold red] {result.stderr}")
        return

    paper_key = result.stdout.strip()

    print(
        Panel(
            f"[bold white]{paper_key}[/bold white]",
            title="[bold yellow]📄 Emergency Paper Key[/bold yellow]",
            border_style="yellow",
            expand=False,
        )
    )

    return paper_key


def run_paper_key_storage(output_file: Path, paper_key: str) -> None:
    output_file.write_text(paper_key)
    output_file.chmod(0o600)
    print(
        f"[green]✔ Saved paper key with permissions 0600 to:[/green] {output_file.resolve()}"
    )
