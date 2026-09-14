import socket


def is_host_reachable(host: str, port: int = 23, timeout: float = 2.0) -> bool:
    """Fast TCP socket check to prevent long SSH hangs when offline."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
