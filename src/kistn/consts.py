from pathlib import Path

import typer
from platformdirs import PlatformDirs

dirs = PlatformDirs(appname="kistn")

CONFIG_DIR = dirs.user_config_path
CONFIG_FILE = CONFIG_DIR / "config.yaml"

CACHE_DIR = dirs.user_cache_path
PROFILES_CACHE_FILE = CACHE_DIR / "profiles.yaml"
REMOTES_CACHE_FILE = CACHE_DIR / "remotes.yaml"

SSH_DIR = Path.home() / ".ssh"
SSH_CONFIG_FILE = SSH_DIR / "config"
SSH_KNOWN_HOSTS_FILE = SSH_DIR / "known_hosts"
SSH_CONFIGS_DIR = SSH_DIR / "conf.d"
SSH_SERVER_ALIVE_INTERVAL = 60
SSH_SERVER_ALIVE_COUNT_MAX = 240
SSH_IPQOS = "none"
SSH_KEY_TYPE = "ed25519"
SSH_DEFAULT_TRUSTED_FINGERPRINTS = [
    # source: https://docs.hetzner.com/de/storage/storage-box/general/#ssh-host-keys
    "XqONwb1S0zuj5A1CDxpOSuD2hnAArV1A3wKY7Z3sdgM",
    "EMlfI8GsRIfpVkoW1H2u0zYVpFGKkIMKHFZIRkf2ioI",
    "RWkLouD9tfTwdboJOzjiWo5njZI59Hcta82ttAWxDA0",
    "oDHZqKXnoMtgvPBjjC57pcuFez28roaEuFcfwyg8O5c",
]

BORGMATIC_CONFIG_DIR = CONFIG_DIR / "borgmatic.d"
BORGMATIC_EXCLUDE_PATTERNS = [
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
