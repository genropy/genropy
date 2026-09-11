"""Tests for the segment-aware drop of queued datachanges (#1259).

``BaseRegister.drop_datachanges`` discards the changes a page has not polled yet under a
subtree root. Matching them by character prefix also discards every pending change on a
sibling whose name merely begins with the same letters -- dropping ``gnr.batch.sync``
takes ``gnr.batch.sync_log.x`` with it, and the page never receives it. Same defect as
#1255/#1258 in the dropping direction, so the same predicate applies.

The register is a real ``SiteRegister`` built with the stand-in server of
``siteregister_datachanges_test``: its constructor only needs ``server.daemon.register``,
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


def _page_with_queue(*paths):
    reg = SiteRegister(_FakeServer(), sitename='testsite').page_register
    reg.create('p1')
    for path in paths:
        reg.set_datachange('p1', path, value=1)
    return reg


def _queued(reg):
    return [dc.path for dc in reg.get_datachanges('p1')]


def test_a_sibling_sharing_a_character_prefix_survives_the_drop():
    """The regression: 'sync_log' is not under 'sync', it only starts with its letters."""
    reg = _page_with_queue('gnr.batch.sync', 'gnr.batch.sync.thermo', 'gnr.batch.sync_log.x')
    reg.drop_datachanges('p1', 'gnr.batch.sync')
    assert _queued(reg) == ['gnr.batch.sync_log.x']


def test_the_dropped_path_itself_is_removed():
    reg = _page_with_queue('gnr.batch.sync')
    reg.drop_datachanges('p1', 'gnr.batch.sync')
    assert _queued(reg) == []


def test_the_whole_subtree_under_the_dropped_path_is_removed():
    reg = _page_with_queue('gnr.batch.sync.thermo', 'gnr.batch.sync.log.line')
    reg.drop_datachanges('p1', 'gnr.batch.sync')
    assert _queued(reg) == []


def test_an_unrelated_path_is_untouched():
    reg = _page_with_queue('other.node')
    reg.drop_datachanges('p1', 'gnr.batch.sync')
    assert _queued(reg) == ['other.node']


def test_a_longer_sibling_segment_survives_the_drop():
    """'srv.ab' shares every character of 'srv.a' but is a different node."""
    reg = _page_with_queue('srv.a', 'srv.ab.x')
    reg.drop_datachanges('p1', 'srv.a')
    assert _queued(reg) == ['srv.ab.x']


def test_dropping_on_a_missing_register_item_does_not_raise():
    reg = _page_with_queue('gnr.batch.sync')
    assert reg.drop_datachanges('unknown-page', 'gnr.batch.sync') is None
