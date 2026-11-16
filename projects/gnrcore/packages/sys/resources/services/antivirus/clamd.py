#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import struct

from gnr.core.gnrlang import GnrException
from gnr.lib.services.antivirus import AntivirusService
from gnr.web.gnrbaseclasses import BaseComponent


class Service(AntivirusService):
    """Scans with a ClamAV ``clamd`` daemon, through its ``INSTREAM`` command.

    The daemon is reached on a unix socket (``socket_path``: a daemon on the
    same machine) or over TCP (``host`` and ``port``: a daemon on the same
    machine or on another one). ``socket_path`` wins when both are given.
    The content travels on the connection: the daemon needs no access to the
    storage of the site."""
    default_port = 3310
    default_timeout = 30
    chunk_size = 65536

    def __init__(self, parent, socket_path=None, host=None, port=None, timeout=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.socket_path = socket_path
        self.host = host
        self.port = int(port or self.default_port)
        self.timeout = float(timeout or self.default_timeout)

    def scan(self, content=None, filename=None, **kwargs):
        try:
            reply = self.instream(content)
        except OSError as error:
            raise GnrException('clamd scan of %s failed: %s' % (filename, error))
        if reply.endswith(' OK'):
            return None
        if reply.endswith(' FOUND'):
            return reply[:-len(' FOUND')].split(': ', 1)[1]
        raise GnrException('clamd scan of %s failed: %s' % (filename, reply))

    def connect(self):
        if self.socket_path:
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                connection.settimeout(self.timeout)
                connection.connect(self.socket_path)
            except OSError:
                connection.close()
                raise
            return connection
        if not self.host:
            raise GnrException('clamd service %s: neither socket_path nor host is configured'
                               % self.service_name)
        return socket.create_connection((self.host, self.port), timeout=self.timeout)

    def instream(self, content):
        """Send the content to clamd and return its reply, e.g. ``stream: OK``
        or ``stream: Eicar-Test-Signature FOUND``."""
        with self.connect() as connection:
            connection.sendall(b'zINSTREAM\0')
            for offset in range(0, len(content), self.chunk_size):
                chunk = content[offset:offset + self.chunk_size]
                connection.sendall(struct.pack('!I', len(chunk)) + chunk)
            connection.sendall(struct.pack('!I', 0))
            reply = b''
            while not reply.endswith(b'\0'):
                data = connection.recv(4096)
                if not data:
                    break
                reply += data
        return reply.rstrip(b'\0').decode('utf-8', 'replace').strip()


class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.socket_path', lbl='Unix socket path', width='30em')
        fb.textbox(value='^.host', lbl='Host', width='30em')
        fb.numberTextBox(value='^.port', lbl='Port', placeholder=str(Service.default_port))
        fb.numberTextBox(value='^.timeout', lbl='Timeout (seconds)',
                         placeholder=str(Service.default_timeout))
