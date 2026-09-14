from pathlib import Path

import typer
from platformdirs import PlatformDirs

dirs = PlatformDirs(appname="kistn")

CONFIG_DIR = dirs.user_config_path
CACHE_DIR = dirs.user_cache_path

SSH_CONFIG_PATH = Path.home() / ".ssh" / "config"
SSH_KEY_DIR = Path.home() / ".ssh"

BORGMATIC_CONFIG_PATH = CONFIG_DIR / "borgmatic" / "config.yaml"
BORGMATIC_EXCLUDE_PATH = [
    "**/node_modules",
    "**/__pycache__",
    "**/.cache",
    "**/.Trash*",
]
BORGMATIC_COMPRESSION = "zstd,3"
BORGMATIC_KEEP_DAILY = 7
BORGMATIC_KEEP_WEEKLY = 4
BORGMATIC_KEEP_MONTHLY = 12
PAPER_KEY_PATH = Path.cwd() / "borg-paper-key.txt"
