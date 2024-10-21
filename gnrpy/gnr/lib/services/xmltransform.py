#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.lib.services import BaseServiceType,GnrBaseService

class ServiceType(BaseServiceType):
    
    def conf_xmltransform(self):
        return dict(implementation='xmltransform')


class XmlTransformService(GnrBaseService):
    
    def __init__(self,parent, **kwargs):
        self.parent = parent

    