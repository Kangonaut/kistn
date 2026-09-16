import shutil
import subprocess
import sys
from pathlib import Path

from packaging.version import parse as parse_version

from kistn import consts

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


def configure_systemd_over_service():
    # determine the path to the kistn executable
    # NOTE: shutil.which handles global installs, sys.argv[0] acts as a fallback for local dev
    kistn_path = shutil.which("kistn") or Path(sys.argv[0]).resolve()

    # define the destination directories
    dir = consts.SYSTEMD_CONFIG_DIR
    try:
        dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        console.abort_with_error(f"Failed to create systemd directory: {e}")

    service_file = dir / "kistn-overdue.service"
    timer_file = dir / "kistn-overdue.timer"

    # 4. Generate file contents
    service_content = f"""[Unit]
Description=Check for overdue kistn backups

[Service]
Type=oneshot
ExecStart={kistn_path} check-overdue --notification --quiet
"""

    timer_content = """[Unit]
Description=Daily timer for kistn overdue backup check

[Timer]
OnCalendar=06:00
Persistent=true

[Install]
WantedBy=timers.target
"""

    # write files and enable the timer
    try:
        with console.status("Writing systemd unit files..."):
            service_file.write_text(service_content)
            timer_file.write_text(timer_content)

        with console.status("Reloading systemd daemon..."):
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
            )

        with utils.console.status("Enabling and starting timer..."):
            subprocess.run(
                ["systemctl", "--user", "enable", "--now", "kistn-overdue.timer"],
                check=True,
                capture_output=True,
            )

    except subprocess.CalledProcessError as e:
        utils.console.abort_with_error(
            f"Systemctl command failed: {e.stderr.decode('utf-8').strip()}"
        )
    except Exception as e:
        utils.console.abort_with_error(f"Failed to install timer: {e}")
