from dataclasses import dataclass


@dataclass
class StorageBoxConfig:
    nickname: str
    hostname: str
    port: int
    username: str
