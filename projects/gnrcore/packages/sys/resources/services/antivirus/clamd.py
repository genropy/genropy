#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import socket
import struct
import subprocess

import requests

from gnr.core.gnrlang import GnrException
from gnr.lib.services.antivirus import AntivirusService
from gnr.web.gnrbaseclasses import BaseComponent


class Service(AntivirusService):
    """Scans with ClamAV, reached in the way ``mode`` says:

    - ``https``: an HTTP endpoint in front of ClamAV. The content is the body
      of a POST to ``url``, sent with ``Authorization: Bearer <token>``. The
      endpoint answers 200 with the JSON ``{"threat": null}`` for a clean
      content and ``{"threat": "<name>"}`` for an infected one.
    - ``tcp``: a ``clamd`` daemon listening on ``host`` and ``port``, through
      its ``INSTREAM`` command.
    - ``local``: the ``clamscan`` executable of the machine the site runs on,
      started once for every scan. It loads the signatures at every start, so
      it is slow: meant for development, where no daemon is running.

    In every mode the content travels to ClamAV: ClamAV needs no access to the
    storage of the site."""
    default_port = 3310
    timeout = 30
    local_timeout = 300
    chunk_size = 65536
    executable = 'clamscan'

    def __init__(self, parent, mode=None, url=None, token=None, host=None, port=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.mode = mode
        self.url = url
        self.token = token
        self.host = host
        self.port = int(port or self.default_port)

    def scan(self, content=None, filename=None, **kwargs):
        handler = getattr(self, 'scan_%s' % self.mode, None)
        if handler is None:
            raise self.scanError(filename, 'unknown mode %r' % self.mode)
        return handler(content, filename)

    def scanError(self, filename, reason):
        return GnrException('antivirus scan of %s failed: %s' % (filename, reason))

    def threatName(self, line):
        """The name in a ClamAV line like ``stream: Eicar-Test-Signature FOUND``"""
        return line[:-len(' FOUND')].split(': ', 1)[1]

    def scan_https(self, content, filename):
        try:
            response = requests.post(self.url, data=content, timeout=self.timeout,
                                     headers={'Authorization': 'Bearer %s' % self.token,
                                              'Content-Type': 'application/octet-stream'})
        except requests.RequestException as error:
            raise self.scanError(filename, error)
        if response.status_code != 200:
            raise self.scanError(filename, 'the endpoint answered %s' % response.status_code)
        return response.json()['threat']

    def scan_tcp(self, content, filename):
        try:
            reply = self.instream(content)
        except OSError as error:
            raise self.scanError(filename, error)
        if reply.endswith(' OK'):
            return None
        if reply.endswith(' FOUND'):
            return self.threatName(reply)
        raise self.scanError(filename, reply)

    def instream(self, content):
        """Send the content to clamd and return its reply, e.g. ``stream: OK``
        or ``stream: Eicar-Test-Signature FOUND``."""
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as connection:
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

    def scan_local(self, content, filename):
        executable = shutil.which(self.executable)
        if not executable:
            raise self.scanError(filename, '%s is not installed on this machine' % self.executable)
        try:
            result = subprocess.run([executable, '--no-summary', '-'], input=content,
                                    capture_output=True, timeout=self.local_timeout)
        except subprocess.TimeoutExpired as error:
            raise self.scanError(filename, error)
        # clamscan exits with 0 for no virus, 1 for a virus found, 2 for an error
        if result.returncode == 0:
            return None
        if result.returncode == 1:
            output = result.stdout.decode('utf-8', 'replace').splitlines()
            return self.threatName([line for line in output if line.endswith(' FOUND')][0])
        raise self.scanError(filename, result.stderr.decode('utf-8', 'replace').strip())


class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.radioButtonText(value='^.mode', values='https:HTTPS,tcp:TCP,local:Local', lbl='Mode')
        fb.textbox(value='^.url', lbl='Url', width='30em', hidden='^.mode?=#v!="https"')
        fb.passwordTextBox(value='^.token', lbl='Token', width='30em', hidden='^.mode?=#v!="https"')
        fb.textbox(value='^.host', lbl='Host', width='30em', hidden='^.mode?=#v!="tcp"')
        fb.numberTextBox(value='^.port', lbl='Port', placeholder=str(Service.default_port),
                         hidden='^.mode?=#v!="tcp"')
        fb.div(shutil.which(Service.executable) or '!!Not installed on this machine',
               lbl=Service.executable, hidden='^.mode?=#v!="local"')
