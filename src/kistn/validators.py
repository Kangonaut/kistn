import re


def validate_nickname(text: str) -> bool | str:
    if not text.strip():
        return "Nickname cannot be empty."
    if not re.match(r"^[a-zA-Z0-9-_]+$", text):
        return "Invalid nickname format. Please only use: letters, digits, hyphons or underscores."
    return True


def validate_username(text: str) -> bool | str:
    text = text.strip()
    if not text:
        return "Username cannot be empty."
    if "uXXXXXX" in text:
        return "Please replace 'XXXXXX' with your actual Storage Box number."
    if not re.match(r"^[a-zA-Z0-9.-_]+$", text):
        return "Invalid username format."
    return True


def validate_hostname(text: str) -> bool | str:
    text = text.strip()
    if not text:
        return "Hostname cannot be empty."
    if "uXXXXXX" in text:
        return "Please replace 'XXXXXX' with your actual Storage Box number."
    if not re.match(r"^[a-zA-Z0-9.-]+$", text):
        return "Invalid host format."
    return True


def validate_port(text: str) -> bool | str:
    text = text.strip()
    if not text:
        return "Port number cannot be empty."

    if not text.isdigit():
        return "Port must be a valid integer."

    port_num = int(text)
    if not (1 <= port_num <= 65535):
        return "Port must be between 1 and 65535."

    return True
