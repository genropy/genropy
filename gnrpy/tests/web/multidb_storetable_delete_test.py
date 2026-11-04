"""Deleting a workspace stops its site register in gnrdaemon (#1567).

``StoreTable.trigger_onDeleted_multidb`` runs unbound against a minimal
fake table: a multidomain site needs a running instance and a daemon. The
site keeps the real ``GnrWsgiSite.get_domainIdentifier`` and a real
``GnrDomainHandler``; only the daemon proxy is replaced, by a recorder.
"""

import importlib.util
import logging
import os
import types

import pytest

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


def _fake_table(site):
    db = types.SimpleNamespace(
        stores_handler=types.SimpleNamespace(refresh_dbstores=lambda: None),
        application=types.SimpleNamespace(site=site),
    )
    return types.SimpleNamespace(db=db)


@pytest.fixture(scope='module')
def storetable():
    return load_storetable().StoreTable


def test_workspace_delete_stops_its_register(storetable):
    site = _FakeSite()

    storetable.trigger_onDeleted_multidb(_fake_table(site), {'dbstore': 'ws1'})

    assert 'ws1' not in site.domains.domains
    assert site.register.gnrdaemon_proxy.stopped == ['teamset|ws1']


def test_register_stop_failure_is_logged_not_raised(storetable, caplog):
    site = _FakeSite(failing=True)

    with caplog.at_level(logging.ERROR):
        storetable.trigger_onDeleted_multidb(_fake_table(site), {'dbstore': 'ws1'})

    assert 'ws1' not in site.domains.domains
    assert any('teamset|ws1' in r.getMessage() for r in caplog.records)


def test_store_delete_without_multidomain_leaves_the_site_register(storetable):
    """Without multidomain the identifier of any store is the site itself."""
    site = _FakeSite(multidomain=False)

    storetable.trigger_onDeleted_multidb(_fake_table(site), {'dbstore': 'ws1'})

    assert site.register.gnrdaemon_proxy.stopped == []
