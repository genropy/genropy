"""Deleting a workspace stops its site register in gnrdaemon once committed (#1567, #1652).

``StoreTable.trigger_onDeleted_multidb`` runs unbound against a minimal
table: a multidomain site needs a running instance and a daemon. The table
holds a real ``GnrSqlDb`` on a throwaway SQLite, so the after-commit queue,
``commit`` and ``rollbackAll`` are the framework's own. The site keeps the
real ``GnrWsgiSite.get_domainIdentifier`` and a real ``GnrDomainHandler``;
only the daemon proxy is replaced, by a recorder.
"""

import importlib.util
import logging
import os
import types

import pytest

from gnr.sql.gnrsql import GnrSqlDb
from gnr.web.gnrwsgisite import GnrDomainHandler, GnrWsgiSite

STORETABLE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..',
                               'projects', 'gnrcore', 'packages', 'multidb',
                               'lib', 'storetable.py')


def load_storetable():
    spec = importlib.util.spec_from_file_location('multidb_storetable_under_test',
                                                  os.path.abspath(STORETABLE_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DaemonProxy:
    def __init__(self, failing=False):
        self.failing = failing
        self.stopped = []

    def siteregister_stop(self, sitename=None, **kwargs):
        self.stopped.append(sitename)
        if self.failing:
            raise ConnectionError('gnrdaemon not reachable')


class _FakeSite:
    get_domainIdentifier = GnrWsgiSite.get_domainIdentifier

    def __init__(self, multidomain=True, failing=False):
        self.site_name = 'teamset'
        self.rootDomain = '_main_'
        self.multidomain = multidomain
        self.db = types.SimpleNamespace(dbstores={'ws1': {}})
        self.domains = GnrDomainHandler(self)
        self.domains.add('ws1')
        self.register = types.SimpleNamespace(gnrdaemon_proxy=_DaemonProxy(failing=failing))


class _StoreDb(GnrSqlDb):
    stores_handler = types.SimpleNamespace(refresh_dbstores=lambda: None)


@pytest.fixture(scope='module')
def storetable():
    return load_storetable().StoreTable


@pytest.fixture
def db(tmp_path):
    db = _StoreDb(dbname=str(tmp_path / 'storetable'))
    db.startup()
    yield db
    db.closeConnection()


def _delete_workspace(storetable, db, site, dbstore='ws1'):
    db.application = types.SimpleNamespace(site=site)
    tbl = types.SimpleNamespace(db=db)
    tbl.multidb_stopDomainRegister = types.MethodType(storetable.multidb_stopDomainRegister, tbl)
    db.execute('SELECT 1')
    storetable.trigger_onDeleted_multidb(tbl, {'dbstore': dbstore})


def test_workspace_delete_stops_its_register_after_commit(storetable, db):
    site = _FakeSite()

    _delete_workspace(storetable, db, site)

    assert 'ws1' not in site.domains.domains
    assert site.register.gnrdaemon_proxy.stopped == []
    db.commit()
    assert site.register.gnrdaemon_proxy.stopped == ['teamset|ws1']


def test_rolled_back_delete_leaves_the_register(storetable, db):
    site = _FakeSite()

    _delete_workspace(storetable, db, site)
    db.rollbackAll()
    db.execute('SELECT 1')
    db.commit()

    assert site.register.gnrdaemon_proxy.stopped == []


def test_register_stop_failure_is_logged_not_raised(storetable, db, caplog):
    site = _FakeSite(failing=True)

    _delete_workspace(storetable, db, site)
    with caplog.at_level(logging.ERROR):
        db.commit()

    assert site.register.gnrdaemon_proxy.stopped == ['teamset|ws1']
    assert any('teamset|ws1' in r.getMessage() for r in caplog.records)


def test_store_delete_without_multidomain_leaves_the_site_register(storetable, db):
    """Without multidomain the identifier of any store is the site itself."""
    site = _FakeSite(multidomain=False)

    _delete_workspace(storetable, db, site)
    db.commit()

    assert site.register.gnrdaemon_proxy.stopped == []
