"""SSH client for executing commands on remote hosts."""

import asyncio
import asyncssh
from typing import Optional


class SSHClient:
    """Async SSH client wrapper using asyncssh.

    Automatically loads ~/.ssh/config for host aliases, default user/port/key,
    ProxyJump, and other directives. Explicit arguments override config values.
    """

    def __init__(
        self,
        hostname: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self._conn: Optional[asyncssh.SSHClientConnection] = None

    async def connect(self):
        """Establish SSH connection, applying ~/.ssh/config automatically."""
        if self._conn is not None:
            return

        connect_kwargs: dict = {"host": self.hostname, "known_hosts": None}

        if self.username:
            connect_kwargs["username"] = self.username
        if self.port:
            connect_kwargs["port"] = self.port
        if self.password:
            connect_kwargs["password"] = self.password
        elif self.key_filename:
            connect_kwargs["client_keys"] = [self.key_filename]

        self._conn = await asyncssh.connect(**connect_kwargs)

    async def execute(self, command: str, timeout: int = 30) -> dict:
        """
        Execute a command on the remote host.

        Returns:
            dict with stdout, stderr, and exit_code
        """
        if self._conn is None:
            await self.connect()

        result = await asyncio.wait_for(self._conn.run(command), timeout=timeout)

        return {
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "exit_code": result.exit_status,
        }

    def close(self):
        """Close the SSH connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
