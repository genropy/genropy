"""cachedKey keys store-local tables on the current dbstore (issue #1794).

Only tables that live in the root store (``multidb='*'`` or
``use_dbstores()`` returning ``False``) share the rootstore key; every
other table must be keyed on ``db.currentStorename``, or a second dbstore
reuses the cached data of the first one.
"""

import pytest

from gnr.sql.gnrsql import GnrSqlDb


class RootOnlyTable(object):
    def use_dbstores(self, **kwargs):
        return False


@pytest.fixture(scope='module')
def db(tmp_path_factory):
    dbname = str(tmp_path_factory.mktemp('cachedkey') / 'cachedkey.sqlite')
    db = GnrSqlDb(implementation='sqlite', dbname=dbname)
    pkg = db.packageSrc('cachekey')
    for tblname, attrs in (('local', {}), ('shared', {'multidb': '*'}), ('rootonly', {})):
        tbl = pkg.table(tblname, pkey='id', **attrs)
        tbl.column('id', size='22')
    db.tableMixin('cachekey.rootonly', RootOnlyTable)
    db.startup()
    yield db
    db.closeConnection()


def test_store_local_table_keyed_on_current_store(db):
    tbl = db.table('cachekey.local')
    assert tbl.use_dbstores() is None
    with db.tempEnv(storename='store_b'):
        assert tbl.cachedKey('sysRecord') == 'store_b.sysRecord.cachekey.local'


def test_multidb_star_table_keyed_on_rootstore(db):
    with db.tempEnv(storename='store_b'):
        key = db.table('cachekey.shared').cachedKey('sysRecord')
    assert key == '%s.sysRecord.cachekey.shared' % db.rootstore


def test_root_only_table_keyed_on_rootstore(db):
    tbl = db.table('cachekey.rootonly')
    assert tbl.use_dbstores() is False
    with db.tempEnv(storename='store_b'):
        assert tbl.cachedKey('sysRecord') == '%s.sysRecord.cachekey.rootonly' % db.rootstore
