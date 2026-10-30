"""A grouped view keeps its selection on the server (#1773).

The export of a grouped view used to upload every grouped row from the
browser, ``_pkeylist`` included, until the request outgrew the proxy limit.
The grouped store now freezes its selection under a name, as the virtual
views do, and the export reads it back by rowidx. A GROUP BY selection has no
pkey column: getSelection must freeze it all the same, and must not offer it
as the table's last selection, whose readers need its pkeylist.

The database is real (``test_invoice`` on sqlite, with its CSV data) and so is
the grouped view's select method, loaded from ``resources/common/th``; only
the HTTP page context is a stand-in.
"""

import importlib.util
import os
import pathlib

import pytest

from core.common import BaseGnrTest
from sql.conftest import db_sqlite, sqlite_temp_dir        # noqa: F401  (fixtures)

from apphandler_legacy_common import _StandInPage

from gnr.core.gnrbag import Bag
from gnr.web._gnrbasewebpage import GnrBaseWebPage
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler

TH_GROUPTH = (pathlib.Path(__file__).parents[3] / 'resources' / 'common'
              / 'th' / 'th_groupth.py')

LAST_SELECTION = 'current.table.invc_invoice.last_selection_path'


def _load_th_groupth():
    spec = importlib.util.spec_from_file_location('th_groupth', TH_GROUPTH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


th_groupth = _load_th_groupth()


def setup_module(module):
    if not os.environ.get('GENRO_GNRFOLDER'):
        BaseGnrTest.setup_class()
        module._owns_config = True


def teardown_module(module):
    if getattr(module, '_owns_config', False):
        BaseGnrTest.teardown_class()


class _GroupedViewPage(_StandInPage):
    """The stand-in page with the grouped view's select method mixed in."""

    sourcepage_id = None
    _thg_selectgroupby = th_groupth.TableHandlerGroupBy._thg_selectgroupby
    getUserSelection = GnrBaseWebPage.getUserSelection


@pytest.fixture
def page(db_sqlite, tmp_path):                              # noqa: F811
    page = _GroupedViewPage(db_sqlite, str(tmp_path))
    page.app = GnrWebAppHandler(page)
    return page


def _grouped_struct():
    struct = Bag()
    struct.setItem('view_0.rows_0.cell_0', None, field='@customer_id.state', name='State', dtype='A')
    struct.setItem('view_0.rows_0.cell_1', None, field='total', name='Total', dtype='N', group_aggr='sum')
    struct.setItem('view_0.rows_0.cell_2', None, field='_grp_count', name='Count', dtype='L', group_aggr='sum')
    return struct


def _load_grouped_view(page):
    """What the grouped store asks the server, selectionName included."""
    return page.app.getSelection(table='invc.invoice', selectmethod=page._thg_selectgroupby,
                                 struct=_grouped_struct(), selectionName='*grouped')


def test_a_grouped_selection_is_frozen_under_its_name(page):
    rows, attrs = _load_grouped_view(page)
    assert attrs['selectionName'] == 'grouped'
    frozen = page.unfreezeSelection(page.db.table('invc.invoice'), 'grouped')
    assert len(frozen) == attrs['totalrows'] == len(rows) > 2
    assert [r.attr['rowidx'] for r in rows] == list(range(len(rows)))
    assert {'_customer_id_state', 'total_sum', '_grp_count_sum', '_pkeylist'} <= set(frozen.allColumns)
    assert 'pkey' not in frozen.allColumns
    assert page.freezedPkeys(page.db.table('invc.invoice'), 'grouped') == []


def test_a_grouped_selection_is_not_the_tables_last_selection(page):
    page.app.getSelection(table='invc.invoice', columns='$inv_number', selectionName='*plain')
    plain_path = page.userStore().getItem(LAST_SELECTION)
    assert plain_path
    _load_grouped_view(page)
    assert page.userStore().getItem(LAST_SELECTION) == plain_path


def test_the_export_reads_the_grouped_rows_back_by_rowidx(page):
    rows, _ = _load_grouped_view(page)
    loaded = {r.attr['rowidx']: r.attr for r in rows}
    picked = [0, 2]
    expected = sorted((loaded[i] for i in picked), key=lambda r: r['total_sum'], reverse=True)
    selection = page.getUserSelection(selectionName='grouped', selectedRowidx=picked,
                                      sortBy='total_sum:d')
    assert [(r['_customer_id_state'], r['total_sum'], r['_grp_count_sum'])
            for r in selection.output('dictlist')] == \
           [(r['_customer_id_state'], r['total_sum'], r['_grp_count_sum']) for r in expected]
