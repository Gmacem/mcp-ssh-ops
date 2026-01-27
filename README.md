# MCP SSH Operations

A Model Context Protocol (MCP) server for executing safe diagnostic commands on remote Linux systems via SSH.

## Features

- **Allowlist-based security**: Only pre-approved commands can be executed
- **Dangerous command protection**: Potentially risky commands require explicit permission
- **Pipeline support**: Chain commands together with pipes
- **Flexible configuration**: Easily customize allowed commands via YAML

## Project Structure

```
mcp-ssh-ops/
├── src/mcp_ssh_ops/
│   ├── __init__.py         # Package initialization
│   ├── server.py           # MCP server implementation
│   ├── ssh_client.py       # SSH client wrapper
│   └── commands.py         # Command validation logic
├── commands.yaml           # Allowlist configuration
├── server.py               # Entry point
├── pyproject.toml          # Project configuration
└── README.md
```

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Run the server:
```bash
uv run server.py
# or
uv run mcp-ssh-ops
```

## Usage

The server exposes a single MCP tool: `ssh_exec`

### Parameters

- `hostname`: SSH server hostname or IP address
- `username`: SSH username
- `command`: Command to execute (must be in allowlist)
- `password`: SSH password (optional)
- `key_file`: Path to SSH private key file (optional)
- `port`: SSH port (default: 22)
- `allow_dangerous`: Enable dangerous commands (default: false)

### Example Commands

**Safe commands** (always allowed):
```bash
# Process information
ps aux
ps aux --sort=-%mem | head -20

# Network diagnostics
ss -tulpn
ip -br addr

# Disk usage
df -h
df -h | grep -v tmpfs

# Memory information
free -h

# System information
uptime
who
uname -a

# Logs
journalctl -n 50 --no-pager
dmesg | tail -50

# Pipelines
cat /proc/meminfo | grep MemTotal
ps aux | grep python | wc -l
```

**Dangerous commands** (require `allow_dangerous=true`):
```bash
# Process management
kill -9 1234
systemctl restart nginx
```

## Configuration

Edit `commands.yaml` to customize allowed commands:

```yaml
safe_commands:
  - ps
  - df
  - free
  # Add more safe commands

dangerous_commands:
  - kill
  - systemctl
  # Commands that require explicit permission

settings:
  allow_pipes: true
  max_command_length: 1000
  default_timeout: 30
```

### Command Categories

- **Safe commands**: Read-only diagnostic tools (ps, df, free, etc.)
- **Dangerous commands**: Can modify system state (kill, systemctl)
- **Not in allowlist**: Automatically rejected (rm, shutdown, etc.)

## Security

This server uses an **allowlist-only approach**:
- Only commands in `safe_commands` or `dangerous_commands` are permitted
- Dangerous commands require explicit opt-in via parameter
- All commands not in the allowlist are automatically rejected
- No destructive operations are allowed by default

`★ Insight ─────────────────────────────────────`
- **Allowlist > Denylist**: Explicitly defining what's allowed is more secure than trying to block everything dangerous
- **Pipeline validation**: Each command in a pipeline is validated separately
- **Configuration over code**: Commands are defined in YAML, making it easy to audit and modify security policies without touching code
`─────────────────────────────────────────────────`
