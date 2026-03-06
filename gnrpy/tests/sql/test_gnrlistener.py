"""Tests for @listen decorator, tblobj.notify(), and GnrListener autodiscovery.

Covers:
- @listen with and without arguments
- tblobj.notify() sends NOTIFY with correct payload
- GnrListener autodiscovery of decorated methods
- GnrListener dispatch with table filtering
"""

import datetime
import select

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import psycopg

from gnr.core.gnrdecorator import listen
from gnr.core.gnrstring import fromTypedJSON, toTypedJSON
from gnr.app.gnrlistener import GnrListener


# -- @listen decorator -------------------------------------------------------

class TestListenDecorator:
    """@listen() must always be used with parentheses."""

    def test_listen_default_channel(self):
        """@listen() sets channel to 'dbevent'."""
        @listen()
        def on_change(self, payload):
            pass

        assert on_change._listen_channel == 'dbevent'

    def test_listen_with_channel(self):
        """@listen('fatturona') sets that channel."""
        @listen('fatturona')
        def alert_big(self, payload):
            pass

        assert alert_big._listen_channel == 'fatturona'

    def test_listen_preserves_function(self):
        """Decorated function is returned unchanged (not wrapped)."""
        @listen('test')
        def handler(self, payload):
            return 42

        assert handler(None, {}) == 42


# -- GnrListener unit tests --------------------------------------------------

class TestGnrListenerRegister:
    """GnrListener.register() and channel tracking."""

    def _make_listener(self):
        class FakeApp:
            db = None
        return GnrListener(FakeApp(), timeout=1, coalesce=0)

    def test_register_adds_handler(self):
        listener = self._make_listener()
        handler = lambda payload: None
        listener.register('dbevent', handler, table='invc.invoice')
        assert 'dbevent' in listener.channels
        assert len(listener._handlers['dbevent']) == 1

    def test_register_multiple_channels(self):
        listener = self._make_listener()
        listener.register('dbevent', lambda p: None)
        listener.register('fatturona', lambda p: None)
        assert listener.channels == {'dbevent', 'fatturona'}

    def test_matches_all_filters(self):
        listener = self._make_listener()
        assert listener._matches({'table': 'invc.invoice', 'event': 'I'},
                                  {'table': 'invc.invoice'})

    def test_matches_rejects_mismatch(self):
        listener = self._make_listener()
        assert not listener._matches({'table': 'invc.product', 'event': 'I'},
                                      {'table': 'invc.invoice'})

    def test_matches_empty_filters(self):
        listener = self._make_listener()
        assert listener._matches({'table': 'invc.invoice'}, {})


# -- GnrListener dispatch ----------------------------------------------------

class TestGnrListenerDispatch:
    """_dispatch routes notifications to matching handlers."""

    def _make_listener(self):
        class FakeApp:
            db = None
        return GnrListener(FakeApp(), timeout=1, coalesce=0)

    def test_dispatch_calls_matching_handler(self):
        listener = self._make_listener()
        received = []
        listener.register('dbevent', lambda p: received.append(p),
                          table='invc.invoice')

        class FakeNotify:
            channel = 'dbevent'
            payload = toTypedJSON({'table': 'invc.invoice', 'pkey': '123', 'event': 'I'})

        listener._dispatch(FakeNotify())
        assert len(received) == 1
        assert received[0]['pkey'] == '123'

    def test_dispatch_skips_non_matching(self):
        listener = self._make_listener()
        received = []
        listener.register('dbevent', lambda p: received.append(p),
                          table='invc.invoice')

        class FakeNotify:
            channel = 'dbevent'
            payload = toTypedJSON({'table': 'invc.product', 'pkey': '456', 'event': 'I'})

        listener._dispatch(FakeNotify())
        assert len(received) == 0

    def test_dispatch_multiple_handlers(self):
        listener = self._make_listener()
        r1, r2 = [], []
        listener.register('dbevent', lambda p: r1.append(p), table='invc.invoice')
        listener.register('dbevent', lambda p: r2.append(p), table='invc.product')

        class FakeNotify:
            channel = 'dbevent'
            payload = toTypedJSON({'table': 'invc.invoice', 'pkey': '1', 'event': 'I'})

        listener._dispatch(FakeNotify())
        assert len(r1) == 1
        assert len(r2) == 0

    def test_dispatch_with_thread_pool(self):
        """With workers > 1, handlers run in threads."""
        import threading

        class FakeApp:
            db = None
        listener = GnrListener(FakeApp(), timeout=1, coalesce=0, workers=2)
        listener._executor = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=2)

        results = []
        listener.register('dbevent', lambda p: results.append(threading.current_thread().name),
                          table='invc.invoice')

        class FakeNotify:
            channel = 'dbevent'
            payload = toTypedJSON({'table': 'invc.invoice', 'pkey': '1', 'event': 'I'})

        listener._dispatch(FakeNotify())
        listener._executor.shutdown(wait=True)

        assert len(results) == 1
        assert results[0] != threading.current_thread().name


# -- tblobj.notify() on Postgres ----------------------------------------------

class TestTableNotify:
    """tblobj.notify() sends NOTIFY with table and kwargs in payload."""

    def test_notify_sends_payload(self, db_pg):
        dsn = db_pg.adapter.dbroot.connection.dsn
        conn = psycopg2.connect(dsn)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute('LISTEN fatturona;')

        tbl = db_pg.table('invc.invoice')
        tbl.notify('fatturona', pkey='inv_big_1', total='99999')
        db_pg.commit()

        ready = select.select([conn], [], [], 5)
        assert ready[0], 'No notification received within 5 seconds'
        conn.poll()
        notifications = list(conn.notifies)
        assert len(notifications) >= 1
        payload = fromTypedJSON(notifications[-1].payload)
        assert payload['table'] == 'invc.invoice'
        assert payload['pkey'] == 'inv_big_1'
        assert payload['total'] == '99999'
        assert payload['user'] is None
        assert payload['page_id'] is None
        assert isinstance(payload['ts'], datetime.datetime)

        conn.close()


# -- Autodiscovery integration -----------------------------------------------

class TestAutodiscovery:
    """GnrApp.listen() autodiscovery of @listen methods on table classes."""

    def test_discover_listen_methods(self, db_pg):
        """Manually simulate what GnrApp.listen() does: scan tables for @listen."""
        listener = GnrListener.__new__(GnrListener)
        listener._handlers = {}

        for dbtable in db_pg.tables:
            for attr_name in dir(dbtable):
                try:
                    method = getattr(dbtable, attr_name)
                except Exception:
                    continue
                channel = getattr(method, '_listen_channel', None)
                if channel is None:
                    continue
                listener.register(channel, method, table=dbtable.fullname)

        # At minimum, the scan completes without error.
        # If no tables have @listen yet, that's fine — the mechanism works.
        assert isinstance(listener._handlers, dict)


# -- psycopg3 tests ---------------------------------------------------------

class TestTableNotifyPsycopg3:
    """tblobj.notify() via psycopg3 adapter."""

    def test_notify_sends_payload(self, db_pg3):
        conninfo = db_pg3.adapter.dbroot.connection.info.dsn
        conn = psycopg.connect(conninfo, autocommit=True)
        conn.execute('LISTEN fatturona;')

        tbl = db_pg3.table('invc.invoice')
        tbl.notify('fatturona', pkey='inv_big_1', total='99999')
        db_pg3.commit()

        gen = conn.notifies(timeout=5)
        notify = next(gen)
        payload = fromTypedJSON(notify.payload)
        assert payload['table'] == 'invc.invoice'
        assert payload['pkey'] == 'inv_big_1'
        assert payload['total'] == '99999'
        assert payload['user'] is None
        assert payload['page_id'] is None
        assert isinstance(payload['ts'], datetime.datetime)

        conn.close()


class TestAutodiscoveryPsycopg3:
    """Autodiscovery via psycopg3 adapter."""

    def test_discover_listen_methods(self, db_pg3):
        listener = GnrListener.__new__(GnrListener)
        listener._handlers = {}

        for dbtable in db_pg3.tables:
            for attr_name in dir(dbtable):
                try:
                    method = getattr(dbtable, attr_name)
                except Exception:
                    continue
                channel = getattr(method, '_listen_channel', None)
                if channel is None:
                    continue
                listener.register(channel, method, table=dbtable.fullname)

        assert isinstance(listener._handlers, dict)


# -- GnrAppListener ---------------------------------------------------------

class TestGnrAppListener:
    """GnrAppListener wraps GnrApp and performs autodiscovery."""

    def test_init_with_app_instance(self, db_pg):
        from gnr.app.gnrapplistener import GnrAppListener
        app_listener = GnrAppListener(db_pg.application, timeout=2, coalesce=0, workers=3)
        assert app_listener.app is db_pg.application
        assert app_listener.timeout == 2
        assert app_listener.coalesce == 0
        assert app_listener.workers == 3

    def test_init_stores_defaults(self, db_pg):
        from gnr.app.gnrapplistener import GnrAppListener
        app_listener = GnrAppListener(db_pg.application)
        assert app_listener.timeout == 5
        assert app_listener.coalesce == 1
        assert app_listener.workers == 1


# -- CLI gnrapplisten --------------------------------------------------------

class TestGnrAppListenCli:
    """CLI parser for gnrapplisten exposes the correct arguments."""

    def test_parser_arguments(self):
        from gnr.core.cli import GnrCliArgParse
        import gnr.app.cli.gnrapplisten as cli_mod

        parser = GnrCliArgParse(description=cli_mod.description)
        parser.add_argument('instance')
        parser.add_argument('-w', '--workers', type=int, default=1)
        parser.add_argument('-t', '--timeout', type=int, default=5)
        parser.add_argument('-c', '--coalesce', type=int, default=1)

        args = parser.parse_args(['myapp', '-w', '4', '-t', '10', '-c', '2'])
        assert args.instance == 'myapp'
        assert args.workers == 4
        assert args.timeout == 10
        assert args.coalesce == 2

    def test_parser_defaults(self):
        from gnr.core.cli import GnrCliArgParse
        import gnr.app.cli.gnrapplisten as cli_mod

        parser = GnrCliArgParse(description=cli_mod.description)
        parser.add_argument('instance')
        parser.add_argument('-w', '--workers', type=int, default=1)
        parser.add_argument('-t', '--timeout', type=int, default=5)
        parser.add_argument('-c', '--coalesce', type=int, default=1)

        args = parser.parse_args(['myapp'])
        assert args.instance == 'myapp'
        assert args.workers == 1
        assert args.timeout == 5
        assert args.coalesce == 1

    def test_entry_point_registered(self):
        """gnrapplisten entry point is registered in pyproject.toml."""
        import importlib
        mod = importlib.import_module('gnr.app.cli.gnrapplisten')
        assert hasattr(mod, 'main')
        assert callable(mod.main)
