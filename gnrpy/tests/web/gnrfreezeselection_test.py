"""
Test suite for freezed selection mechanism.

Tests the full freeze/unfreeze cycle at web page level using
GnrWsgiSite('test_invoice_pg') + site.dummyPage.

Entry point is page.app.getSelection() which internally:
- executes the query
- calls selection.setKey('rowidx')
- calls page.freezeSelection(selection, name, freezePkeys=True)

The freeze/unfreeze lifecycle is managed exclusively by the
GnrFreezedSelections proxy.  Two backends are tested: pickle and sqlite.
"""
import os
import shutil

import pytest

COLUMNS = '$id,$inv_number,$date,$total,$gross_total,$customer_id'
TABLE = 'invc.invoice'
SEL_NAME = 'test_sel'
SEL_LIMIT = 20


@pytest.fixture(params=[False, True], ids=['pickle', 'sqlite'])
def page(site, request):
    p = site.dummyPage
    p.page_id = 'test_page'
    p._connection_id = 'test_conn'
    p.sourcepage_id = None
    p.use_freeze_sqlite = request.param
    if hasattr(p, '_gnrfreezedselections'):
        del p._gnrfreezedselections
    yield p
    conn_folder = os.path.join(site.allConnectionsFolder, 'test_conn')
    if os.path.exists(conn_folder):
        shutil.rmtree(conn_folder)


@pytest.fixture
def frozen_page(page):
    """Page with a frozen selection created via getSelection (the real entry point)."""
    page.app.getSelection(
        table=TABLE,
        columns=COLUMNS,
        selectionName=SEL_NAME,
        limit=SEL_LIMIT
    )
    return page


class TestFreezeUnfreezeBase:

    def test_freeze_creates_folder(self, frozen_page):
        folder = frozen_page.pageLocalDocument(SEL_NAME)
        assert os.path.isdir(folder)

    def test_freeze_creates_files_pickle(self, frozen_page):
        if frozen_page.use_freeze_sqlite:
            pytest.skip('pickle-only test')
        folder = frozen_page.pageLocalDocument(SEL_NAME)
        assert os.path.exists(os.path.join(folder, 'selection.pik'))
        assert os.path.exists(os.path.join(folder, 'selection_data.pik'))

    def test_freeze_creates_files_sqlite(self, frozen_page):
        if not frozen_page.use_freeze_sqlite:
            pytest.skip('sqlite-only test')
        folder = frozen_page.pageLocalDocument(SEL_NAME)
        assert os.path.exists(os.path.join(folder, 'selection_meta.json'))
        assert os.path.exists(os.path.join(folder, 'selection.sqlite'))

    def test_freeze_creates_pkeys_file(self, frozen_page):
        if frozen_page.use_freeze_sqlite:
            pytest.skip('pkeys file is pickle-only')
        folder = frozen_page.pageLocalDocument(SEL_NAME)
        assert os.path.exists(os.path.join(folder, 'selection_pkeys.pik'))

    def test_unfreeze_returns_selection(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        assert sel is not None

    def test_freeze_unfreeze_data_integrity(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        assert len(sel.data) == SEL_LIMIT

    def test_freeze_unfreeze_columns(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        for col in ('id', 'inv_number', 'date', 'total', 'gross_total', 'customer_id'):
            assert col in sel.allColumns

    def test_freeze_unfreeze_has_rowidx(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        assert 'rowidx' in sel.allColumns

    def test_freeze_unfreeze_colattrs(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        assert 'total' in sel.colAttrs
        assert 'dataType' in sel.colAttrs['total']

    def test_unfreeze_returns_fully_loaded(self, frozen_page):
        """The selection returned by unfreezeSelection must be immediately usable."""
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        assert sel._frz_data is not None
        assert sel._frz_data != 'frozen'
        assert isinstance(sel._frz_data, list)
        assert len(sel._frz_data) == SEL_LIMIT


class TestGetUserSelection:

    def test_getUserSelection_basic(self, frozen_page):
        result = frozen_page.getUserSelection(selectionName=SEL_NAME, table=TABLE)
        assert result is not None
        assert len(result) == SEL_LIMIT

    def test_getUserSelection_with_columns(self, frozen_page):
        result = frozen_page.getUserSelection(
            selectionName=SEL_NAME,
            table=TABLE,
            columns='$inv_number,$total'
        )
        assert result is not None
        assert len(result) == SEL_LIMIT
        assert 'inv_number' in result.allColumns
        assert 'total' in result.allColumns

    def test_getUserSelection_with_pkey_columns(self, frozen_page):
        pkeys = frozen_page.getUserSelection(
            selectionName=SEL_NAME,
            table=TABLE,
            columns='pkey'
        )
        assert isinstance(pkeys, list)
        assert len(pkeys) == SEL_LIMIT

    def test_getUserSelection_with_selectedRowidx(self, frozen_page):
        result = frozen_page.getUserSelection(
            selectionName=SEL_NAME,
            table=TABLE,
            selectedRowidx={0, 2, 4}
        )
        assert result is not None
        assert len(result) == 3

    def test_getUserSelection_with_sortBy(self, frozen_page):
        result = frozen_page.getUserSelection(
            selectionName=SEL_NAME,
            table=TABLE,
            sortBy='total'
        )
        assert result is not None
        totals = [r['total'] for r in result]
        assert totals == sorted(totals)


class TestFreezeUpdate:

    def test_freezeUpdate_after_change(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        sel.filter(lambda r: r['total'] is not None and r['total'] > 0)
        sel.isChangedData = True
        sel.isChangedFiltered = True
        sel.isChangedSelection = True
        frozen_page.freezeSelectionUpdate(sel)
        sel2 = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        assert sel2._filtered_data is not None or len(sel2.data) <= SEL_LIMIT

    def test_freezeUpdate_selective_pickle(self, frozen_page):
        """Pickle backend only rewrites files whose content changed."""
        if frozen_page.use_freeze_sqlite:
            pytest.skip('selective update is pickle-only')
        folder = frozen_page.pageLocalDocument(SEL_NAME)
        pik_path = os.path.join(folder, 'selection.pik')
        data_path = os.path.join(folder, 'selection_data.pik')
        pik_mtime = os.path.getmtime(pik_path)
        data_mtime = os.path.getmtime(data_path)
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        sel.isChangedData = False
        sel.isChangedFiltered = False
        sel.isChangedSelection = True
        frozen_page.freezeSelectionUpdate(sel)
        assert os.path.getmtime(pik_path) >= pik_mtime
        assert os.path.getmtime(data_path) == data_mtime


class TestFullyLoaded:
    """Verify that unfrozen selections are fully loaded (no lazy loading)."""

    def test_data_fully_loaded(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        assert sel._frz_data is not None
        assert sel._frz_data != 'frozen'
        assert len(sel.data) == SEL_LIMIT

    def test_filtered_fully_loaded(self, frozen_page):
        if frozen_page.use_freeze_sqlite:
            pytest.skip('sqlite backend does not preserve filtered data separately')
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        sel.filter(lambda r: r['total'] is not None and r['total'] > 0)
        frozen_page.freezeSelection(sel, 'test_sel_filtered')
        sel2 = frozen_page.unfreezeSelection(
            dbtable=TABLE, name='test_sel_filtered')
        assert sel2._frz_filtered_data is not None
        assert sel2._frz_filtered_data != 'frozen'


class TestFilterAndFreeze:

    def test_freeze_with_filter(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        original_len = len(sel.data)
        sel.filter(lambda r: r['total'] is not None and r['total'] > 100)
        filtered_len = len(sel.data)
        frozen_page.freezeSelection(sel, 'test_sel_filtered')
        sel2 = frozen_page.unfreezeSelection(dbtable=TABLE, name='test_sel_filtered')
        assert len(sel2.data) == filtered_len
        assert filtered_len <= original_len

    def test_freeze_filter_then_clear(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        original_len = len(sel.data)
        sel.filter(lambda r: r['total'] is not None and r['total'] > 100)
        frozen_page.freezeSelection(sel, 'test_sel_filtered')
        sel2 = frozen_page.unfreezeSelection(dbtable=TABLE, name='test_sel_filtered')
        sel2.filter()
        assert len(sel2._data) == original_len


class TestFreezedPkeys:

    def test_freezedPkeys(self, frozen_page):
        pkeys = frozen_page.freezedPkeys(dbtable=TABLE, name=SEL_NAME)
        assert isinstance(pkeys, list)
        assert len(pkeys) == SEL_LIMIT

    def test_freezedPkeys_match_selection(self, frozen_page):
        pkeys = frozen_page.freezedPkeys(dbtable=TABLE, name=SEL_NAME)
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        expected = sel.output('pkeylist')
        assert pkeys == expected


class TestAppHandlerMethods:

    def test_freezedSelectionPkeys(self, frozen_page):
        pkeys = frozen_page.app.freezedSelectionPkeys(
            table=TABLE,
            selectionName=SEL_NAME
        )
        assert isinstance(pkeys, list)
        assert len(pkeys) == SEL_LIMIT

    def test_sumOnFreezedSelection(self, frozen_page):
        result = frozen_page.app.sumOnFreezedSelection(
            selectionName=SEL_NAME,
            table=TABLE,
            sum_column='total'
        )
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        expected = sel.sum('total')
        assert result == expected

    def test_checkFreezedSelection_no_change(self, frozen_page):
        result = frozen_page.app.checkFreezedSelection(
            changelist=[],
            selectionName=SEL_NAME,
            table=TABLE
        )
        assert result is False

    def test_checkFreezedSelection_with_delete(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        pkey = sel.output('pkeylist')[0]
        result = frozen_page.app.checkFreezedSelection(
            changelist=[{'dbevent': 'D', 'pkey': pkey}],
            selectionName=SEL_NAME,
            table=TABLE
        )
        assert result is True

    def test_checkFreezedSelection_with_insert(self, frozen_page):
        result = frozen_page.app.checkFreezedSelection(
            changelist=[{'dbevent': 'I', 'pkey': 'nonexistent_pkey_12345'}],
            selectionName=SEL_NAME,
            table=TABLE
        )
        assert result is False
