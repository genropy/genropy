#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#

from rpclib.decorator import srpc
from rpclib.model.primitive import String

from gnr.web.gnrsoappagenew import GnrSoapPage

class GnrCustomWebPage(object):
    page_factory = GnrSoapPage
    @srpc(String,String,_returns=String, _no_ctx=False)
    def test(self, pippo, pluto):
        print(pippo)
        raise Exception("x exception")
        print(pluto)
        return pluto
