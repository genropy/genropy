"""Conftest for web tests.

Provides a shared GnrWsgiSite session fixture using test_invoice_pg (PostgreSQL).
Loads 50 invoices + rows from test_invoice_fixture.json before the test session
and removes them after.
"""
import json
import os

import pytest

from gnr.web.gnrwsgisite import GnrWsgiSite

FIXTURE_JSON = os.path.join(
    os.path.dirname(__file__), '..', '..', '..',
    'projects', 'test_invoice', 'data', 'test_invoice_fixture.json'
)


def _cleanup_fixture_data(db, data):
    """Delete all fixture invoices (cascade removes rows)."""
    inv_tbl = db.table('invc.invoice')
    for inv in data['invoice']:
        try:
            inv_tbl.delete({'id': inv['id']})
        except Exception:
            pass
    db.commit()


@pytest.fixture(scope='session')
def site():
    s = GnrWsgiSite('test_invoice_pg')
    with open(FIXTURE_JSON) as f:
        data = json.load(f)
    db = s.db
    _cleanup_fixture_data(db, data)
    inv_tbl = db.table('invc.invoice')
    row_tbl = db.table('invc.invoice_row')
    for inv in data['invoice']:
        inv_tbl.insert(inv)
    for row in data['invoice_row']:
        row_tbl.insert(row)
    db.commit()
    yield s
    _cleanup_fixture_data(db, data)
