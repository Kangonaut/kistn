import os
import re
import shutil
import socket
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

import yaml

from kistn.borgmatic_config import BorgmaticConfig
from kistn.storage_box_config import StorageBoxConfig

CONFIG_DIR = Path.home() / ".config" / "kistn"
CACHE_DIR = Path.home() / ".cache" / "kistn"
SSH_CONFIG = Path.home() / ".ssh" / "config"


def get_backup_profiles() -> list[str]:
    return [file.name for file in CONFIG_DIR.iterdir()]


def save_storagebox_config(config: StorageBoxConfig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w+") as file:
        yaml.dump(asdict(config), file, sort_keys=False)


def load_storagebox_config(path: Path) -> StorageBoxConfig:
    with open(path, "r") as file:
        data = yaml.safe_load(file)
        config = StorageBoxConfig(**data)
        return config


def is_host_reachable(host: str, port: int = 23, timeout: float = 2.0) -> bool:
    """Fast TCP socket check to prevent long SSH hangs when offline."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def record_last_backup(profile: str) -> None:
    path = CACHE_DIR / profile
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(int(time.time())))


def get_days_since_last_backup(profile: str) -> int | None:
    path = CACHE_DIR / profile

    if not path.exists():
        return None
    try:
        last_time = int(path.read_text().strip())
        return int((time.time() - last_time) / 86400)
    except ValueError:
        return None


def add_ssh_host_entry(
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


def generate_borgmatic_config_yaml(
    storagebox_config: StorageBoxConfig, borgmatic_config: BorgmaticConfig
) -> str:
    # add source directories
    yaml = f"source_directories:\n"
    for dir in borgmatic_config.directories:
        yaml += f"  - {dir}\n"
    yaml += "\n"

    # add exclude patterns
    yaml += (
        f"exclude_patterns:\n"
        f"  - '**/node_modules'\n"
        f"  - '**/__pycache__'\n"
        f"  - '**/.cache'\n"
        f"  - '**/.Trash*'\n"
        "\n"
    )

    # add repository
    yaml += (
        f"repositories:\n"
        f"  - path: ssh://{storagebox_config.nickname}/./{storagebox_config.backup_name}\n"
        f"    label: {storagebox_config.nickname}\n"
        "\n"
    )

    yaml += (
        f"# storage and encryption\n"
        f"encryption_passphrase: '{borgmatic_config.passphrase}'\n"
        f"compression: zstd,3\n"
        f"\n"
    )

    yaml += (
        f"# retention policy\n"
        f"keep_daily: 7\n"
        f"keep_weekly: 4\n"
        f"keep_monthly: 12\n"
        f"\n"
    )

    yaml += (
        f"# consistency checks\n"
        f"checks:\n"
        f"  - name: repository\n"
        f"  - name: archives\n"
    )

    return yaml
