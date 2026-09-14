from pathlib import Path

from rich.console import Console

from kistn import constants, prompts, utils
from kistn.models import (BorgmaticCheck, BorgmaticConfig, BorgmaticRepository,
                          RemoteConfig)

console = Console()


class SetupWizard:
    def __init__(self):
        self.profile_name: str = "pandoras-box"
        self.remind_frequency: int | None = None
        self.remote_config: RemoteConfig | None = None
        self.borgmatic_config: BorgmaticConfig | None = None
        self.gen_ssh_key: bool = False
        self.upload_ssh_key: bool = False
        self.borgmatic_config_overwrite: bool = False
        self.generate_paper_key: bool = False
        self.store_paper_key: bool = False

    @property
    def ssh_key_path(self) -> Path:
        return constants.SSH_KEY_DIR / self.profile_name

    def run(self):
        self._run_preflight()
        self._run_questionare()
        self._run_review()
        self._run_exec()

        print(
            "\n[bold green]🎉 Setup complete! Run 'kistn run' to initiate your first backup.[/bold green]\n"
        )

    def _run_preflight(self):
        utils.system.check_system_dependencies()

    def _run_questionare(self):
        self.profile_name = prompts.config.prompt_profile_name()
        hostname = prompts.config.prompt_remote_hostname()
        port = prompts.config.prompt_remote_port()
        username = prompts.config.prompt_remote_username()
        remote_name = prompts.config.prompt_remote_name()
        self.remote_config = RemoteConfig(
            hostname=hostname,
            port=port,
            username=username,
            name=remote_name,
        )

        self.gen_ssh_key = prompts.ssh.prompt_key_generation(self.ssh_key_path)
        self.upload_ssh_key = prompts.ssh.prompt_key_upload()

        source_directories = prompts.config.prompt_source_directories()
        encryption_passphrase = prompts.config.prompt_encryption_passphrase()
        self.borgmatic_config_overwrite = (
            prompts.config.prompt_borgmatic_config_overwrite()
        )
        self.borgmatic_config = BorgmaticConfig(
            source_directories=source_directories,
            encryption_passphrase=encryption_passphrase,
            exclude_patterns=constants.BORGMATIC_EXCLUDE_PATTERNS,
            repositories=[
                BorgmaticRepository(
                    path=f"ssh://{self.profile_name}/./{self.profile_name}",
                    label=self.profile_name,
                ),
            ],
            compression=constants.BORGMATIC_COMPRESSION,
            keep_daily=constants.BORGMATIC_KEEP_DAILY,
            keep_weekly=constants.BORGMATIC_KEEP_WEEKLY,
            keep_monthly=constants.BORGMATIC_KEEP_MONTHLY,
            checks=[
                BorgmaticCheck(name="repository"),
                BorgmaticCheck(name="archives"),
            ],
        )

        self.generate_paper_key = prompts.borgmatic.confirm_paper_key_generation()
        if self.generate_paper_key:
            self.store_paper_key = prompts.borgmatic.confirm_paper_key_storage()

    def _run_review(self):
        pass

    def _run_exec(self):
        if self.gen_ssh_key:
            prompts.ssh.run_key_generation(self.ssh_key_path)

        prompts.ssh.run_config_update(self.config, self.ssh_key_path)

        if self.upload_ssh_key:
            prompts.ssh.run_key_upload(self.config, self.ssh_key_path)

        prompts.config.run_borgmatic_config_update(
            self.borgmatic_config,
            self.borgmatic_config_overwrite,
        )

        if self.generate_paper_key:
            prompts.borgmatic.run_paper_key_export()
            if self.store_paper_key:
                prompts.borgmatic.run_paper_key_storage()
            else:
                print(
                    "[yellow]Skipping paper key storage. Don't forget to save it before closing this terminal session![/yellow]"
                )
        else:
            print("[yellow]Skipping paper key export.[/yellow]")
