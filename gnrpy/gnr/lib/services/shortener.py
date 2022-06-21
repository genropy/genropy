#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.lib.services import GnrBaseService,BaseServiceType



class ShortenerService(GnrBaseService):
    
    def __init__(self,parent,endpoint=None,**kwargs):
        self.parent = parent
        self.endpoint = endpoint


    def shorten(self,longUrl=None,**kwargs):
        raise NotImplementedError


    def remove(self,key=None,**kwargs):
        raise NotImplementedError


    def track(self,key=None,**kwargs):
        raise NotImplementedError

