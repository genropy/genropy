#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module gnrwebcore : core module for genropy web framework
# Copyright (c)     : 2004 - 2019 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari 
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

#Copyright (c) 2019 Softwell. All rights reserved.

from gnr.core.gnrbag import Bag
from gnr.web.gnrwsgisite import GnrWsgiSite


class FakeStore(object):
    """Null replacement for the daemon backed ServerStore.

    Always empty: reads give back the default, writes are dropped. It is also
    a context manager, because the real store is normally entered as
    ``with register.globalStore() as store:``.
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        return False

    def getItem(self, path, default=None, **kwargs):
        return default

    def setItem(self, path, value=None, **kwargs):
        pass

    def delItem(self, path, **kwargs):
        pass


class FakeSiteRegister(object):
    """Null replacement for the remote SiteRegister proxy.

    Provides the read only surface the DataCollector asks for, so that a site
    can be built without a gnrdaemon answering on the other side.
    """
    def users(self, **kwargs):
        return {}

    def pages(self, **kwargs):
        return {}

    def connections(self, **kwargs):
        return {}

    def counters(self):
        return {}


class FakeRegister(object):
    """Register stub for sites running without a gnrdaemon.

    Covers the part of SiteRegisterClient a site touches outside of a real
    request: the siteregister proxy handed to the DataCollector, the per scope
    stores and the db environment of a page.
    """
    def __init__(self, site, **kwargs):
        self.site = site
        self.siteregister = FakeSiteRegister()

    def globalStore(self, triggered=False):
        return FakeStore()

    def pageStore(self, page_id=None, triggered=False):
        return FakeStore()

    def connectionStore(self, connection_id=None, triggered=False):
        return FakeStore()

    def userStore(self, user=None, triggered=False):
        return FakeStore()

    def get_dbenv(self, register_item_id, register_name=None):
        return Bag()


class GnrDummySite(GnrWsgiSite):
    """Site without a register server, for headless, CLI and test contexts."""

    # GnrWsgiSite keeps the register on the domain proxy; here it lives on the
    # site itself, so it must exist before __init__ touches self.register.
    _register = None

    @property
    def register(self):
        if self._register is None:
            self._register = FakeRegister(self)
        return self._register

    @property
    def main_register(self):
        """Shadows the daemon backed rootDomain register of GnrWsgiSite."""
        return self.register

    def getSubscribedTables(self,*args):
        return []

    def allSubscribedTables(self):
        return []
