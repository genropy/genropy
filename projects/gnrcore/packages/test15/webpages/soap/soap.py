#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#

from __future__ import print_function

from gnr.web.gnrsoappagenew import GnrSoapPage as page_factory



from rpclib.decorator import srpc
from rpclib.model.complex import Iterable
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
class GnrCustomWebPage(object):
    
    @srpc(String,String,_returns=String, _no_ctx=False)
    def test(self, pippo, pluto):
        print(pippo)
        print(x)
        print(pluto)
        return pluto
