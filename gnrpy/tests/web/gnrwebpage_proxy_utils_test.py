from types import SimpleNamespace

from gnr.web.gnrwebpage_proxy.utils import GnrWebUtils


class RecordingPage(object):
    def __init__(self):
        self.site = SimpleNamespace(site_path='/tmp/site')
        self.filename = '/tmp/site/page.py'
        self.canonical_filename = self.filename
        self.client_updates = []

    def _subscribe_event(self, name, proxy):
        pass

    def localize(self, value):
        return value

    def setInClientData(self, path, value, **kwargs):
        self.client_updates.append((path, value, kwargs))


def _utils():
    page = RecordingPage()
    return GnrWebUtils(page), page


def test_quickthermo_empty_list_yields_nothing_and_sends_no_update():
    utils, page = _utils()
    assert list(utils.quickThermo([])) == []
    assert page.client_updates == []


def test_quickthermo_empty_generator_with_maxidx():
    utils, page = _utils()
    assert list(utils.quickThermo(iter(()), maxidx=5)) == []
    assert page.client_updates == []


def test_quickthermo_non_empty_iterable_updates_client():
    utils, page = _utils()
    assert list(utils.quickThermo(['a', 'b'])) == ['a', 'b']
    assert [kw for _, _, kw in page.client_updates] == [
        dict(idx=1, maxidx=2, lbl='a'),
        dict(idx=2, maxidx=2, lbl='b'),
        dict(idx=2, maxidx=2, lbl='b'),
    ]
    assert all(path == 'gnr.lockScreen.thermo' for path, _, _ in page.client_updates)
    assert 'value="2"' in page.client_updates[-1][1]
