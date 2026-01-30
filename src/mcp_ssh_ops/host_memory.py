"""Host memory: read-only lookup of user-managed host descriptions."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class HostEntry:
    """A single host's description and associated commands."""

    description: str
    tools: list[str] = field(default_factory=list)


class HostMemory:
    """Loads host descriptions and per-host tools from hosts.yaml."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "hosts.yaml"

        self._hosts: dict[str, HostEntry] = {}

        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    self._hosts[str(k)] = self._parse_entry(v)

    @staticmethod
    def _parse_entry(value) -> HostEntry:
        """Parse a host entry from either a plain string or a dict."""
        if isinstance(value, dict):
            description = str(value.get("description", ""))
            tools = [str(t) for t in value.get("tools", [])]
            return HostEntry(description=description, tools=tools)
        return HostEntry(description=str(value))

    def get(self, hostname: str) -> Optional[HostEntry]:
        """Look up a single host's entry."""
        return self._hosts.get(hostname)

    def list_all(self) -> dict[str, HostEntry]:
        """Return the full hostname-to-entry mapping."""
        return dict(self._hosts)
