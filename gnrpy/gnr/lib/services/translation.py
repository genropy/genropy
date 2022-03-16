#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.lib.services import GnrBaseService,BaseServiceType

class ServiceType(BaseServiceType):
    def conf_translation(self):
        return dict(implementation=False)

class TranslationService(GnrBaseService):
    
    def __init__(self,parent,**kwargs):
        self.parent = parent

    def translate(self, what=None, to_language=None, from_language=None, **kwargs):
        pass

    @property
    def languages(self):
        pass

    @property
    def translator(self):
        pass
