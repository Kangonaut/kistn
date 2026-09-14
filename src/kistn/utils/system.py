import shutil
import subprocess

SYSTEM_DEPS: list[str] = [
    "borg",
    "borgmatic",
    "ssh",
    "ssh-keygen",
    "ssh-copy-id",
]


def check_system_dependencies() -> list[str]:
    """
    Checks if all required dependencies are installed.

    Returns a list of missing package names.
    """
    missing = []

    for package in SYSTEM_DEPS:
        if shutil.which(package) is None:
            missing.append(package)

    return missing


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
