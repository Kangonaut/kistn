import subprocess
from pathlib import Path

from kistn import consts


def create_skeleton():
    # ~/.config/borgmatic.d
    consts.BORGMATIC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    consts.BORGMATIC_CONFIG_DIR.chmod(mode=0o700)


def export_paper_key(config_file: Path) -> str:
    try:
        cmd = ["borgmatic", "key", "export", "--paper", "--config", str(config_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error."
        raise RuntimeError(f"Failed to export key. {e.returncode}: {error_msg}") from e


def init_repo(config_file: Path) -> bool:
    try:
        result = subprocess.run(
            [
                "borgmatic",
                "rcreate",
                "--config",
                str(config_file),
                "--encryption",
                "repokey-blake2",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr.lower():
            return False
        else:
            error_msg = e.stderr.strip() if e.stderr else "Unknown error."
            raise RuntimeError(
                f"Failed to init repository. {e.returncode}: {error_msg}"
            ) from e


def check_repositories(config_file: Path):
    try:
        subprocess.run(
            [
                "borgmatic",
                "repo-info",
                "--config",
                str(config_file),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error."
        raise RuntimeError(
            f"Repositories are not ready. Return code: {e.returncode}. Message: {error_msg}"
        ) from e


def create_backup(config_file: Path):
    try:
        result = subprocess.run(
            [
                "borgmatic",
                "create",
                "--config",
                str(config_file),
                "--verbosity",
                "1",
                "--stats",
                "--progress",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Backup failed with return code {e.returncode}.") from e
