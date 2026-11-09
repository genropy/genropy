# encoding: utf-8
"""A multidomain store without its _mainpref_ row reads as empty preferences.

A workspace that never saved its preferences has no _mainpref_ row in its own
database. Reading the preferences there must not raise: upgrade scripts call
getPreference on every store during `gnr db migrate '<instance>.*' -u`.
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import instanceMixin
from gnr.sql.gnrsql_exceptions import RecordNotExistingError

MODEL_PY = Path(__file__).resolve().parents[1] / 'model' / 'preference.py'
_spec = importlib.util.spec_from_file_location('adm_preference_under_test', MODEL_PY)
preference_model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preference_model)


class MissingRecord(object):
    def output(self, mode):
        return Bag()


class FakeTable(object):
    def __init__(self):
        self.db = MagicMock()
        self.db.multidomain = True
        self.db.usingMultiStore.return_value = False
        self.db.usingRootstore.return_value = False
        self.db.currentEnv = {'storename': 'newstore'}
        self.db.application.cache.expiredItem.return_value = True
        pkgobj = MagicMock()
        pkgobj.attributes = {}
        self.db.application.packages = {'adm': pkgobj}
        multidb = self.db.package.return_value
        multidb.getHostingPreference.return_value = Bag(dict(adm=Bag(dict(hosted='h'))))

    def record(self, pkey=None, ignoreMissing=False, **kwargs):
        if not ignoreMissing:
            raise RecordNotExistingError('No record found for %s' % pkey)
        return MissingRecord()


@pytest.fixture
def tbl():
    table = FakeTable()
    instanceMixin(table, preference_model.Table)
    table.getMainStorePreference = Bag
    return table


def test_store_preferences_without_mainpref_row(tbl):
    preference = tbl.getStorePreferences()
    assert preference['adm.hosted'] == 'h'


def test_restore_tenant_preferences_without_mainpref_row(tbl):
    data = Bag(dict(adm=Bag(dict(hosted='h'))))
    tbl.restoreTenantPreferences(data)
    assert data['adm.hosted'] is None
