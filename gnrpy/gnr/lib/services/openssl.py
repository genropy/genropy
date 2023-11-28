#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.lib.services import GnrBaseService,BaseServiceType


class ServiceType(BaseServiceType):
    def conf_git(self):
        return dict(implementation='openssl')

class OpenSSLService(GnrBaseService):

    def __init__(self,parent,**kwargs):
        self.parent = parent

