# -*- coding: utf-8 -*-

"""@autocast: the strings a client sends, converted before the method body runs

Everything an RPC receives from the browser arrives as text. `@autocast` declares
a dtype per parameter - `L` int, `D` date, `N` Decimal, the same codes the column
definitions use - and the framework converts each one on the way in, so the method
works with real Python types instead of parsing them itself. The tree renders the
Bag the method returns: what it shows is the value AS the server built it.
"""

from gnr.core.gnrdecorator import public_method, autocast
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_basic(self, pane):
        """Type an integer, a date and a decimal: the RPC receives them already converted"""
        fb = pane.formbuilder(datapath='.test1')
        fb.textbox('^.a', lbl='Type an integer')
        fb.textbox('^.b', lbl='Type a date YYYY-MM-DD')
        fb.textbox('^.c', lbl='Type a decimal')
        pane.button('Cast types', action='FIRE casting')
        fb.dataRpc('.result', self.getCastedTypes, a='=.a', b='=.b', c='=.c', _fired='^casting')
        pane.tree(storepath='.test1.result')

    @public_method
    @autocast(a='L', b='D', c='N')
    def getCastedTypes(self, a=None, b=None, c=None):
        return Bag(dict(integer_p=a, date_p=b, decimal_p=c))
