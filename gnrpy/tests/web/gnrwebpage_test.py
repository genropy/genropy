from gnr.web.gnrwebpage import GnrWebPage


class _PaneStub(object):
    def __init__(self):
        self.captured = None

    def contentPane(self, **kwargs):
        self.captured = kwargs
        return self


class _PageStub(object):
    def bf_value(self, box, **kwargs):
        return box


def test_bagFieldDispatcher_without_resource_does_not_raise():
    """resource=None must not raise UnboundLocalError on mixinedClass (#1101)."""
    page = _PageStub()
    pane = _PaneStub()
    GnrWebPage.bagFieldDispatcher(page, pane, resource=None, field='value')
    assert pane.captured['bagfieldmodule'] is None
