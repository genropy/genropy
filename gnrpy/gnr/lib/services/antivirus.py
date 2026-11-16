#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gnr.lib.services import GnrBaseService


class AntivirusService(GnrBaseService):
    """Base class of the services that scan a file content for threats.

    When a service named ``antivirus`` is configured, the site scans every
    uploaded file with it before storing it (see ``GnrWsgiSite.uploadFile``)."""

    def scan(self, content=None, filename=None, **kwargs):
        """Scan a file content.

        :param content: the bytes to scan
        :param filename: the name of the file, used in the error messages
        :returns: the name of the threat found, ``None`` when the content is clean
        :raises GnrException: when the content could not be scanned"""
        raise NotImplementedError
