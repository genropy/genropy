"""Closing a connection of the session log is one transaction (issue #1977).

The end of a connection closes its pages from the update trigger: a commit
there released the row lock before the end of the connection was written,
and a logout landing in that window was overwritten by the recovery.

The lock is a row lock: PostgreSQL only, with one connection for each thread.
"""
import threading
import time
from datetime import datetime, timedelta

from core.common import BaseGnrTest

T0 = datetime(2026, 10, 3, 9, 0)
RECOVERY_TS = T0 + timedelta(hours=1)
LOGOUT_TS = T0 + timedelta(hours=2)


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def test_logout_waits_for_a_recovery_closing_the_same_connection(db_pg, monkeypatch):
    db = db_pg
    connection_tbl = db.table('adm.connection')
    page_tbl = db.table('adm.served_page')
    connection_tbl.insert(dict(id='conn_lock', start_ts=T0))
    page_tbl.insert(dict(page_id='page_lock', connection_id='conn_lock', start_ts=T0))
    db.commit()

    def logout_thread():
        try:
            connection_tbl.closeConnection('conn_lock', end_ts=LOGOUT_TS, end_reason='logout')
        finally:
            db.closeConnection()

    thread = threading.Thread(target=logout_thread)
    observer = db.adapter.connection()
    observer.autocommit = True
    held = []
    closePendingPages = page_tbl.closePendingPages

    def pages_closed_then_logout_arrives(**kwargs):
        closePendingPages(**kwargs)
        if thread.ident is not None:
            return
        thread.start()
        cursor = observer.cursor()
        deadline = time.time() + 10
        while not held and thread.is_alive() and time.time() < deadline:
            cursor.execute('SELECT count(*) FROM pg_locks WHERE NOT granted')
            if cursor.fetchone()[0]:
                held.append(True)

    monkeypatch.setattr(page_tbl, 'closePendingPages', pages_closed_then_logout_arrives)
    try:
        connection_tbl.closeConnection('conn_lock', end_ts=RECOVERY_TS, end_reason='aborted')
        thread.join(30)
    finally:
        observer.close()

    assert held, 'the logout wrote while the recovery was closing the connection'
    assert not thread.is_alive()
    connection = connection_tbl.record('conn_lock').output('dict')
    page = page_tbl.record('page_lock').output('dict')
    db.rollback()
    assert (connection['end_reason'], connection['end_ts']) == ('logout', LOGOUT_TS)
    assert (page['end_reason'], page['end_ts']) == ('logout', LOGOUT_TS)
