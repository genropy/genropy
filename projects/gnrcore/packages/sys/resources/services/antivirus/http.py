#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ipaddress
import socket
from urllib.parse import urlsplit

import requests

from gnr.lib.services.antivirus import AntivirusService
from gnr.web.gnrbaseclasses import BaseComponent


class Service(AntivirusService):
    """Scans through an HTTP endpoint in front of ClamAV.

    Contract of the endpoint:

    - request: ``POST <url>``, body = the bytes of the file, headers
      ``Authorization: Bearer <token>`` and ``Content-Type: application/octet-stream``;
    - answer ``200`` with the JSON ``{"threat": null}`` for a clean content,
      ``{"threat": "<name>"}`` for an infected one;
    - any other answer means that the content was not scanned.

    An ``https://`` url is always accepted. An ``http://`` url is accepted only
    when its host resolves to private or loopback addresses, e.g. a service
    inside the same Kubernetes cluster: towards any other host the token and
    the file would travel in clear."""

    def __init__(self, parent, url=None, token=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.url = url
        self.token = token

    def scan(self, content=None, filename=None, **kwargs):
        self.checkUrl()
        try:
            response = requests.post(self.url, data=content, timeout=self.timeout,
                                     headers={'Authorization': 'Bearer %s' % self.token,
                                              'Content-Type': 'application/octet-stream'})
        except requests.RequestException as error:
            raise self.unavailable(error)
        if response.status_code != 200:
            raise self.unavailable('the endpoint answered %s' % response.status_code)
        try:
            return response.json()['threat']
        except (ValueError, KeyError, TypeError):
            raise self.unavailable('unexpected answer from the endpoint: %r' % response.text[:200])

    def checkUrl(self):
        """Refuse a url that is neither https nor http towards an internal host"""
        parts = urlsplit(self.url or '')
        if parts.scheme == 'https' and parts.hostname:
            return
        if parts.scheme != 'http' or not parts.hostname:
            raise self.unavailable('%r is not an http or https url' % self.url)
        try:
            addresses = {info[4][0] for info in socket.getaddrinfo(parts.hostname, parts.port or 80)}
        except OSError as error:
            raise self.unavailable(error)
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not (ip.is_private or ip.is_loopback):
                raise self.unavailable('http is accepted only towards private or loopback addresses, '
                                       '%s resolves to %s: use https' % (parts.hostname, address))


class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.url', lbl='Url', width='30em')
        fb.passwordTextBox(value='^.token', lbl='Token', width='30em')
        fb.numberTextBox(value='^.timeout', lbl='Timeout (seconds)',
                         placeholder=str(Service.default_timeout))
