"""Tests for the boolean contract of ``setInClientData``/``set_datachange`` (#1253).

Filing a data change against a page that is no longer registered is a silent no-op: the
change is dropped and the caller has no way to tell. The register now answers with a
boolean, so a caller that cares can react instead of assuming delivery.

The page register is taken from a real ``SiteRegister``, built with a stand-in server:
its constructor only needs ``server.daemon.register`` for the remote-bag handler, so no
daemon and no Pyro are involved.
"""

from gnr.core.gnrbag import Bag
from gnr.web.daemon.siteregister import SiteRegister


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


def _register():
    return SiteRegister(_FakeServer(), sitename='testsite').page_register


# ---------------------------------------------------------------------------
# single page
# ---------------------------------------------------------------------------


def test_setinclientdata_on_a_live_page_returns_true():
    reg = _register()
    reg.create('p1')
    assert reg.setInClientData('a.b', value=1, page_id='p1') is True
    assert [dc.path for dc in reg.get_datachanges('p1')] == ['a.b']


def test_setinclientdata_on_an_unknown_page_returns_false():
    reg = _register()
    reg.create('p1')
    assert reg.setInClientData('a.b', value=1, page_id='ghost') is False
    assert reg.get_datachanges('p1') == []


def test_setinclientdata_on_a_dropped_page_returns_false():
    reg = _register()
    reg.create('p1')
    reg.drop('p1')
    assert reg.setInClientData('a.b', value=1, page_id='p1') is False


# ---------------------------------------------------------------------------
# filters
# ---------------------------------------------------------------------------


def test_setinclientdata_with_filters_matching_live_pages_returns_true():
    reg = _register()
    reg.create('p1', pagename='dashboard')
    reg.create('p2', pagename='dashboard')
    reg.create('p3', pagename='other')
    assert reg.setInClientData('a.b', value=1, filters='pagename:dashboard') is True
    assert len(reg.get_datachanges('p1')) == 1
    assert len(reg.get_datachanges('p2')) == 1
    assert reg.get_datachanges('p3') == []


def test_setinclientdata_with_filters_matching_nothing_returns_true():
    # vacuous truth: no page matched, so no change was dropped
    reg = _register()
    reg.create('p1', pagename='dashboard')
    assert reg.setInClientData('a.b', value=1, filters='pagename:nosuchpage') is True
    assert reg.get_datachanges('p1') == []


# ---------------------------------------------------------------------------
# Bag path
# ---------------------------------------------------------------------------


def _changebag():
    changes = Bag()
    changes.setItem('c0', 1, _client_path='a.b')
    changes.setItem('c1', 2, _client_path='a.c')
    return changes


def test_setinclientdata_with_a_bag_path_on_a_live_page_returns_true():
    reg = _register()
    reg.create('p1')
    assert reg.setInClientData(_changebag(), page_id='p1') is True
    assert [dc.path for dc in reg.get_datachanges('p1')] == ['a.b', 'a.c']


def test_setinclientdata_with_a_bag_path_on_an_unknown_page_returns_false():
    reg = _register()
    reg.create('p1')
    assert reg.setInClientData(_changebag(), page_id='ghost') is False


# ---------------------------------------------------------------------------
# the underlying primitive
# ---------------------------------------------------------------------------


def test_set_datachange_returns_true_when_filed_and_false_when_dropped():
    reg = _register()
    reg.create('p1')
    assert reg.set_datachange('p1', 'a.b', value=1) is True
    assert reg.set_datachange('ghost', 'a.b', value=1) is False
