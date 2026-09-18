# encoding: utf-8
"""Unit tests for MultidbTable.createSysRecords (no db required).

The multidb override must delegate to GnrDboTable.createSysRecords on the
rootstore (so do_update is honored and changes propagate to the stores through
the standard multidb sync triggers) and stay a no-op on store-side runs,
warning when do_update is requested there.
"""

import importlib.util
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gnr.core.gnrlang import instanceMixin

MAIN_PY = Path(__file__).resolve().parents[1] / 'main.py'
_spec = importlib.util.spec_from_file_location('multidb_main_under_test', MAIN_PY)
multidb_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(multidb_main)


class FakeTable(object):
    fullname = 'fake.lookup'

    def __init__(self, rootstore=True):
        self.db = MagicMock()
        self.db.usingRootstore.return_value = rootstore
        self.db.currentEnv = {'storename': None if rootstore else 'store_1'}


@pytest.fixture
def base_calls(monkeypatch):
    calls = []

    def fake_base(self, do_update=False):
        calls.append(dict(table=self, do_update=do_update))

    monkeypatch.setattr(multidb_main.GnrDboTable, 'createSysRecords', fake_base)
    return calls


def mixined_table(rootstore=True):
    tbl = FakeTable(rootstore=rootstore)
    instanceMixin(tbl, multidb_main.MultidbTable)
    return tbl


def test_rootstore_delegates_to_base(base_calls):
    tbl = mixined_table(rootstore=True)
    tbl.createSysRecords()
    assert base_calls == [dict(table=tbl, do_update=False)]


def test_rootstore_forwards_do_update(base_calls):
    tbl = mixined_table(rootstore=True)
    tbl.createSysRecords(do_update=True)
    assert base_calls == [dict(table=tbl, do_update=True)]


def test_store_side_is_noop(base_calls, caplog):
    tbl = mixined_table(rootstore=False)
    with caplog.at_level(logging.WARNING, logger='gnr.pkg'):
        tbl.createSysRecords()
    assert base_calls == []
    assert caplog.records == []


def test_store_side_do_update_warns(base_calls, caplog):
    tbl = mixined_table(rootstore=False)
    with caplog.at_level(logging.WARNING, logger='gnr.pkg'):
        tbl.createSysRecords(do_update=True)
    assert base_calls == []
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert 'fake.lookup' in message
    assert 'store_1' in message
