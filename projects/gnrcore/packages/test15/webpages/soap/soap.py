#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#

from rpclib.decorator import srpc
from rpclib.model.primitive import String

from gnr.web.gnrsoappagenew import GnrSoapPage as page_factory # noqa: F401

class GnrCustomWebPage(object):
    
    @srpc(String,String,_returns=String, _no_ctx=False)
    def test(self, pippo, pluto):
        print(pippo)
        raise Exception("x exception")
        print(pluto)
        return pluto
