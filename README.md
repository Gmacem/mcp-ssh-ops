# MCP SSH Operations

A Model Context Protocol (MCP) server for executing safe diagnostic commands on remote Linux systems via SSH.

## Features

- **Structured command format**: Commands are specified as structured JSON — shell injection is impossible by construction
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
- `pipeline`: Structured command pipeline (see format below)
- `username`: SSH username (optional if set in ~/.ssh/config)
- `password`: SSH password (optional)
- `key_file`: Path to SSH private key file (optional)
- `port`: SSH port (default: 22)
- `allow_dangerous`: Enable dangerous commands (default: false)

### Pipeline Format

Commands are passed as a structured `pipeline` object containing a list of commands. Each command specifies a `program` and its `args` separately:

```json
{
  "pipeline": {
    "commands": [
      {"program": "ps", "args": ["aux"]}
    ]
  }
}
```

Multiple commands are joined with pipes:

```json
{
  "pipeline": {
    "commands": [
      {"program": "ps", "args": ["aux"]},
      {"program": "grep", "args": ["python"]},
      {"program": "wc", "args": ["-l"]}
    ]
  }
}
```

This constructs: `ps aux | grep python | wc -l` with every token escaped via `shlex.quote()`.

### Example Commands

**Safe commands** (always allowed):
```json
// Process information
{"commands": [{"program": "ps", "args": ["aux"]}]}
{"commands": [{"program": "ps", "args": ["aux", "--sort=-%mem"]}, {"program": "head", "args": ["-20"]}]}

// Network diagnostics
{"commands": [{"program": "ss", "args": ["-tulpn"]}]}
{"commands": [{"program": "ip", "args": ["-br", "addr"]}]}

// Disk usage
{"commands": [{"program": "df", "args": ["-h"]}]}
{"commands": [{"program": "df", "args": ["-h"]}, {"program": "grep", "args": ["-v", "tmpfs"]}]}

// Memory information
{"commands": [{"program": "free", "args": ["-h"]}]}

// System information
{"commands": [{"program": "uptime"}]}
{"commands": [{"program": "uname", "args": ["-a"]}]}

// Logs
{"commands": [{"program": "journalctl", "args": ["-n", "50", "--no-pager"]}]}
{"commands": [{"program": "dmesg"}, {"program": "tail", "args": ["-50"]}]}

// Pipelines
{"commands": [{"program": "cat", "args": ["/proc/meminfo"]}, {"program": "grep", "args": ["MemTotal"]}]}
{"commands": [{"program": "ps", "args": ["aux"]}, {"program": "grep", "args": ["python"]}, {"program": "wc", "args": ["-l"]}]}
```

**Dangerous commands** (require `allow_dangerous=true`):
```json
{"commands": [{"program": "kill", "args": ["-9", "1234"]}]}
{"commands": [{"program": "systemctl", "args": ["restart", "nginx"]}]}
```

## Configuration

Edit `commands.yaml` to customize allowed commands:

```yaml
safe_commands:
  - ps
  - df
  - free

dangerous_commands:
  - kill
  - systemctl
  - awk
  - sed

blocked_args:
  ip:
    - add
    - del
    - set
    - flush
  dmesg:
    - -C
    - --clear

settings:
  allow_pipes: true
  max_command_length: 1000
  default_timeout: 30
```

### Command Categories

- **Safe commands**: Read-only diagnostic tools (ps, df, free, etc.)
- **Dangerous commands**: Can modify system state (kill, systemctl) or execute arbitrary commands (awk, sed), require `allow_dangerous=true`
- **Blocked args**: Per-command argument blacklist preventing state-changing flags/subcommands (e.g. `ip addr add`, `dmesg --clear`)
- **Not in allowlist**: Automatically rejected (rm, shutdown, etc.)

### Argument Blocking

Commands like `ip`, `journalctl`, `date` are safe for read-only use but have flags or subcommands that modify state. The `blocked_args` section blocks specific arguments:

- Exact match: `-C` blocks `dmesg -C`
- Long flags with values: `--vacuum-size` blocks `journalctl --vacuum-size=100M`
- Combined short flags: `-C` blocks `dmesg -Cl`
- Subcommands: `add`, `set` block `ip addr add`, `ip link set`

## Security

This server eliminates shell injection by construction:

- **Structured input**: The AI provides program names and arguments as separate JSON fields — never a raw shell string
- **Automatic escaping**: Every token passes through `shlex.quote()` before reaching the shell. The only shell operators in the final command are `|` characters inserted by the server itself
- **Program name validation**: Program names must match `^[a-zA-Z0-9_][a-zA-Z0-9_.+-]*$` — no paths like `/bin/bash`, no shell operators
- **Allowlist enforcement**: Only commands in `safe_commands` or `dangerous_commands` are permitted
- **Per-command argument blacklists**: Prevent state-changing flags on otherwise safe commands
- **No sequencing operators**: Only pipelines (`|`) are supported — no `&&`, `||`, or `;`. The AI can make multiple tool calls for sequential operations
