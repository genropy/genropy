"""Tests for the segment-aware matching of ``subscribed_paths`` (#1255).

``BaseRegister._on_data_trigger`` filters a page store write against the paths the page
subscribed. Matching them by character prefix announces every write under ``formats.*``
to a page subscribed to ``form``; the client then rebuilds the client path by slicing off
the server prefix, so the change lands on a path nothing reads. A subscription must match
whole path segments only.

The page register is taken from a real ``SiteRegister`` built with the stand-in server of
``subscribed_tables_index_test``: its constructor only needs ``server.daemon.register``,
so no daemon and no Pyro are involved.
"""

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


def _announced(reg, page_id='page-1'):
    return [dc.path for dc in reg.get_datachanges(page_id)]


def _subscribed_page(subscribed='form'):
    reg = _register()
    reg.create('page-1')
    reg.subscribe_path('page-1', subscribed)
    return reg, reg.get_item_data('page-1')


def test_a_sibling_sharing_a_character_prefix_is_not_announced():
    """The regression: 'formats' is not under 'form', it only starts with its letters."""
    reg, data = _subscribed_page()
    data.setItem('form.name', 'Ada')
    data.setItem('formats.date', 'dmy')
    announced = _announced(reg)
    assert not [p for p in announced if p == 'formats' or p.startswith('formats.')]


def test_the_subscribed_subtree_is_still_announced():
    reg, data = _subscribed_page()
    data.setItem('form.name', 'Ada')
    data.setItem('formats.date', 'dmy')
    assert 'form.name' in _announced(reg)


def test_a_write_on_the_subscribed_path_itself_is_announced():
    reg, data = _subscribed_page()
    data.setItem('form', 'Ada')
    assert 'form' in _announced(reg)


def test_a_deeper_write_under_the_subscription_is_announced():
    reg, data = _subscribed_page()
    data.setItem('form.address.city', 'Turin')
    assert 'form.address.city' in _announced(reg)


def test_an_unrelated_path_is_never_announced():
    reg, data = _subscribed_page()
    data.setItem('other.name', 'Ada')
    assert _announced(reg) == []


def test_a_segment_subscription_does_not_match_a_longer_sibling_segment():
    """'srv.ab' shares every character of 'srv.a' but is a different node."""
    reg, data = _subscribed_page(subscribed='srv.a')
    data.setItem('srv.ab.x', 1)
    assert not [p for p in _announced(reg) if p.startswith('srv.ab')]
