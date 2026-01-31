"""Command validation using allowlist from config."""

import shlex
from pathlib import Path
from typing import Optional

import yaml


class CommandValidator:
    """Validates commands against allowlist from config."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "commands.yaml"

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.safe_commands = set(self.config.get("safe_commands", []))
        self.dangerous_commands = set(self.config.get("dangerous_commands", []))
        self.settings = self.config.get("settings", {})

    def validate(
        self, command: str, allow_dangerous: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if a command is allowed to execute.

        Args:
            command: The command string to validate
            allow_dangerous: Whether to allow dangerous commands

        Returns:
            (is_valid, error_message)
        """
        if not command or not command.strip():
            return False, "Command cannot be empty"

        max_length = self.settings.get("max_command_length", 1000)
        if len(command) > max_length:
            return False, f"Command exceeds maximum length of {max_length} characters"

        if "|" in command and not self.settings.get("allow_pipes", True):
            return False, "Piped commands are not allowed"

        parts = command.split("|")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            try:
                tokens = shlex.split(part)
            except ValueError as e:
                return False, f"Invalid command syntax: {e}"

            if not tokens:
                continue

            base_cmd = tokens[0]

            if base_cmd in self.dangerous_commands:
                if not allow_dangerous:
                    return False, (
                        f"Command '{base_cmd}' is dangerous and requires "
                        "allow_dangerous=true flag"
                    )
            elif base_cmd not in self.safe_commands:
                return False, (
                    f"Command '{base_cmd}' is not in the allowlist. "
                    "Only whitelisted commands are permitted."
                )

        return True, None
