from pathlib import Path

import typer
from platformdirs import PlatformDirs

dirs = PlatformDirs(appname="kistn")

CONFIG_DIR = dirs.user_config_path
CONFIG_FILE = CONFIG_DIR / "config.yaml"

CACHE_DIR = dirs.user_cache_path
PROFILES_CACHE_FILE = CACHE_DIR / "profiles.yaml"

SSH_DIR = Path.home() / ".ssh"
SSH_CONFIG = SSH_DIR / "config"

BORGMATIC_CONFIG_DIR = CONFIG_DIR / "borgmatic"
BORGMATIC_EXCLUDE_PATH = [
    "**/node_modules",
    "**/__pycache__",
    "**/.cache",
    "**/.Trash*",
]

BORGMATIC_DEFAULT_COMPRESSION = "zstd,3"
BORGMATIC_DEFAULT_KEEP_DAILY = 7
BORGMATIC_DEFAULT_KEEP_WEEKLY = 4
BORGMATIC_DEFAULT_KEEP_MONTHLY = 12

PAPER_KEY_PATH = Path.cwd() / "borg-paper-key.txt"
