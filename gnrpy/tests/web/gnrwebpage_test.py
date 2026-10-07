import pytest

from gnr.core.gnrlang import GnrException
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


class _ApplicationStub(object):
    localizer = None


class _ExceptionPageStub(object):
    user = 'tester'
    application = _ApplicationStub()


def test_exception_unknown_name_raises_naming_it():
    """An unregistered name raises GnrException naming it, not TypeError (#1622)."""
    with pytest.raises(GnrException) as excinfo:
        GnrWebPage.exception(_ExceptionPageStub(), 'no_such_name')
    assert 'no_such_name' in str(excinfo.value)


def test_exception_registered_name_returns_instance():
    exc = GnrWebPage.exception(_ExceptionPageStub(), 'generic')
    assert isinstance(exc, GnrException)
