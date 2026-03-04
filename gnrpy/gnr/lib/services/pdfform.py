#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.core.gnrlang import  GnrException
from gnr.lib.services import GnrBaseService,BaseServiceType

class HtmlToPdfError(GnrException):
    pass
    
class ServiceType(BaseServiceType):
    def conf_pdfform(self):
        return dict(implementation='pdftk')

class PdfFormService(GnrBaseService):
    def __init__(self,parent, **kwargs):
        self.parent = parent

    def getFields(self, template=None):
        pass

    def fillForm(self,template=None, values=None, output=None):
        pass


