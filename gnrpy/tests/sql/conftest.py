"""Shared fixtures for sql tests that need a populated test_invoice database.

Creates SQLite and PostgreSQL databases on the fly using db_attrs,
then imports CSV data from projects/test_invoice/data/export/.
"""

import csv
import os
import sys
import subprocess
import tempfile

import pytest

from gnr.app.gnrapp import GnrApp
from core.common import BaseGnrTest

_base_gnr_test_ready = False


def _ensure_base_gnr_test():
    global _base_gnr_test_ready
    if not _base_gnr_test_ready:
        BaseGnrTest.setup_class()
        _base_gnr_test_ready = True


def _csv_dir():
    """Return the path to the CSV export directory."""
    return os.path.join(
        os.path.dirname(__file__), '..', '..', '..',
        'projects', 'test_invoice', 'data', 'export'
    )


# Tables in FK-safe import order.
# 'user' belongs to the 'adm' package (schema adm on PG, prefix adm_ on SQLite).
IMPORT_TABLES = [
    ('invc', 'region'),
    ('invc', 'state'),
    ('invc', 'customer_type'),
    ('invc', 'vat_type'),
    ('invc', 'payment_type'),
    ('invc', 'postcode'),
    ('invc', 'product_type'),
    ('invc', 'product'),
    ('invc', 'customer'),
    ('invc', 'staff_role'),
    ('adm', 'user'),
    ('invc', 'staff'),
    ('invc', 'discount_tier'),
    ('invc', 'price_year'),
    ('invc', 'price_year_note'),
    ('invc', 'invoice'),
    ('invc', 'invoice_row'),
    ('invc', 'invoice_note'),
]

SKIP_COLUMNS = {'pkey'}


def _import_csv_data(db):
    """Import all CSV files into the database using raw SQL."""
    csv_path = _csv_dir()
    impl = db.implementation
    conn = db.adapter.connection()
    cur = conn.cursor()

    for pkg, table in IMPORT_TABLES:
        fpath = os.path.join(csv_path, '%s.csv' % table)
        if not os.path.isfile(fpath):
            continue

        if impl == 'sqlite':
            tname = '%s_%s' % (pkg, table)
        else:
            tname = '%s.%s_%s' % (pkg, pkg, table)

        with open(fpath, 'r', newline='') as f:
            reader = csv.DictReader(f)
            columns = [c for c in reader.fieldnames if c not in SKIP_COLUMNS]
            cols_str = ','.join(columns)

            if impl == 'sqlite':
                placeholders = ','.join([':%s' % c for c in columns])
            else:
                placeholders = ','.join(['%%(%s)s' % c for c in columns])

            sql = 'INSERT INTO %s (%s) VALUES (%s)' % (tname, cols_str, placeholders)
            batch = []
            for row in reader:
                record = {c: (None if row[c] == '' else row[c]) for c in columns}
                batch.append(record)
                if len(batch) >= 1000:
                    cur.executemany(sql, batch)
                    batch = []
            if batch:
                cur.executemany(sql, batch)

    conn.commit()
    cur.close()


@pytest.fixture(scope='module')
def db_sqlite():
    _ensure_base_gnr_test()
    tempdir = tempfile.mkdtemp()
    app = GnrApp('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(tempdir, 'testing'),
    ))
    app.db.model.check(applyChanges=True)
    _import_csv_data(app.db)
    return app.db


@pytest.fixture(scope='module')
def db_pg():
    _ensure_base_gnr_test()
    if sys.platform == 'win32':
        pytest.skip('testing.postgresql not available on Windows')
    pg_instance = None
    if 'GITHUB_WORKFLOW' in os.environ:
        pg_conf = dict(host='127.0.0.1', port='5432',
                       user='postgres', password='postgres')
    elif 'GNR_TEST_PG_PASSWORD' in os.environ:
        pg_conf = dict(
            host=os.environ.get('GNR_TEST_PG_HOST', '127.0.0.1'),
            port=os.environ.get('GNR_TEST_PG_PORT', '5432'),
            user=os.environ.get('GNR_TEST_PG_USER', 'postgres'),
            password=os.environ.get('GNR_TEST_PG_PASSWORD'),
        )
    else:
        try:
            from testing.postgresql import Postgresql
        except ImportError:
            pytest.skip('testing.postgresql not installed')
        subprocess.run(['pkill', '-f', 'postgres.*tmp'], capture_output=True)
        pg_instance = Postgresql()
        dsn = pg_instance.dsn()
        pg_conf = dict(host=dsn['host'], port=dsn['port'], user=dsn['user'])
    dbname = pg_conf.pop('database', 'test_compiler')
    try:
        app = GnrApp('test_invoice', db_attrs=dict(
            implementation='postgres',
            dbname=dbname,
            **pg_conf,
        ))
        app.db.model.check(applyChanges=True)
        _import_csv_data(app.db)
        yield app.db
    except Exception:
        pytest.skip('PostgreSQL not available')
    finally:
        if pg_instance:
            pg_instance.stop()
