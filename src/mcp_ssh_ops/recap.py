"""Optional recap logging of SSH command executions."""

from datetime import datetime
from pathlib import Path
from typing import Optional


class RecapLogger:
    """Writes command recaps to date-organized directories.

    Directory layout::

        recap_dir/
            2026-02-01/
                153045_123456.log
                153212_654321.log
            2026-02-02/
                ...
    """

    def __init__(self, recap_dir: Optional[Path] = None):
        self._dir = recap_dir

    def save(self, hostname: str, command: str, output: str) -> None:
        """Save a command recap. No-op if recap_dir was not configured."""
        if self._dir is None:
            return

        now = datetime.now()
        date_dir = self._dir / now.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        filename = now.strftime("%H%M%S_%f") + ".log"
        filepath = date_dir / filename

        with open(filepath, "w") as f:
            f.write(f"Host: {hostname}\n")
            f.write(f"Timestamp: {now.isoformat()}\n")
            f.write(f"Command: {command}\n")
            f.write(f"\n{output}")
