import sys
from types import SimpleNamespace

import pytest

from gnr.web.serverwsgi import _reloader_type


@pytest.mark.parametrize('major,expected', [(7, 'stat'), (6, 'auto'), (None, 'auto')])
def test_reloader_type(monkeypatch, major, expected):
    version = SimpleNamespace(VERSION_MAJOR=major) if major is not None else None
    monkeypatch.setitem(sys.modules, 'watchdog.version', version)
    assert _reloader_type() == expected
