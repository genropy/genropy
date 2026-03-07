"""Tests for the adapter.notify() and _dbNotify infrastructure (issue #663).

Verifies that:
- adapter.notify() is a no-op on SQLite
- adapter.notify() sends NOTIFY on Postgres
- _dbNotify builds correct payloads for insert/update/delete
- notify=True sends minimal payload
- notify='field1,field2' includes fields in payload
- update only includes changed fields
- LISTEN receives the notification with correct payload
"""

import json
import select

from gnr.sql.adapters._gnrbaseadapter import SqlDbAdapter


# -- Base adapter: notify is a no-op ---------------------------------------

class TestBaseAdapterNotify:
    """Base SqlDbAdapter.notify() must be a no-op (not raise)."""

    def test_notify_noop(self):
        """notify() on base adapter does nothing and does not raise."""

        class FakeDbRoot:
            fixed_schema = False

        adapter = SqlDbAdapter(FakeDbRoot())
        adapter.notify('dbevent')
        adapter.notify('dbevent', payload='{"table":"t"}')
        adapter.notify('dbevent', payload='{"table":"t"}', autocommit=True)


# -- SQLite: notify is a no-op --------------------------------------------

class TestSqliteNotify:
    """SQLite adapter inherits the no-op notify."""

    def test_notify_silent(self):
        from gnr.sql.adapters.gnrsqlite import SqlDbAdapter as SqliteAdapter

        class FakeDbRoot:
            fixed_schema = False

        adapter = SqliteAdapter(FakeDbRoot())
        adapter.notify('dbevent', payload='test')


# -- Postgres: notify sends NOTIFY ----------------------------------------

class TestPostgresNotify:
    """Postgres adapter.notify() must send a NOTIFY."""

    def test_notify_without_payload(self, db_pg):
        db_pg.adapter.notify('test_channel')
        db_pg.commit()

    def test_notify_with_payload(self, db_pg):
        db_pg.adapter.notify('test_channel', payload='hello world')
        db_pg.commit()

    def test_notify_with_json_payload(self, db_pg):
        payload = json.dumps({'table': 'invc.invoice', 'pkey': '123', 'event': 'I'})
        db_pg.adapter.notify('dbevent', payload=payload)
        db_pg.commit()

    def test_notify_escapes_quotes(self, db_pg):
        payload = json.dumps({'note': "it's a test"})
        db_pg.adapter.notify('dbevent', payload=payload)
        db_pg.commit()


# -- LISTEN/NOTIFY integration --------------------------------------------

class TestListenNotify:
    """End-to-end LISTEN/NOTIFY on Postgres."""

    def test_listen_receives_notify(self, db_pg):
        """A LISTEN connection must receive NOTIFY with payload."""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        dsn = db_pg.adapter.dbroot.connection.dsn
        listener = psycopg2.connect(dsn)
        listener.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = listener.cursor()
        cur.execute('LISTEN test_listen;')

        expected_payload = json.dumps({'table': 'invc.invoice', 'event': 'I', 'pkey': 'x1'})
        db_pg.adapter.notify('test_listen', payload=expected_payload)
        db_pg.commit()

        ready = select.select([listener], [], [], 5)
        assert ready[0], 'No notification received within 5 seconds'
        listener.poll()
        notifications = list(listener.notifies)
        assert len(notifications) >= 1
        received = json.loads(notifications[0].payload)
        assert received['table'] == 'invc.invoice'
        assert received['event'] == 'I'
        assert received['pkey'] == 'x1'

        listener.close()


# -- _dbNotify payload construction ----------------------------------------

class TestDbNotifyPayload:
    """_dbNotify must build correct payloads based on notify attribute."""

    def _set_notify(self, tblobj, value):
        tblobj.attributes['notify'] = value

    def _clear_notify(self, tblobj):
        if 'notify' in tblobj.attributes:
            del tblobj.attributes['notify']

    def test_no_notify_attribute(self, db_pg):
        """No notify attribute means no NOTIFY is sent."""
        tbl = db_pg.table('invc.product')
        self._clear_notify(tbl)
        record = {'id': 'test_no_notify', 'code': 'NNN', 'description': 'no notify'}
        db_pg._dbNotify(tbl, 'I', record)
        db_pg.commit()

    def test_notify_true_insert(self, db_pg):
        """notify=True on insert sends {table, pkey, event}."""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        dsn = db_pg.adapter.dbroot.connection.dsn
        listener = psycopg2.connect(dsn)
        listener.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = listener.cursor()
        cur.execute('LISTEN dbevent;')

        tbl = db_pg.table('invc.product')
        self._set_notify(tbl, True)
        try:
            record = {'id': 'notify_test_1', 'code': 'NT1', 'description': 'test'}
            db_pg._dbNotify(tbl, 'I', record)
            db_pg.commit()

            ready = select.select([listener], [], [], 5)
            assert ready[0], 'No notification received'
            listener.poll()
            notifications = list(listener.notifies)
            assert len(notifications) >= 1
            payload = json.loads(notifications[-1].payload)
            assert payload['table'] == 'invc.product'
            assert payload['pkey'] == 'notify_test_1'
            assert payload['event'] == 'I'
            assert 'fields' not in payload
        finally:
            self._clear_notify(tbl)
            listener.close()

    def test_notify_fields_delete(self, db_pg):
        """notify='invoice_id' on delete includes field values."""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        dsn = db_pg.adapter.dbroot.connection.dsn
        listener = psycopg2.connect(dsn)
        listener.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = listener.cursor()
        cur.execute('LISTEN dbevent;')

        tbl = db_pg.table('invc.invoice_row')
        self._set_notify(tbl, 'invoice_id,product_id')
        try:
            record = {'id': 'row_del_1', 'invoice_id': 'inv_001', 'product_id': 'prod_42'}
            db_pg._dbNotify(tbl, 'D', record)
            db_pg.commit()

            ready = select.select([listener], [], [], 5)
            assert ready[0], 'No notification received'
            listener.poll()
            notifications = list(listener.notifies)
            payload = json.loads(notifications[-1].payload)
            assert payload['event'] == 'D'
            assert payload['fields']['invoice_id'] == 'inv_001'
            assert payload['fields']['product_id'] == 'prod_42'
        finally:
            self._clear_notify(tbl)
            listener.close()

    def test_notify_fields_update_changed(self, db_pg):
        """notify='invoice_id' on update includes only changed fields."""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        dsn = db_pg.adapter.dbroot.connection.dsn
        listener = psycopg2.connect(dsn)
        listener.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = listener.cursor()
        cur.execute('LISTEN dbevent;')

        tbl = db_pg.table('invc.invoice_row')
        self._set_notify(tbl, 'invoice_id,product_id')
        try:
            record = {'id': 'row_upd_1', 'invoice_id': 'inv_002', 'product_id': 'prod_42'}
            old_record = {'id': 'row_upd_1', 'invoice_id': 'inv_001', 'product_id': 'prod_42'}
            db_pg._dbNotify(tbl, 'U', record, old_record=old_record)
            db_pg.commit()

            ready = select.select([listener], [], [], 5)
            assert ready[0], 'No notification received'
            listener.poll()
            notifications = list(listener.notifies)
            payload = json.loads(notifications[-1].payload)
            assert payload['event'] == 'U'
            assert 'invoice_id' in payload['fields']
            assert payload['fields']['invoice_id']['old'] == 'inv_001'
            assert payload['fields']['invoice_id']['new'] == 'inv_002'
            assert 'product_id' not in payload['fields']
        finally:
            self._clear_notify(tbl)
            listener.close()

    def test_notify_fields_update_no_change(self, db_pg):
        """notify='invoice_id' on update with no fkey change sends no fields."""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        dsn = db_pg.adapter.dbroot.connection.dsn
        listener = psycopg2.connect(dsn)
        listener.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = listener.cursor()
        cur.execute('LISTEN dbevent;')

        tbl = db_pg.table('invc.invoice_row')
        self._set_notify(tbl, 'invoice_id')
        try:
            record = {'id': 'row_upd_2', 'invoice_id': 'inv_001', 'quantity': 10}
            old_record = {'id': 'row_upd_2', 'invoice_id': 'inv_001', 'quantity': 5}
            db_pg._dbNotify(tbl, 'U', record, old_record=old_record)
            db_pg.commit()

            ready = select.select([listener], [], [], 5)
            assert ready[0], 'No notification received'
            listener.poll()
            notifications = list(listener.notifies)
            payload = json.loads(notifications[-1].payload)
            assert payload['event'] == 'U'
            assert 'fields' not in payload
        finally:
            self._clear_notify(tbl)
            listener.close()
