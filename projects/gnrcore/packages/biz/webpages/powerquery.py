#  -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:BaseRpc'

    def saved_query(self,*args,**kwargs):
        self.getCallArgs('method','pkg','table','queryName')
        raise Exception("x exception")
