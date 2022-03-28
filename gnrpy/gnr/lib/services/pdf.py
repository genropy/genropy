#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-


from gnr.lib.services import GnrBaseService,BaseServiceType

class ServiceType(BaseServiceType):
    def conf_pdf(self):
        return dict(implementation='pypdf')


class PdfService(GnrBaseService):
    def __init__(self,parent,**kwargs):
        self.parent = parent

    def joinPdf(self, pdf_list, output_filepath):
        pass
