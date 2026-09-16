import shutil
import subprocess
import sys
from pathlib import Path

import typer

from kistn import consts, utils

app = typer.Typer()


def configure_systemd_over_service():
    # determine the path to the kistn executable
    # NOTE: shutil.which handles global installs, sys.argv[0] acts as a fallback for local dev
    kistn_path = shutil.which("kistn") or Path(sys.argv[0]).resolve()

    # define the destination directories
    dir = consts.SYSTEMD_CONFIG_DIR
    try:
        dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        utils.console.abort_with_error(f"Failed to create systemd directory: {e}")

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
OnCalendar=08:00
Persistent=true

[Install]
WantedBy=timers.target
"""

    # write files and enable the timer
    try:
        with utils.console.status("Writing systemd unit files..."):
            service_file.write_text(service_content)
            timer_file.write_text(timer_content)

        with utils.console.status("Reloading systemd daemon..."):
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
            f"`systemctl` command failed: {e.stderr.decode('utf-8').strip()}"
        )
    except Exception as e:
        utils.console.abort_with_error(f"Failed to install timer: {e}")


@app.command("install-timer")
def install_timer():
    """Install and activate a systemd timer for daily background checks."""

    # verify systemd is available
    if not shutil.which("systemctl"):
        utils.console.abort_with_error(
            "[cyan]`systemctl`[/cyan] not found. This feature requires a Linux system running systemd."
        )

    configure_systemd_over_service()

    utils.console.success("Background timer installed and activated successfully!")
    utils.console.info("The overdue check will now run daily at 12:00.")
