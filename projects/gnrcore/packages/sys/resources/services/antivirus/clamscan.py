#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import subprocess

from gnr.lib.services.antivirus import AntivirusService
from gnr.web.gnrbaseclasses import BaseComponent


class Service(AntivirusService):
    """Scans with the ``clamscan`` executable of the machine the site runs on,
    started once for every scan with the content on its standard input.

    clamscan loads the signatures at every start, so a scan takes seconds:
    meant for development, where no clamd daemon is running."""
    default_timeout = 300
    executable = 'clamscan'

    def scan(self, content=None, filename=None, **kwargs):
        executable = shutil.which(self.executable)
        if not executable:
            raise self.unavailable('%s is not installed on this machine' % self.executable)
        try:
            result = subprocess.run([executable, '--no-summary', '-'], input=content,
                                    capture_output=True, timeout=self.timeout)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise self.unavailable(error)
        # clamscan exits with 0 for no virus, 1 for a virus found, 2 for an error
        if result.returncode == 0:
            return None
        if result.returncode == 1:
            output = result.stdout.decode('utf-8', 'replace').splitlines()
            found = [line for line in output if line.endswith(' FOUND')]
            if found:
                return self.threatName(found[0])
        raise self.unavailable('%s exited with %s: %s' % (self.executable, result.returncode,
                                                          result.stderr.decode('utf-8', 'replace').strip()))


class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.div(shutil.which(Service.executable) or '!!Not installed on this machine',
               lbl=Service.executable)
        fb.numberTextBox(value='^.timeout', lbl='Timeout (seconds)',
                         placeholder=str(Service.default_timeout))
