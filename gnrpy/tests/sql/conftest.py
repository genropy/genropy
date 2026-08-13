"""Shared fixtures for sql tests that need a populated test_invoice database.

Creates SQLite and PostgreSQL databases on the fly using db_attrs,
then imports CSV data from projects/test_invoice/data/export/.
"""

import csv
import os
import tempfile
import shutil

import pytest

from gnr.app.gnrapp import GnrApp
from core.common import BaseGnrTest
from .common import get_pg_config



@pytest.fixture(scope="module", autouse=True)
def sqlite_temp_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def setup_module(module):
    BaseGnrTest.setup_class()
def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope='module', autouse=True)
def gnr_test_config():
    """Make sure every module in this package runs with a genro configuration.

    The setup_module/teardown_module above are never called: pytest honours
    xunit module hooks on test modules, not on a conftest.  Every module that
    needs a configuration therefore repeats the call itself -- and
    test_db_notify and test_gnrlistener do not, so on a machine without a
    ~/.gnr of its own, CI included, their fixtures died with
    'Missing genro configuration'.  Modules that already set one up keep it.
    """
    if os.environ.get('GENRO_GNRFOLDER'):
        yield
        return
    BaseGnrTest.setup_class()
    try:
        yield
    finally:
        BaseGnrTest.teardown_class()

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
def db_sqlite(sqlite_temp_dir):
    app = GnrApp('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(sqlite_temp_dir, 'testing'),
    ))
    app.db.model.check(applyChanges=True)
    _import_csv_data(app.db)
    return app.db


def _pg_dbname(request, implementation):
    """Database name unique to the requesting module and implementation.

    get_pg_config() returns an already running server whenever the tests run
    against a shared postgres (CI, or GNR_TEST_PG_*).  There every one of
    these module-scoped fixtures would land on the same database and import
    the CSV data on top of the previous module's rows, so the second module
    onwards died on a duplicate key.
    """
    module = request.module.__name__.rsplit('.', 1)[-1]
    return '%s_%s' % (module, implementation)


@pytest.fixture(scope='module')
def db_pg(request):
    # no skip on failure: postgres is a required part of this suite, and a
    # run that cannot reach it has to fail loudly instead of reporting green.
    pg_conf, pg_instance = get_pg_config()
    pg_conf.pop('database', None)
    dbname = _pg_dbname(request, 'postgres')
    try:
        app = GnrApp('test_invoice', db_attrs=dict(
            implementation='postgres',
            dbname=dbname,
            **pg_conf,
        ))
        app.db.model.check(applyChanges=True)
        _import_csv_data(app.db)
        yield app.db
    finally:
        if pg_instance is not None:
            pg_instance.stop()


@pytest.fixture(scope='module')
def db_pg3(request):
    # no skip on failure: postgres is a required part of this suite, and a
    # run that cannot reach it has to fail loudly instead of reporting green.
    pg_conf, pg_instance = get_pg_config()
    pg_conf.pop('database', None)
    dbname = _pg_dbname(request, 'postgres3')
    try:
        app = GnrApp('test_invoice', db_attrs=dict(
            implementation='postgres3',
            dbname=dbname,
            **pg_conf,
        ))
        app.db.model.check(applyChanges=True)
        _import_csv_data(app.db)
        yield app.db
    finally:
        if pg_instance is not None:
            pg_instance.stop()
