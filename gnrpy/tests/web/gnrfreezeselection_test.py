"""
Test suite for freezed selection mechanism.

Tests the full freeze/unfreeze cycle at web page level using
GnrWsgiSite('test_invoice_pg') + site.dummyPage.

Entry point is page.app.getSelection() which internally:
- executes the query
- calls selection.setKey('rowidx')
- calls page.freezeSelection(selection, name, freezePkeys=True)

This provides baseline coverage before refactoring freeze/unfreeze
into a dedicated proxy and introducing SQLite backend.
"""
import os
import shutil
import pytest

from gnr.web.gnrwsgisite import GnrWsgiSite

COLUMNS = '$id,$inv_number,$date,$total,$gross_total,$customer_id'
TABLE = 'invc.invoice'
SEL_NAME = 'test_sel'
SEL_LIMIT = 20


@pytest.fixture(scope='module')
def site():
    return GnrWsgiSite('test_invoice_pg')


@pytest.fixture
def page(site):
    p = site.dummyPage
    p.page_id = 'test_page'
    p._connection_id = 'test_conn'
    p.sourcepage_id = None
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

    def test_freeze_creates_files(self, frozen_page):
        path = frozen_page.pageLocalDocument(SEL_NAME)
        assert os.path.exists(path + '.pik')
        assert os.path.exists(path + '_data.pik')

    def test_freeze_creates_pkeys_file(self, frozen_page):
        path = frozen_page.pageLocalDocument(SEL_NAME)
        assert os.path.exists(path + '_pkeys.pik')

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

    def test_freezeUpdate_selective(self, frozen_page):
        path = frozen_page.pageLocalDocument(SEL_NAME)
        pik_mtime = os.path.getmtime(path + '.pik')
        data_mtime = os.path.getmtime(path + '_data.pik')
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        sel.isChangedData = False
        sel.isChangedFiltered = False
        sel.isChangedSelection = True
        frozen_page.freezeSelectionUpdate(sel)
        assert os.path.getmtime(path + '.pik') >= pik_mtime
        assert os.path.getmtime(path + '_data.pik') == data_mtime


class TestLazyLoading:

    def test_lazy_loading_data(self, frozen_page):
        sel = frozen_page.db.unfreezeSelection(
            frozen_page.pageLocalDocument(SEL_NAME)
        )
        assert sel._frz_data == 'frozen'
        _ = sel.data
        assert sel._frz_data != 'frozen'

    def test_lazy_loading_filtered(self, frozen_page):
        sel = frozen_page.unfreezeSelection(dbtable=TABLE, name=SEL_NAME)
        sel.filter(lambda r: r['total'] is not None and r['total'] > 0)
        frozen_page.freezeSelection(sel, 'test_sel_filtered')
        sel2 = frozen_page.db.unfreezeSelection(
            frozen_page.pageLocalDocument('test_sel_filtered')
        )
        assert sel2._frz_filtered_data == 'frozen'
        _ = sel2._filtered_data
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
