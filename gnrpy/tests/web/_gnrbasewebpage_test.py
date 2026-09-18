"""Regression tests for the makedirs race in ``pageLocalDocument`` (#1033).

``pageLocalDocument`` used to check ``os.path.isdir(folder)`` and then call
``os.makedirs(folder)``: a classic check-then-act race. Two concurrent
requests belonging to the same page could both pass the ``isdir`` check and
the second one would blow up with ``FileExistsError``. The fix makes the
call idempotent with ``os.makedirs(folder, exist_ok=True)``.

``pageLocalDocument`` only touches ``self.connectionFolder`` and
``self.page_id``/``page_id``, so it is exercised unbound against a minimal
fake, following the precedent in ``gnrwsgisite_folder_cleanup_test.py``.
"""

import os
import threading

from gnr.web._gnrbasewebpage import GnrBaseWebPage


class _FakePage:
    """Bag of attributes accessed by ``pageLocalDocument``. The method is
    invoked unbound: ``GnrBaseWebPage.pageLocalDocument(_FakePage(...), ...)``."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_pagelocaldocument_creates_folder(tmp_path):
    """First call creates the per-page folder and returns the doc path."""
    page = _FakePage(connectionFolder=str(tmp_path), page_id='page1')

    result = GnrBaseWebPage.pageLocalDocument(page, 'selection.xml')

    assert result == os.path.join(str(tmp_path), 'page1', 'selection.xml')
    assert os.path.isdir(os.path.join(str(tmp_path), 'page1'))


def test_pagelocaldocument_repeated_call_does_not_raise(tmp_path):
    """Calling it twice for the same page (folder already exists) must not
    raise FileExistsError: this is the exact sequence the TOCTOU bug hit."""
    page = _FakePage(connectionFolder=str(tmp_path), page_id='page1')

    first = GnrBaseWebPage.pageLocalDocument(page, 'selection.xml')
    second = GnrBaseWebPage.pageLocalDocument(page, 'selection.xml')

    assert first == second
    assert os.path.isdir(os.path.join(str(tmp_path), 'page1'))


def test_pagelocaldocument_concurrent_calls_do_not_raise(tmp_path):
    """Two threads racing to create the same page folder must not raise:
    this reproduces the production FileExistsError from concurrent
    requests hitting checkFreezedSelection -> unfreezeSelection ->
    pageLocalDocument for the same page."""
    page = _FakePage(connectionFolder=str(tmp_path), page_id='page1')
    barrier = threading.Barrier(2)
    errors = []

    def _call():
        try:
            barrier.wait(timeout=5)
            GnrBaseWebPage.pageLocalDocument(page, 'selection.xml')
        except Exception as exc:  # noqa: BLE001 - we want to see any failure
            errors.append(exc)

    threads = [threading.Thread(target=_call) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert errors == [], f"pageLocalDocument raised under concurrency: {errors}"
    assert os.path.isdir(os.path.join(str(tmp_path), 'page1'))
