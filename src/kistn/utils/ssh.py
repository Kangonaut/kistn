import re
import subprocess
from pathlib import Path

from kistn import constants


def gen_key(path: Path) -> None:
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(path)], check=True)


def upload_key(path: Path, name: str) -> None:
    subprocess.run(["ssh-copy-id", "-s", "-i", f"{path}.pub", name])


def add_host_entry(
    nickname: str, hostname: str, port: int, user: str, key_path: str
) -> bool:
    """Idempotently adds or updates host configuration in ~/.ssh/config.

    Returns True if an existing entry was updated, False if a new entry was appended.
    """
    constants.SSH_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    constants.SSH_CONFIG_PATH.touch(mode=0o600, exist_ok=True)

    content = constants.SSH_CONFIG_PATH.read_text()

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

    constants.SSH_CONFIG_PATH.write_text(updated_content)
    return was_updated
