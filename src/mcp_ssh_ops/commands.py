"""Command validation using allowlist from config."""

import re
import shlex
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, field_validator

VALID_PROGRAM_NAME = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.+-]*$")


class Command(BaseModel):
    """A single command with its arguments."""

    program: str
    args: list[str] = []

    @field_validator("program")
    @classmethod
    def validate_program_name(cls, v: str) -> str:
        if not VALID_PROGRAM_NAME.match(v):
            raise ValueError(
                f"Invalid program name '{v}': must be a bare name "
                "(no paths, no shell operators)"
            )
        return v


class Pipeline(BaseModel):
    """A pipeline of commands to be joined with | operators."""

    commands: list[Command]

    @field_validator("commands")
    @classmethod
    def validate_non_empty(cls, v: list[Command]) -> list[Command]:
        if not v:
            raise ValueError("Pipeline must contain at least one command")
        return v


def build_shell_command(pipeline: Pipeline) -> str:
    """Construct a shell command string from a Pipeline.

    Every token is shlex.quote()'d. The only shell operators in the output
    are the | characters we insert ourselves.
    """
    segments = []
    for cmd in pipeline.commands:
        parts = [shlex.quote(cmd.program)]
        parts.extend(shlex.quote(arg) for arg in cmd.args)
        segments.append(" ".join(parts))
    return " | ".join(segments)


class CommandValidator:
    """Validates commands against allowlist from config."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "commands.yaml"

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.settings = self.config.get("settings", {})

        raw_safe = self.config.get("safe_commands") or {}
        raw_dangerous = self.config.get("dangerous_commands") or {}

        self.safe_commands: set[str] = set(raw_safe.keys())
        self.dangerous_commands: set[str] = set(raw_dangerous.keys())

        self._whitelist: dict[str, set[str]] = {}
        self._blacklist: dict[str, set[str]] = {}

        for cmd, spec in {**raw_safe, **raw_dangerous}.items():
            if spec is None:
                continue
            args_spec = spec.get("args") if isinstance(spec, dict) else None
            if args_spec is None:
                continue
            wl = args_spec.get("whitelist")
            bl = args_spec.get("blacklist")
            if wl:
                self._whitelist[cmd] = set(wl)
            if bl:
                self._blacklist[cmd] = set(bl)

    def _find_blocked_arg(self, token: str, blocked: set[str]) -> Optional[str]:
        """Check if a token matches any blocked argument.

        Handles exact matches, --flag=value, and combined short flags (-Ci matching -C).
        """
        if token in blocked:
            return token

        if "=" in token:
            flag_part = token.split("=", 1)[0]
            if flag_part in blocked:
                return flag_part

        if token.startswith("-") and not token.startswith("--") and len(token) > 2:
            for b in blocked:
                if b.startswith("-") and not b.startswith("--") and len(b) == 2:
                    if b[1] in token[1:]:
                        return b

        return None

    def validate_pipeline(
        self, pipeline: Pipeline, allow_dangerous: bool = False
    ) -> tuple[bool, Optional[str]]:
        """Validate a structured pipeline against the allowlist.

        Args:
            pipeline: The structured pipeline to validate
            allow_dangerous: Whether to allow dangerous commands

        Returns:
            (is_valid, error_message)
        """
        if not self.settings.get("allow_pipes", True) and len(pipeline.commands) > 1:
            return False, "Piped commands are not allowed"

        for cmd in pipeline.commands:
            program = cmd.program

            if program in self.dangerous_commands:
                if not allow_dangerous:
                    return False, (
                        f"Command '{program}' is dangerous and requires "
                        "allow_dangerous=true flag"
                    )
            elif program not in self.safe_commands:
                return False, (
                    f"Command '{program}' is not in the allowlist. "
                    "Only whitelisted commands are permitted."
                )

            if program in self._whitelist:
                allowed = self._whitelist[program]
                for arg in cmd.args:
                    if arg not in allowed:
                        return False, (
                            f"Argument '{arg}' is not in the whitelist for "
                            f"command '{program}'"
                        )

            if program in self._blacklist:
                blocked = self._blacklist[program]
                for arg in cmd.args:
                    matched = self._find_blocked_arg(arg, blocked)
                    if matched:
                        return False, (
                            f"Argument '{matched}' is not allowed for "
                            f"command '{program}'"
                        )

        return True, None
