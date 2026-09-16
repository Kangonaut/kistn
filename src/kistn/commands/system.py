import shutil
import subprocess
import sys
from pathlib import Path

import typer

from kistn import consts, utils

app = typer.Typer()


def check_systemd_availability():
    if not shutil.which("systemctl"):
        utils.console.abort_with_error(
            "[cyan]`systemctl`[/cyan] not found. This feature requires a Linux system running systemd."
        )


def install_systemd_overdue_service():
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


def uninstall_systemd_overdue_service():
    dir = consts.SYSTEMD_CONFIG_DIR
    service_file = dir / "kistn-overdue.service"
    timer_file = dir / "kistn-overdue.timer"

    try:
        with utils.console.status("Stopping and disabling timer..."):
            # We set check=False here because if the timer is already stopped
            # or deleted, we don't want the command to crash. We just want it gone.
            subprocess.run(
                ["systemctl", "--user", "stop", "kistn-overdue.timer"],
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "disable", "kistn-overdue.timer"],
                capture_output=True,
            )

        with utils.console.status("Removing systemd unit files..."):
            # missing_ok=True prevents crashes if the files were already deleted manually
            service_file.unlink(missing_ok=True)
            timer_file.unlink(missing_ok=True)

        with utils.console.status("Reloading systemd daemon..."):
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
            )

    except Exception as e:
        utils.console.abort_with_error(f"Failed to uninstall timer: {e}")


@app.command("install-timer")
def install_timer():
    """Install and activate a systemd timer for daily background checks."""

    check_systemd_availability()
    install_systemd_overdue_service()

    utils.console.success("Background timer installed and activated successfully!")
    utils.console.info("The overdue check will now run daily at 12:00.")


@app.command("uninstall-timer")
def uninstall_timer():
    """Remove and disable the background overdue check timer."""

    check_systemd_availability()
    uninstall_systemd_overdue_service()

    utils.console.success("Background timer successfully removed!")
    utils.console.info("The overdue check will no longer run automatically.")
