"""MCP server for executing safe commands over SSH."""

import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .commands import CommandValidator, Pipeline, build_shell_command
from .host_memory import HostMemory
from .recap import RecapLogger
from .ssh_client import SSHClient


mcp = FastMCP("SSH Operations")
validator: CommandValidator = None  # type: ignore[assignment]
memory: HostMemory = None  # type: ignore[assignment]
recap: RecapLogger = None  # type: ignore[assignment]


@mcp.tool()
async def ssh_exec(
    hostname: str,
    pipeline: Pipeline,
    username: str = None,
    password: str = None,
    key_file: str = None,
    port: int = None,
    allow_dangerous: bool = False,
) -> str:
    """
    Execute a command pipeline on a remote host via SSH.

    Takes a structured pipeline instead of a raw command string.
    Each command specifies a program and its arguments as separate fields.
    The server constructs the shell command with proper escaping.

    Supports ~/.ssh/config: host aliases, default user/port/key, ProxyJump,
    and other directives are resolved automatically. Explicit arguments
    override config values.

    Args:
        hostname: SSH server hostname, IP, or host alias from ~/.ssh/config
        pipeline: Structured command pipeline, e.g.:
            {"commands": [{"program": "ps", "args": ["aux"]}]}
            {"commands": [
                {"program": "ps", "args": ["aux"]},
                {"program": "grep", "args": ["python"]},
                {"program": "wc", "args": ["-l"]}
            ]}
        username: SSH username (optional if set in ~/.ssh/config)
        password: SSH password (optional)
        key_file: Path to SSH private key (optional if set in ~/.ssh/config)
        port: SSH port (optional, defaults to ~/.ssh/config value or 22)
        allow_dangerous: Allow dangerous commands (default: false)

    Returns:
        Command output
    """
    is_valid, error = validator.validate_pipeline(
        pipeline, allow_dangerous=allow_dangerous
    )
    if not is_valid:
        return f"ERROR: {error}"

    command = build_shell_command(pipeline)

    try:
        async with SSHClient(
            hostname=hostname,
            username=username,
            password=password,
            key_filename=key_file,
            port=port,
        ) as client:
            result = await client.execute(
                command, timeout=validator.settings.get("default_timeout", 30)
            )

            output = f"Command: {command}\n"
            output += f"Exit code: {result['exit_code']}\n\n"

            if result["stdout"]:
                output += f"STDOUT:\n{result['stdout']}\n"

            if result["stderr"]:
                output += f"STDERR:\n{result['stderr']}\n"

            recap.save(hostname, command, output)
            return output

    except Exception as e:
        error_output = f"ERROR: {str(e)}"
        recap.save(hostname, command, error_output)
        return error_output


@mcp.tool()
async def host_info(hostname: str = None) -> str:
    """
    Look up stored host descriptions and per-host tools from hosts.yaml.

    Args:
        hostname: Host alias to look up. If omitted, returns all hosts.

    Returns:
        Host description(s), associated tools, or a not-found message.
    """
    if hostname is not None:
        entry = memory.get(hostname)
        if entry is None:
            return f"No host memory found for '{hostname}'."
        return _format_host(hostname, entry)

    hosts = memory.list_all()
    if not hosts:
        return "No host memory entries found. Add hosts to hosts.yaml."
    return "\n\n".join(_format_host(k, v) for k, v in hosts.items())


def _format_host(name: str, entry) -> str:
    """Format a single host entry for display."""
    lines = [f"{name}: {entry.description}"]
    if entry.tools:
        lines.append("  tools: " + ", ".join(entry.tools))
    return "\n".join(lines)


@mcp.tool()
async def list_commands(category: str = None) -> str:
    """
    List commands available for execution via ssh_exec.

    Args:
        category: Filter by category — "safe", "dangerous", or omit for all.

    Returns:
        Available commands grouped by category.
    """
    safe = sorted(validator.safe_commands)
    dangerous = sorted(validator.dangerous_commands)

    if category == "safe":
        return "Safe commands:\n" + ", ".join(safe)
    if category == "dangerous":
        return "Dangerous commands (require allow_dangerous=true):\n" + ", ".join(
            dangerous
        )

    lines = [
        "Safe commands:",
        ", ".join(safe),
        "",
        "Dangerous commands (require allow_dangerous=true):",
        ", ".join(dangerous),
    ]
    return "\n".join(lines)


def main():
    """Run the MCP server."""
    global validator, memory, recap

    parser = argparse.ArgumentParser(description="MCP SSH Operations server")
    parser.add_argument(
        "--hosts-config",
        type=Path,
        default=None,
        help="Path to hosts.yaml (omit for empty host memory)",
    )
    parser.add_argument(
        "--commands-config",
        type=Path,
        default=None,
        help="Path to commands.yaml (default: commands.yaml next to the package)",
    )
    parser.add_argument(
        "--recap-dir",
        type=Path,
        default=None,
        help="Directory for saving command recaps (omit to disable)",
    )
    args = parser.parse_args()

    validator = CommandValidator(config_path=args.commands_config)
    memory = HostMemory(config_path=args.hosts_config)
    recap = RecapLogger(recap_dir=args.recap_dir)

    mcp.run()


if __name__ == "__main__":
    main()
