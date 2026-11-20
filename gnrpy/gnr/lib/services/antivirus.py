#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gnr.lib.services import GnrBaseService


class AntivirusUnavailable(Exception):
    """Raised by an antivirus service that could not scan a content.

    Its message is the technical reason. The site logs it and tells the user
    that the antivirus service is not available (see ``GnrWsgiSite.scanUpload``)."""


class AntivirusService(GnrBaseService):
    """Base class of the services that scan a file content for threats.

    When a service named ``antivirus`` is configured, the site scans every
    uploaded file with it before any upload hook runs and before the file is
    stored (see ``GnrWsgiSite.scanUpload``). Each implementation reaches the
    scanner in its own way: ``clamscan`` (a local process), ``clamd`` (a ClamAV
    daemon over TCP), ``http`` (an HTTP endpoint in front of ClamAV)."""
    default_timeout = 30

    def __init__(self, parent, timeout=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.timeout = float(timeout or self.default_timeout)

    def scan(self, content=None, filename=None, **kwargs):
        """Scan a file content.

        :param content: the bytes to scan
        :param filename: the name of the file
        :returns: the name of the threat found, ``None`` when the content is clean
        :raises AntivirusUnavailable: when the content could not be scanned"""
        raise NotImplementedError

    def unavailable(self, reason):
        """The exception that reports a scan that could not be done, with its reason"""
        return AntivirusUnavailable('antivirus %s (%s): %s'
                                    % (self.service_name, self.service_implementation, reason))

    def threatName(self, line):
        """The name in a ClamAV line like ``stream: Eicar-Test-Signature FOUND``"""
        return line[:-len(' FOUND')].split(': ', 1)[1]
