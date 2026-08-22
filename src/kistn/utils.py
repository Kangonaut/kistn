import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

CACHE_FILE = Path.home() / ".cache" / "backup_cli_last_run"
SSH_CONFIG = Path.home() / ".ssh" / "config"


def is_host_reachable(host: str, port: int = 23, timeout: float = 2.0) -> bool:
    """Fast TCP socket check to prevent long SSH hangs when offline."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def record_last_backup() -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(str(int(time.time())))


def get_days_since_last_backup() -> int | None:
    if not CACHE_FILE.exists():
        return None
    try:
        last_time = int(CACHE_FILE.read_text().strip())
        return int((time.time() - last_time) / 86400)
    except ValueError:
        return None


def ensure_ssh_host_entry(
    nickname: str, hostname: str, port: int, user: str, key_path: str
) -> bool:
    """Idempotently adds or updates host configuration in ~/.ssh/config.

    Returns True if an existing entry was updated, False if a new entry was appended.
    """
    SSH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SSH_CONFIG.touch(mode=0o600, exist_ok=True)

    content = SSH_CONFIG.read_text()

    # formatted SSH config block
    snippet = (
        f"Host {nickname}\n"
        f"  HostName {hostname}\n"
        f"  Port {port}\n"
        f"  User {user}\n"
        f"  IdentityFile {key_path}\n"
        f"  ServerAliveInterval 60\n"
        f"  ServerAliveCountMax 240\n"
        f"  IPQoS none"
    )

    # regex matches 'Host nickname' up to the next 'Host ' entry or end of file
    pattern = re.compile(
        rf"^Host\s+{re.escape(nickname)}\b.*?(?=\nHost\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    if pattern.search(content):
        # replace existing host block
        updated_content = pattern.sub(snippet, content)
        was_updated = True
    else:
        # append new host block with proper spacing
        prefix = "\n\n" if content.strip() else ""
        updated_content = content.rstrip() + prefix + snippet + "\n"
        was_updated = False

    SSH_CONFIG.write_text(updated_content)
    return was_updated


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
