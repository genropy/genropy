#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.web.gnrheadlesspage import GnrHeadlessPage as page_factory # noqa: F401
from gnr.core.gnrdecorator import public_method
class GnrCustomWebPage(object):
    skip_connection=False
    pass

    @public_method
    def ws_doLogin(self, rootenv=None,login=None,guestName=None, **kwargs):
        self.doLogin(login=login,guestName=guestName,rootenv=rootenv,**kwargs)
