"""SSH client for executing commands on remote hosts."""

import paramiko
from typing import Optional


class SSHClient:
    """Simple SSH client wrapper."""

    def __init__(
        self,
        hostname: str,
        username: str,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22,
    ):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self):
        """Establish SSH connection."""
        if self._client is not None:
            return

        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.hostname,
            "port": self.port,
            "username": self.username,
        }

        if self.password:
            connect_kwargs["password"] = self.password
        elif self.key_filename:
            connect_kwargs["key_filename"] = self.key_filename

        self._client.connect(**connect_kwargs)

    def execute(self, command: str, timeout: int = 30) -> dict:
        """
        Execute a command on the remote host.

        Returns:
            dict with stdout, stderr, and exit_code
        """
        if self._client is None:
            self.connect()

        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)

        return {
            "stdout": stdout.read().decode("utf-8"),
            "stderr": stderr.read().decode("utf-8"),
            "exit_code": stdout.channel.recv_exit_status(),
        }

    def close(self):
        """Close the SSH connection."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
