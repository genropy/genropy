#!/usr/bin/env python
"""SSH tunneling utilities for secure port forwarding.

This module provides SSH tunnel functionality using paramiko, allowing
secure forwarding of local ports through SSH connections. It is primarily
used by the daemon handler for database connections through SSH tunnels.

Example:
    >>> tunnel = SshTunnel(
    ...     forwarded_port=5432,
    ...     ssh_host='example.com',
    ...     ssh_port=22,
    ...     username='user',
    ...     password='pass'
    ... )
    >>> tunnel.prepare_tunnel()
    >>> tunnel.serve_tunnel()
    >>> print(tunnel.local_port)  # dynamically assigned port
    >>> tunnel.stop()

Dependencies:
    - paramiko: SSH client library (optional, raises GnrException if missing)
"""

from __future__ import annotations

import re
import getpass
import select
import socketserver
import threading
import _thread
import atexit
from typing import TYPE_CHECKING

try:
    import paramiko
except ImportError:
    paramiko = None  # type: ignore[assignment]

from gnr.core import logger
from gnr.core.gnrlang import GnrException

if TYPE_CHECKING:
    from typing import Any
    from paramiko.transport import Transport


# Regex pattern for parsing SSH connection strings
# Format: user:password@host:port (password and port are optional)
CONN_STRING_RE = r"(?P<ssh_user>\w*)\:?(?P<ssh_password>\w*)\@(?P<ssh_host>(\w|\.)*)\:?(?P<ssh_port>\w*)"
CONN_STRING = re.compile(CONN_STRING_RE)


def normalized_sshtunnel_parameters(**options: Any) -> dict[str, Any]:
    """Parse and normalize SSH tunnel configuration parameters.

    Parses a connection string and merges it with explicit options.
    The connection string format is: user:password@host:port

    Args:
        **options: Configuration options. Must include 'ssh_host' which
            can be either a plain hostname or a connection string.
            Other options (ssh_user, ssh_password, ssh_port, forwarded_host,
            forwarded_port) override parsed values if not None.

    Returns:
        Dictionary with normalized parameters:
            - ssh_user: Username for SSH connection
            - ssh_password: Password for SSH authentication
            - ssh_host: SSH server hostname
            - ssh_port: SSH server port (default: '22')
            - forwarded_host: Host to forward to (default: '127.0.0.1')
            - Plus any other options passed in

    Raises:
        KeyError: If ssh_host is not provided in options.
        AttributeError: If ssh_host doesn't match the connection string pattern.
    """
    connection_string = options.pop("ssh_host")
    match = re.search(CONN_STRING, connection_string)
    result: dict[str, Any] = dict(
        ssh_user=match.group("ssh_user") or None,  # type: ignore[union-attr]
        ssh_password=match.group("ssh_password") or None,  # type: ignore[union-attr]
        ssh_host=match.group("ssh_host") or None,  # type: ignore[union-attr]
        ssh_port=match.group("ssh_port") or "22",
    )  # type: ignore[union-attr]
    options = options or dict()
    for k, v in list(options.items()):
        if v is not None:
            result[k] = v
    result["forwarded_host"] = options.get("forwarded_host") or "127.0.0.1"
    return result


class ForwardServer(socketserver.ThreadingTCPServer):
    """Threaded TCP server for SSH port forwarding.

    A TCP server that handles multiple connections using threads,
    suitable for forwarding traffic through SSH tunnels.

    Attributes:
        daemon_threads: If True, threads are daemon threads (default: True).
        allow_reuse_address: If True, allows address reuse (default: True).
    """

    daemon_threads = True
    allow_reuse_address = True


class Handler(socketserver.BaseRequestHandler):
    """Request handler for forwarding data through SSH channel.

    This handler creates an SSH channel for each connection and
    bidirectionally forwards data between the local socket and
    the remote host through the SSH tunnel.

    Class Attributes (set by SshTunnel):
        forwarded_host: Remote host to forward to.
        forwarded_port: Remote port to forward to.
        ssh_transport: Paramiko transport for SSH connection.
        exit_event: Threading event for shutdown signaling.
    """

    # These are set dynamically by SshTunnel.prepare_tunnel()
    forwarded_host: str
    forwarded_port: int
    ssh_transport: Transport
    exit_event: threading.Event

    def handle(self) -> None:
        """Handle a single connection by forwarding through SSH.

        Opens an SSH channel to the forwarded host/port and copies
        data bidirectionally between the local request socket and
        the SSH channel until either side closes the connection.
        """
        try:
            chan = self.ssh_transport.open_channel(
                "direct-tcpip",
                (self.forwarded_host, self.forwarded_port),
                self.request.getpeername(),
            )
        except Exception:
            # REVIEW:SMELL - bare except that just re-raises
            raise
        if chan is None:
            return

        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        chan.close()
        self.request.close()


class IncompleteConfigurationException(Exception):
    """Raised when SSH tunnel configuration is incomplete.

    This exception indicates that required parameters for establishing
    an SSH tunnel are missing.
    """

    pass


class SshTunnel:
    """SSH tunnel for secure port forwarding.

    Creates an SSH connection and forwards a local port to a remote
    host/port through the encrypted tunnel. Useful for secure database
    connections and other services.

    Args:
        local_port: Local port to listen on (0 for auto-assign).
        forwarded_host: Remote host to forward to (default: '127.0.0.1').
        forwarded_port: Remote port to forward to.
        ssh_host: SSH server hostname.
        ssh_port: SSH server port (default: 22).
        username: SSH username.
        password: SSH password.

    Attributes:
        local_port: The actual local port being used (may be auto-assigned).
        forwarded_host: Remote host being forwarded to.
        forwarded_port: Remote port being forwarded to.
        ssh_host: SSH server hostname.
        ssh_port: SSH server port.
        username: SSH username.
        password: SSH password.
        exit_event: Threading event for shutdown coordination.

    Example:
        >>> tunnel = SshTunnel(
        ...     forwarded_port=5432,
        ...     ssh_host='db-gateway.example.com',
        ...     username='admin',
        ...     password='secret'
        ... )
        >>> tunnel.prepare_tunnel()
        >>> tunnel.serve_tunnel()
        >>> # Connect to localhost:tunnel.local_port
        >>> tunnel.stop()
    """

    def __init__(
        self,
        local_port: int = 0,
        forwarded_host: str = "127.0.0.1",
        forwarded_port: int | None = None,
        ssh_host: str | None = None,
        ssh_port: int = 22,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize SSH tunnel configuration.

        Args:
            local_port: Local port to listen on (0 for auto-assign).
            forwarded_host: Remote host to forward to.
            forwarded_port: Remote port to forward to.
            ssh_host: SSH server hostname.
            ssh_port: SSH server port.
            username: SSH username for authentication.
            password: SSH password for authentication.
        """
        self.forwarded_host = forwarded_host
        self.forwarded_port = forwarded_port
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self._local_port = local_port
        self.username = username
        self.password = password
        self.exit_event = threading.Event()
        self.client: "paramiko.SSHClient | None" = None
        self.forwarding_server: ForwardServer | None = None

    @property
    def local_port(self) -> int:
        """Get the local port number.

        Returns:
            The local port number. If 0 was specified during init,
            the actual assigned port is returned after prepare_tunnel().
        """
        return self._local_port

    def prepare_tunnel(self) -> None:
        """Prepare the SSH tunnel for use.

        Establishes the SSH connection and sets up the local forwarding
        server. Must be called before serve_tunnel().

        Raises:
            GnrException: If paramiko is not installed.
            IncompleteConfigurationException: If required parameters are missing.
            paramiko.SSHException: If SSH connection fails.
        """
        if not paramiko:
            raise GnrException(
                "Missing required library paramiko. Please run pip install paramiko"
            )
        if not self.forwarded_host:
            raise IncompleteConfigurationException("Missing Forwarded Host")
        if not self.forwarded_port:
            raise IncompleteConfigurationException("Missing Forwarded Port")
        if not self.ssh_host:
            raise IncompleteConfigurationException("Missing Ssh Host")
        if not self.ssh_port:
            raise IncompleteConfigurationException("Missing Ssh Port")
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.client.connect(
            self.ssh_host,
            self.ssh_port,
            username=self.username,
            look_for_keys=False,
            password=self.password,
        )
        transport = self.client.get_transport()

        # Create a subclass with instance-specific attributes
        tunnel_self = self

        class SubHandler(Handler):
            forwarded_host = tunnel_self.forwarded_host
            forwarded_port = tunnel_self.forwarded_port  # type: ignore[assignment]
            ssh_transport = transport  # type: ignore[assignment]
            exit_event = tunnel_self.exit_event

        self.forwarding_server = ForwardServer(("", self.local_port), SubHandler)
        self._local_port = self.forwarding_server.socket.getsockname()[1]

    def stop(self) -> None:
        """Stop the SSH tunnel.

        Shuts down the forwarding server. The SSH connection remains
        open and should be closed separately if needed.
        """
        if self.forwarding_server:
            self.forwarding_server.shutdown()

    def serve_tunnel(self) -> None:
        """Start serving the tunnel in a background thread.

        Starts the forwarding server in a separate thread, allowing
        the main thread to continue execution.
        """
        _thread.start_new_thread(self._serve_tunnel, ())

    def _serve_tunnel(self) -> None:
        """Internal method to run the forwarding server.

        This method runs in a background thread and blocks until
        the server is shut down.
        """
        if self.forwarding_server:
            self.forwarding_server.serve_forever()


def stop_tunnel(tunnel: SshTunnel) -> None:
    """Stop an SSH tunnel (for use with atexit).

    Args:
        tunnel: The tunnel to stop.
    """
    tunnel.stop()


def main() -> None:
    """Demo function for testing SSH tunnel functionality.

    Creates a tunnel to genropy.org and waits for user input to stop.
    This is intended for manual testing only.
    """
    # REVIEW:SMELL - hardcoded test server, password assigned twice
    server_host = "genropy.org"
    server_port = 22
    password = None
    password = getpass.getpass("Enter SSH password: ")
    tunnel = SshTunnel(
        forwarded_port=22,
        ssh_host=server_host,
        ssh_port=server_port,
        username="genro",
        password=password,
    )
    tunnel.prepare_tunnel()
    logger.info(f"Local port {tunnel.local_port}")
    tunnel.serve_tunnel()
    atexit.register(stop_tunnel, tunnel)
    password = getpass.getpass("any key to stop ")


if __name__ == "__main__":
    main()
