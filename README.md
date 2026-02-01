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
│   ├── commands.py         # Command validation logic
│   ├── host_memory.py      # Host descriptions from hosts.yaml
│   └── recap.py            # Optional command recap logging
├── commands.yaml           # Allowlist configuration
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
uv run mcp-ssh-ops
```

### CLI Arguments

| Argument | Description | Default |
|---|---|---|
| `--hosts-config PATH` | Path to `hosts.yaml` with host descriptions | None (empty host memory) |
| `--commands-config PATH` | Path to `commands.yaml` with allowlist | `commands.yaml` next to the package |
| `--recap-dir PATH` | Directory for saving command execution recaps | None (disabled) |

Example MCP client config:

```json
{
  "mcpServers": {
    "ssh-ops": {
      "command": "mcp-ssh-ops",
      "args": [
        "--hosts-config", "/etc/mcp/hosts.yaml",
        "--commands-config", "/etc/mcp/commands.yaml",
        "--recap-dir", "/var/log/mcp-recaps"
      ]
    }
  }
}
```

When `--recap-dir` is set, each command execution is saved as a `.log` file under `recap-dir/YYYY-MM-DD/HHMMSS_ffffff.log`.

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

Edit `commands.yaml` to customize allowed commands. Both `safe_commands` and `dangerous_commands` are dicts where each key is a command name. A command with no value (or `null`) has no argument restrictions. To restrict arguments, add an `args` key with `whitelist` and/or `blacklist`:

```yaml
safe_commands:
  ps:
  df:
  free:
  ip:
    args:
      blacklist: [add, del, set, flush]
  dmesg:
    args:
      blacklist: [-C, --clear, -c]

dangerous_commands:
  kill:
  systemctl:
  awk:
  sed:

settings:
  allow_pipes: true
  max_command_length: 1000
  default_timeout: 30
```

### Command Categories

- **Safe commands**: Read-only diagnostic tools (ps, df, free, etc.)
- **Dangerous commands**: Can modify system state (kill, systemctl) or execute arbitrary commands (awk, sed), require `allow_dangerous=true`
- **Not in allowlist**: Automatically rejected (rm, shutdown, etc.)

### Per-Command Argument Restrictions

Each command can define `whitelist` and/or `blacklist` under `args`:

- **whitelist**: If set, only these exact arguments are allowed
- **blacklist**: If set, these arguments are blocked (supports exact match, `--flag=value`, and combined short flags like `-Cl` matching `-C`)

Both can be combined — whitelist is checked first, then blacklist.

Examples of blacklist matching:
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
- **Per-command argument whitelists/blacklists**: Restrict or block specific arguments on a per-command basis
- **No sequencing operators**: Only pipelines (`|`) are supported — no `&&`, `||`, or `;`. The AI can make multiple tool calls for sequential operations
