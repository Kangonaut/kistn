from dataclasses import dataclass


@dataclass
class BorgmaticConfig:
    directories: list[str]
    passphrase: str
