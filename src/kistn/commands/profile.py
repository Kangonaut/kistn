import questionary
import typer
from rich.console import Console
from typer.params import Argument, Option

from kistn import profile, utils, validators
from kistn.profile import Profile

app = typer.Typer()

console = Console()


@app.command("add")
@app.command()
def create(
    name: str | None = Option(
        default=None,
        callback=validators.validate_typer_param(validators.validate_name, "name"),
    ),
    description: str | None = Option(
        default=None,
    ),
    frequency: int | None = Option(
        default=None,
    ),
    automatic: bool | None = Option(
        default=None,
    ),
):
    profiles = profile.load()
    profile_names = set(profiles.keys())

    try:
        if not name:
            name = questionary.text(
                message="Name:",
                validate=validators.validate_unique_name(profile_names),
            ).unsafe_ask()
        elif name in profile_names:
            utils.console.abort_with_error("This name is already in use.")

        if not description:
            description = questionary.text(
                message="Description:",
            ).unsafe_ask()

        if not frequency:
            utils.console.hint("How often do you want to run this backup?")
            frequency = int(
                questionary.text(
                    message="Frequency (in days):",
                    validate=validators.validate_int,
                ).unsafe_ask()
            )

        if not automatic:
            utils.console.hint("Should the backup be performed automatically?")
            utils.console.hint("NOTE: This setting is not recommended for laptops.")
            automatic = questionary.confirm(
                message="Automatic Backup?",
                default=False,
            ).unsafe_ask()
    except KeyboardInterrupt:
        utils.console.abort()

    p = Profile(
        name=name,  # type: ignore
        description=description,  # type: ignore
        frequency=frequency,  # type: ignore
        automatic=automatic,  # type: ignore
    )

    profiles[p.name] = p
    profile.save(profiles)

    utils.console.success(f"Profile added! Total count: {len(profiles)}")


@app.command("list")
@app.command()
def query():
    profiles = profile.load()
    profiles_list = list(profiles.values())
    profiles_list.sort(key=lambda p: p.name)

    profile.print_profiles(profiles_list)
    console.print(f"\nTotal: {len(profiles)}")


@app.command("delete")
@app.command()
def remove(
    name: str = Argument(
        callback=validators.validate_typer_param(validators.validate_name, "name"),
    ),
):
    profiles: dict[str, Profile] = profile.load()

    if name not in profiles:
        utils.console.abort_with_message("Profile doesn't exist.")

    del profiles[name]  # type: ignore

    profile.save(profiles)
    utils.console.success(f"Profile removed! Total count: {len(profiles)}")
