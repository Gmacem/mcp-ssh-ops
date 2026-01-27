# Agent Instructions

## Project Overview

This is an MCP (Model Context Protocol) server for executing safe diagnostic commands on remote Linux systems via SSH.

**Core principle**: Security through allowlist - only explicitly permitted commands can be executed.

## Architecture

- `src/mcp_ssh_ops/server.py` - FastMCP server exposing ssh_exec tool
- `src/mcp_ssh_ops/ssh_client.py` - Paramiko SSH wrapper
- `src/mcp_ssh_ops/commands.py` - Command validation against YAML allowlist
- `commands.yaml` - Security configuration (safe/dangerous commands)

## Code Style

### Modern Python Best Practices

- Use Python 3.10+ features (type hints, pattern matching if needed)
- Follow PEP 8
- Type hints on all function signatures
- Dataclasses for data structures
- Context managers for resource handling
- F-strings for formatting

### Avoid Unnecessary Comments

**Don't add comments that:**
- Restate what the code does: `# Loop through items`
- Explain obvious Python syntax
- Add TODOs or placeholder comments

**Do add comments for:**
- Non-obvious business logic
- Security decisions
- Complex algorithms
- Why something is done a certain way (not what)

### Example

```python
# Bad
def validate(command: str) -> bool:
    # Split the command by pipe character
    parts = command.split("|")
    # Loop through each part
    for part in parts:
        # Check if valid
        if not self._is_valid(part):
            return False
    return True

# Good
def validate(command: str) -> bool:
    """Validate each command in a pipeline separately."""
    parts = command.split("|")
    return all(self._is_valid(part) for part in parts)
```

## Development Guidelines

1. **Minimize dependencies** - only add packages that are truly needed
2. **Security first** - this project executes remote commands, be paranoid
3. **Keep it simple** - prefer straightforward code over clever abstractions
4. **No premature optimization** - clarity over performance unless there's a real problem
5. **Configuration over code** - security policies belong in YAML, not Python

## Adding New Features

- New safe commands → Add to `commands.yaml` only
- New functionality → Consider if it's needed before implementing
- Security changes → Review allowlist validation carefully
- Dependencies → Must justify the addition

## What Not to Add

- Logging frameworks (print/stderr is fine for now)
- Complex abstractions for simple tasks
- Features "for future use"
- Multiple ways to do the same thing
- Configuration options without clear use cases
