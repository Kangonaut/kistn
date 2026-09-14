import re

from kistn import utils


def validate_filename(text: str) -> bool | str:
    if not text.strip():
        return "Cannot be empty."
    if not re.match(r"^[a-zA-Z0-9-_]+$", text):
        return (
            "Invalid format. Please only use: letters, digits, hyphons or underscores."
        )
    return True


def validate_unique_name(existing_names: set[str]):
    def _validate(text: str) -> bool | str:
        result = validate_name(text)
        if result == True and text in existing_names:
            return "This name is already in use."
        return result

    return _validate


def validate_name(text: str) -> bool | str:
    if not text.strip():
        return "Cannot be empty."
    if not re.match(r"^[a-zA-Z0-9-_]+$", text):
        return (
            "Invalid format. Please only use: letters, digits, hyphons or underscores."
        )
    return True


def validate_int(text: str) -> bool | str:
    if not text.strip():
        return "Cannot be empty."
    if not re.match(r"^[0-9]+$", text):
        return "Invalid format. Please enter an integer."
    return True


def validate_bool(text: str) -> bool | str:
    if not text.strip():
        return "Cannot be empty."
    if not re.match(r"^(0|1)$", text):
        return "Invalid format. Please enter 0 or 1."
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


def validate_typer_param(func, name: str):
    def _validate(text: str | None):
        if text is not None:
            result = func(text)
            if result != True:
                utils.console.abort_with_error(f"Invalid input for {name}. {result}")

        return text

    return _validate
