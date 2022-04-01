#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.lib.services import BaseServiceType

class ServiceType(BaseServiceType):
    def conf_rst2html(self):
        return dict(implementation='rst2html')