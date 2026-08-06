import importlib.util
import os

import pytest

# GnrCustomWebPage lives under projects/gnrcore/ which is not on the
# default test sys.path. Load it directly from the file system so the
# test can run without requiring a full GenroPy site setup.
_thpage_module_path = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir,
    'projects', 'gnrcore', 'packages', 'sys', 'webpages', 'thpage.py',
)
_thpage_module_path = os.path.normpath(_thpage_module_path)


def _get_page_class():
    """Import GnrCustomWebPage from the thpage module."""
    spec = importlib.util.spec_from_file_location('thpage', _thpage_module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.GnrCustomWebPage


GnrCustomWebPage = _get_page_class()


def _make_page():
    """A bare page instance, good enough to exercise onIniting's URL guards.

    onIniting validates request_args before doing any framework work
    (the mixinComponent calls), so those are stubbed here only to let the
    valid-argument cases run past the guards without raising. The guard
    logic itself runs unmodified, straight from the real module.
    """
    page = GnrCustomWebPage()
    page.mixinComponent = lambda *args, **kwargs: None
    page._th_getResourceName = lambda *args, **kwargs: 'stub_resource'
    page.packageId = 'stub_pkg'
    return page


def test_onIniting_rejects_too_few_arguments():
    page = _make_page()
    with pytest.raises(ValueError, match='Missing table arguments in URL'):
        page.onIniting(('sys',), {})


def test_onIniting_rejects_too_many_arguments():
    page = _make_page()
    # Mirrors the malformed URL from the reported issue:
    # /sys/thpage/<pkg>/:/_storage/documenti/<folder>/<id>/<id>.pdf
    request_args = ('sys', ':', '_storage', 'documenti', 'folder', 'id', 'id.pdf')
    with pytest.raises(ValueError, match='Too many table arguments in URL'):
        page.onIniting(request_args, {})


def test_onIniting_accepts_two_arguments():
    page = _make_page()
    page.onIniting(('sys', 'mytable'), {})  # must not raise


def test_onIniting_accepts_three_arguments():
    page = _make_page()
    page.onIniting(('sys', 'mytable', '1'), {})  # must not raise
