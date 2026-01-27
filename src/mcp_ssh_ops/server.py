"""MCP server for executing safe commands over SSH."""

from mcp.server.fastmcp import FastMCP

from .commands import CommandValidator
from .ssh_client import SSHClient


# Initialize MCP server
mcp = FastMCP("SSH Operations")

# Initialize command validator
validator = CommandValidator()


@mcp.tool()
def ssh_exec(
    hostname: str,
    username: str,
    command: str,
    password: str = None,
    key_file: str = None,
    port: int = 22,
    allow_dangerous: bool = False,
) -> str:
    """
    Execute a command on a remote host via SSH.

    Args:
        hostname: SSH server hostname or IP
        username: SSH username
        command: Command to execute (must be in allowlist)
        password: SSH password (optional)
        key_file: Path to SSH private key (optional)
        port: SSH port (default: 22)
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
        with SSHClient(
            hostname=hostname,
            username=username,
            password=password,
            key_filename=key_file,
            port=port,
        ) as client:
            result = client.execute(
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


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
