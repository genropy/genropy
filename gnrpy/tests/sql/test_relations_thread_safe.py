"""Test that RelationTreeResolver.load() does not deadlock on exception.

Issue #548: if _fields() raises, the lock acquired at line 107 of
resolvers.py is never released (no try/finally), causing deadlock
on subsequent calls from another thread.
"""

import threading
from unittest.mock import MagicMock

import pytest

from gnr.sql.gnrsqlmodel.resolvers import RelationTreeResolver


def _make_resolver_with_failing_fields():
    """Create a RelationTreeResolver whose _fields() raises RuntimeError."""
    pkg_mock = MagicMock()
    pkg_mock.table.return_value = {'columns': MagicMock(values=lambda: []),
                                   'virtual_columns': MagicMock(values=lambda: [])}

    dbroot = MagicMock()
    dbroot.package.return_value = pkg_mock
    dbroot.model.table.return_value = MagicMock()
    dbroot.model.relations.return_value = None

    resolver = RelationTreeResolver(
        main_tbl='test.broken',
        tbl_name='broken',
        pkg_name='test',
        cacheTime=0,
    )
    resolver.setDbroot(dbroot)

    # Make _fields() raise on first call
    resolver._fields = MagicMock(side_effect=RuntimeError('simulated failure in _fields'))
    return resolver


class TestRelationTreeResolverDeadlock:
    """Reproduce the deadlock bug from issue #548."""

    def test_lock_not_released_after_exception(self):
        """After _fields() raises, a second call from another thread must not deadlock."""
        resolver = _make_resolver_with_failing_fields()

        # First call: must raise RuntimeError
        with pytest.raises(RuntimeError, match='simulated failure'):
            resolver.load()

        # Second call from a different thread: if the lock was not released,
        # this will deadlock. We use a timeout to detect it.
        result = {}

        def second_call():
            try:
                resolver.load()
                result['ok'] = True
            except RuntimeError:
                # Expected — _fields still raises, but we got past the lock
                result['ok'] = True
            except Exception as e:
                result['error'] = str(e)

        t = threading.Thread(target=second_call)
        t.start()
        t.join(timeout=2.0)

        if t.is_alive():
            pytest.fail(
                'DEADLOCK: second thread blocked on lock that was never released '
                'after _fields() exception (issue #548)'
            )

        assert result.get('ok'), 'Second call should complete without deadlock'

    def test_lock_released_with_rlock_same_thread(self):
        """RLock allows re-entry from the same thread, so same-thread retry works.

        This test documents that the bug is only visible cross-thread.
        With RLock, the same thread can re-acquire the lock even if it
        was not released — masking the bug in single-threaded usage.
        """
        resolver = _make_resolver_with_failing_fields()

        with pytest.raises(RuntimeError, match='simulated failure'):
            resolver.load()

        # Same thread: RLock allows re-entry, so this does NOT deadlock.
        # But it still raises because _fields still fails.
        with pytest.raises(RuntimeError, match='simulated failure'):
            resolver.load()
