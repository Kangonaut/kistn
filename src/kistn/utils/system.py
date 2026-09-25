import shutil
import subprocess

from packaging.version import parse as parse_version

from . import console


def check_system_dependency(
    command: str,
    min_version: str | None = None,
    version_flag: str = "--version",
) -> bool:
    # 1. check if the command exists
    if shutil.which(command) is None:
        console.error(
            f"Missing dependency: [bold cyan]{command}[/bold cyan] is not installed or not in your PATH."
        )
        return False

    # 2. if a minimum version is required, check it
    if min_version:
        try:
            result = subprocess.run(
                [command, version_flag], capture_output=True, text=True, check=True
            )
            current_version_str = result.stdout.strip()

            if parse_version(current_version_str) < parse_version(min_version):
                console.error(
                    f"[bold cyan]{command}[/bold cyan] is outdated. "
                    f"Minimum required is [yellow]{min_version}[/yellow], "
                    f"but found [red]{current_version_str}[/red]."
                )
                return False

        except subprocess.CalledProcessError:
            console.warn(
                f"Found [cyan]{command}[/cyan], but could not determine its version."
            )
            return True

    return True


def send_notification(
    title: str,
    message: str,
    urgency: str = "normal",  # low, normal, critical
    icon: str | None = None,
) -> None:
    """Sends a desktop notification using notify-send if available."""
    if not shutil.which("notify-send"):
        return  # Silently ignore if notify-send is missing

    cmd = ["notify-send", "--app-name=Backup CLI", "-u", urgency, title, message]
    if icon:
        cmd.extend(["-i", icon])

    try:
        subprocess.run(cmd, check=False)
    except Exception:
        pass
