import base64
import hashlib
import os
import re
import subprocess
from pathlib import Path

from kistn import consts, settings
from kistn.commands.remote import create


def gen_key(path: Path, passphrase: str) -> None:
    subprocess.run(
        ["ssh-keygen", "-t", consts.SSH_KEY_TYPE, "-N", passphrase, "-f", str(path)],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def verify_host_key(hostname: str) -> str | None:
    result = subprocess.run(
        ["ssh-keyscan", hostname],
        capture_output=True,
        text=True,
    )

    if not result.stdout:
        return None

    # check if trusted keys appear in the ouptput
    for line in result.stdout.splitlines():
        # skip empty lines or comments
        if line.startswith("#") or not line.strip():
            continue

        # format: <hostname> <key-type> <base64-key>
        tokens = line.split()
        if len(tokens) >= 3:
            b64_key = tokens[2]

            key_bytes = base64.b64decode(b64_key)
            digest = hashlib.sha256(key_bytes).digest()
            fingerprint = base64.b64encode(digest).decode("utf-8").rstrip("=")

            if fingerprint in settings.active.trusted_ssh_fingerprints:
                return line

    return None


def add_to_known_hosts(key_line: str) -> None:
    path = consts.SSH_KNOWN_HOSTS_FILE

    # avoid duplicate entries
    if path.exists() and key_line in path.read_text():
        return

    # append the key
    with path.open("a") as f:
        f.write(f"{key_line}\n")


def is_host_in_known_hosts(hostname: str) -> bool:
    result = subprocess.run(
        ["ssh-keygen", "-F", hostname],
        capture_output=True,
    )
    return result.returncode == 0


def upload_key(
    path: Path,
    ssh_name: str,
    password: str,
    check_host_key: bool = True,
) -> None:
    # inject the SSHPASS variable
    env = os.environ.copy()
    env["SSHPASS"] = password

    try:
        subprocess.run(
            [
                "sshpass",
                "-e",
                "ssh-copy-id",
                "-o",
                f"StrictHostKeyChecking={"yes" if check_host_key else "accept-new"}",
                "-s",
                "-i",
                f"{path}.pub",
                ssh_name,
            ],
            env=env,
            check=True,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "The 'sshpass' utility is not installed or not found in PATH."
        ) from e
    except subprocess.CalledProcessError as e:
        if e.returncode == 6:
            raise RuntimeError(
                f"SSH connection aborted (exit code 6): The host key for {ssh_name} is unknown. "
                "Ensure it was properly added to known_hosts before running this command."
            ) from e
        elif e.returncode == 5:
            raise RuntimeError(
                f"SSH authentication failed (exit code 5): Incorrect password for {ssh_name}."
            ) from e
        elif e.returncode == 4:
            raise RuntimeError(
                f"SSH prompt error (exit code 4): sshpass was confused by the prompt from {ssh_name}. "
                "This usually happens if the server asks for a 2FA token instead of a standard password."
            ) from e
        else:
            # re-raise with the actual error message captured from stderr
            error_msg = e.stderr.strip() if e.stderr else "Unknown error."
            raise RuntimeError(
                f"Command failed with exit code {e.returncode}: {error_msg}"
            ) from e


def create_skeleton():
    # ~/.ssh
    consts.SSH_DIR.mkdir(exist_ok=True)
    consts.SSH_DIR.chmod(mode=0o700)

    # ~/.ssh/conf.d
    consts.SSH_CONFIGS_DIR.mkdir(exist_ok=True)
    consts.SSH_CONFIGS_DIR.chmod(mode=0o700)

    # ~/.ssh/config
    consts.SSH_CONFIG_FILE.touch(mode=0o600, exist_ok=True)

    # ~/.ssh/known_hosts
    consts.SSH_KNOWN_HOSTS_FILE.touch(mode=0o600, exist_ok=True)


def add_ssh_include_directive() -> bool:
    content = consts.SSH_CONFIG_FILE.read_text()

    pattern = re.compile(rf"^Include conf\.d\/\*$", re.MULTILINE)

    if not pattern.search(content):
        content = "Include conf.d/*\n" + content
        consts.SSH_CONFIG_FILE.write_text(content)
        return True

    return False


def init():
    create_skeleton()
    add_ssh_include_directive()


def add_host_entry(
    nickname: str, hostname: str, port: int, user: str, key_path: str
) -> bool:
    """Idempotently adds or updates host configuration in ~/.ssh/config.

    Returns True if an existing entry was updated, False if a new entry was appended.
    """
    consts.SSH_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    consts.SSH_CONFIG_FILE.touch(mode=0o600, exist_ok=True)

    content = consts.SSH_CONFIG_FILE.read_text()

    # formatted SSH config block
    snippet = (
        f"Host kistn.{nickname}\n"
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

    consts.SSH_CONFIG_FILE.write_text(updated_content)
    return was_updated
