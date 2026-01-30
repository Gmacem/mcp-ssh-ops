"""MCP server for executing safe commands over SSH."""

from mcp.server.fastmcp import FastMCP

from .commands import CommandValidator
from .host_memory import HostMemory
from .ssh_client import SSHClient


# Initialize MCP server
mcp = FastMCP("SSH Operations")

# Initialize command validator
validator = CommandValidator()

# Initialize host memory
memory = HostMemory()


@mcp.tool()
async def ssh_exec(
    hostname: str,
    command: str,
    username: str = None,
    password: str = None,
    key_file: str = None,
    port: int = None,
    allow_dangerous: bool = False,
) -> str:
    """
    Execute a command on a remote host via SSH.

    Supports ~/.ssh/config: host aliases, default user/port/key, ProxyJump,
    and other directives are resolved automatically. Explicit arguments
    override config values.

    Args:
        hostname: SSH server hostname, IP, or host alias from ~/.ssh/config
        command: Command to execute (must be in allowlist)
        username: SSH username (optional if set in ~/.ssh/config)
        password: SSH password (optional)
        key_file: Path to SSH private key (optional if set in ~/.ssh/config)
        port: SSH port (optional, defaults to ~/.ssh/config value or 22)
        allow_dangerous: Allow dangerous commands (default: false)

    Returns:
        Command output
    """
    # Validate command
    is_valid, error = validator.validate(command, allow_dangerous=allow_dangerous)
    if not is_valid:
        return f"ERROR: {error}"

    # Execute command
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

            # Format output
            output = f"Command: {command}\n"
            output += f"Exit code: {result['exit_code']}\n\n"

            if result["stdout"]:
                output += f"STDOUT:\n{result['stdout']}\n"

            if result["stderr"]:
                output += f"STDERR:\n{result['stderr']}\n"

            return output

    except Exception as e:
        return f"ERROR: {str(e)}"


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
    mcp.run()


if __name__ == "__main__":
    main()
