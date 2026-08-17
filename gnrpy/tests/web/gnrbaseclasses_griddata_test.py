"""Regression test for issue #980: TableScriptToHtml.gridData() must not
crash when the selection-order sort is applied to a query that was not
actually built from the current selection.

``gridData()`` (gnr/web/gnrbaseclasses.py) only rewrites the query to
``$pkey IN :selectionPkeys`` when ``use_current_selection`` is set (or the
resource defines no ``gridQueryParameters()`` at all). Before the fix, the
trailing sort-by-selection-order step only checked ``selectionPkeys`` and
``order_by``, ignoring whether the query had actually been restricted to
the selection. When a resource has its own ``gridQueryParameters()`` and no
``order_by``, and the caller's selection is a strict subset of what that
query returns, ``selectionPkeys.index(r['pkey'])`` raised ``ValueError`` for
every row outside the selection.
"""

import os
import shutil
import tempfile

import pytest

from gnr.app.gnrapp import GnrApp
from core.common import BaseGnrTest
from gnr.core.gnrbag import Bag
from gnr.web.gnrbaseclasses import TableScriptToHtml


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


PAYMENT_TYPES = [
    ('C1', 'Cash'),
    ('C2', 'Bank transfer'),
    ('C3', 'Credit card'),
    ('C4', 'Check'),
]


@pytest.fixture(scope='module')
def sqlite_temp_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope='module')
def sqlite_db(sqlite_temp_dir):
    app = GnrApp('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(sqlite_temp_dir, 'testing'),
    ))
    app.db.model.check(applyChanges=True)
    tbl = app.db.table('invc.payment_type')
    for code, description in PAYMENT_TYPES:
        tbl.insert(dict(code=code, description=description))
    app.db.commit()
    return app.db


class _FakeExportParent:
    """Minimal stand-in for the batch/export caller: gridData() only reads
    .export_mode on it to decide between the grid-Bag and dictlist output.
    """
    export_mode = True


class _GridDataResource(TableScriptToHtml):
    """Narrowest real stand-in for a print/export resource with its own
    gridQueryParameters(). Bypasses TableScriptToHtml.__init__() (which
    needs a full webpage with .btc.thermo_wrapper), and exercises the
    genuine gridData() against a real sqlite table.
    """
    grid_sqlcolumns = 'code,description'
    grid_subtotal_order_by = None

    def gridQueryParameters(self):
        return dict(table='invc.payment_type')


def _make_resource(db, selection_pkeys, use_current_selection=False):
    obj = _GridDataResource.__new__(_GridDataResource)
    obj.db = db
    # Real resources set row_table themselves (class attribute or
    # onRecordLoaded()) before gridData() runs; currentSelectionQueryParameters()
    # relies on it already being set.
    obj.row_table = 'invc.payment_type'
    obj.parent = _FakeExportParent()
    obj._parameters = Bag()
    if use_current_selection:
        obj._parameters['use_current_selection'] = True
    obj.record = Bag(dict(selectionPkeys=selection_pkeys))
    return obj


def test_griddata_partial_selection_without_use_current_selection(sqlite_db):
    """Resource-driven query (no use_current_selection, no order_by) with a
    selection that is a strict subset of the query's rows: the query must
    NOT be treated as selection-driven, so the crashing sort must not run
    and every row must come back untouched, in natural query order."""
    resource = _make_resource(sqlite_db, selection_pkeys=['C1', 'C3'])
    data = resource.gridData()
    assert [row['code'] for row in data] == ['C1', 'C2', 'C3', 'C4']


def test_griddata_use_current_selection_still_sorts_by_selection_order(sqlite_db):
    """Regression guard for the ca68b0d01 feature: when
    use_current_selection is set, the query IS selection-driven and rows
    must come back sorted in selectionPkeys order."""
    resource = _make_resource(sqlite_db, selection_pkeys=['C3', 'C1'],
                               use_current_selection=True)
    data = resource.gridData()
    assert [row['code'] for row in data] == ['C3', 'C1']
