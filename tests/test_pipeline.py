"""Tests for structured command pipeline."""

import textwrap
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from pydantic import ValidationError

from mcp_ssh_ops.commands import Command, Pipeline, CommandValidator, build_shell_command


@pytest.fixture
def validator():
    return CommandValidator()


def _make_validator(yaml_text: str) -> CommandValidator:
    """Create a CommandValidator from inline YAML."""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(textwrap.dedent(yaml_text))
        f.flush()
        return CommandValidator(config_path=Path(f.name))


# --- Model validation ---


class TestCommandModel:
    def test_rejects_path_in_program(self):
        with pytest.raises(ValidationError):
            Command(program="/bin/bash")

    def test_rejects_shell_operators_in_program(self):
        with pytest.raises(ValidationError):
            Command(program="rm;echo")

    def test_empty_pipeline_rejected(self):
        with pytest.raises(ValidationError):
            Pipeline(commands=[])


# --- build_shell_command ---


class TestBuildShellCommand:
    def test_single_command(self):
        p = Pipeline(commands=[Command(program="ps", args=["aux"])])
        assert build_shell_command(p) == "ps aux"

    def test_pipeline(self):
        p = Pipeline(commands=[
            Command(program="ps", args=["aux"]),
            Command(program="grep", args=["python"]),
        ])
        assert build_shell_command(p) == "ps aux | grep python"

    def test_quotes_special_characters(self):
        p = Pipeline(commands=[Command(program="grep", args=["hello world"])])
        assert build_shell_command(p) == "grep 'hello world'"


# --- Allowlist validation ---


class TestAllowlistValidation:
    def test_safe_command_allowed(self, validator):
        p = Pipeline(commands=[Command(program="ps", args=["aux"])])
        ok, err = validator.validate_pipeline(p)
        assert ok and err is None

    def test_unknown_command_rejected(self, validator):
        p = Pipeline(commands=[Command(program="rm", args=["-rf", "/"])])
        ok, err = validator.validate_pipeline(p)
        assert not ok
        assert "not in the allowlist" in err

    def test_dangerous_rejected_by_default(self, validator):
        p = Pipeline(commands=[Command(program="kill", args=["-9", "1234"])])
        ok, err = validator.validate_pipeline(p)
        assert not ok
        assert "dangerous" in err

    def test_dangerous_allowed_with_flag(self, validator):
        p = Pipeline(commands=[Command(program="kill", args=["-9", "1234"])])
        ok, err = validator.validate_pipeline(p, allow_dangerous=True)
        assert ok and err is None


# --- Blacklist arguments ---


class TestBlacklistArgs:
    def test_exact_match(self, validator):
        p = Pipeline(commands=[Command(program="dmesg", args=["-C"])])
        ok, _ = validator.validate_pipeline(p)
        assert not ok

    def test_long_flag_with_value(self, validator):
        p = Pipeline(commands=[Command(program="journalctl", args=["--vacuum-size=100M"])])
        ok, _ = validator.validate_pipeline(p)
        assert not ok

    def test_combined_short_flags(self, validator):
        p = Pipeline(commands=[Command(program="dmesg", args=["-Cl"])])
        ok, _ = validator.validate_pipeline(p)
        assert not ok

    def test_blocked_subcommand(self, validator):
        p = Pipeline(commands=[Command(program="ip", args=["addr", "add", "10.0.0.1/24"])])
        ok, _ = validator.validate_pipeline(p)
        assert not ok

    def test_safe_usage_of_command_with_blocked_args(self, validator):
        p = Pipeline(commands=[Command(program="ip", args=["-br", "addr"])])
        ok, err = validator.validate_pipeline(p)
        assert ok and err is None


# --- Whitelist arguments ---


class TestWhitelistArgs:
    def test_whitelist_allows_listed_arg(self):
        v = _make_validator("""\
            safe_commands:
              myctl:
                args:
                  whitelist: [status, show]
            dangerous_commands: {}
        """)
        p = Pipeline(commands=[Command(program="myctl", args=["status"])])
        ok, err = v.validate_pipeline(p)
        assert ok and err is None

    def test_whitelist_rejects_unlisted_arg(self):
        v = _make_validator("""\
            safe_commands:
              myctl:
                args:
                  whitelist: [status, show]
            dangerous_commands: {}
        """)
        p = Pipeline(commands=[Command(program="myctl", args=["restart"])])
        ok, err = v.validate_pipeline(p)
        assert not ok
        assert "not in the whitelist" in err

    def test_whitelist_rejects_extra_arg(self):
        v = _make_validator("""\
            safe_commands:
              myctl:
                args:
                  whitelist: [status]
            dangerous_commands: {}
        """)
        p = Pipeline(commands=[Command(program="myctl", args=["status", "--verbose"])])
        ok, err = v.validate_pipeline(p)
        assert not ok
        assert "not in the whitelist" in err


# --- Combined whitelist + blacklist ---


class TestCombinedWhitelistBlacklist:
    def test_allowed_arg_passes_both(self):
        v = _make_validator("""\
            safe_commands:
              tool:
                args:
                  whitelist: ["-n", "--no-pager", "--rotate"]
                  blacklist: ["--rotate"]
            dangerous_commands: {}
        """)
        p = Pipeline(commands=[Command(program="tool", args=["-n"])])
        ok, err = v.validate_pipeline(p)
        assert ok and err is None

    def test_whitelisted_but_blacklisted_arg_rejected(self):
        v = _make_validator("""\
            safe_commands:
              tool:
                args:
                  whitelist: ["-n", "--no-pager", "--rotate"]
                  blacklist: ["--rotate"]
            dangerous_commands: {}
        """)
        p = Pipeline(commands=[Command(program="tool", args=["--rotate"])])
        ok, err = v.validate_pipeline(p)
        assert not ok
        assert "not allowed" in err

    def test_not_whitelisted_rejected_before_blacklist(self):
        v = _make_validator("""\
            safe_commands:
              tool:
                args:
                  whitelist: ["-n", "--no-pager"]
                  blacklist: ["--rotate"]
            dangerous_commands: {}
        """)
        p = Pipeline(commands=[Command(program="tool", args=["--other"])])
        ok, err = v.validate_pipeline(p)
        assert not ok
        assert "not in the whitelist" in err


# --- No-restriction commands ---


class TestNoRestrictionCommands:
    def test_command_with_null_spec_allows_any_args(self):
        v = _make_validator("""\
            safe_commands:
              free:
            dangerous_commands: {}
        """)
        p = Pipeline(commands=[Command(program="free", args=["-h", "--si"])])
        ok, err = v.validate_pipeline(p)
        assert ok and err is None

    def test_dangerous_command_no_restrictions(self):
        v = _make_validator("""\
            safe_commands: {}
            dangerous_commands:
              kill:
        """)
        p = Pipeline(commands=[Command(program="kill", args=["-9", "1234"])])
        ok, err = v.validate_pipeline(p, allow_dangerous=True)
        assert ok and err is None
