"""Five defects of GnrWebAppHandler that do not raise on every runtime.

Unlike the ones in ``test_apphandler_hard_errors.py`` the call returns. They
were found while building the handler copy of #1387 and are recorded there as
A9, D9, F4, DS5 and D8. Three of them give a wrong answer: A9, D9 and F4. DS5
and D8 change no result: the code was wrong and is now right, and their tests
pin what it does.

Two of them do raise, but only on part of the matrix or only on part of the
signature, which is why they were read as silent: A9 raises on Python 3.11 and
is silent from 3.12 on, and D9 raises whenever its optional parameter is used.

The database is real, and only the HTTP page context is a stand-in.
"""

import os

import pytest

from core.common import BaseGnrTest
from sql.conftest import db_sqlite, sqlite_temp_dir        # noqa: F401  (fixtures)

from apphandler_legacy_common import _StandInPage

from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler
from gnr.web.gnrwebpage_proxy.apphandler_next import GnrWebAppHandlerNext


def setup_module(module):
    if not os.environ.get('GENRO_GNRFOLDER'):
        BaseGnrTest.setup_class()
        module._owns_config = True


def teardown_module(module):
    if getattr(module, '_owns_config', False):
        BaseGnrTest.teardown_class()


@pytest.fixture
def page(db_sqlite, tmp_path):                              # noqa: F811
    return _StandInPage(db_sqlite, str(tmp_path))


@pytest.fixture
def handler(page):
    return GnrWebAppHandler(page)


@pytest.fixture(params=[GnrWebAppHandler, GnrWebAppHandlerNext],
                ids=['legacy', 'next'])
def either_handler(request, page):
    """Both handlers, where the fix has to hold in each of them."""
    return request.param(page)


# ---------------------------------------------------------------------------
#  A9 - the format_<column> keyword
# ---------------------------------------------------------------------------

def test_format_kwarg_reaches_its_column(handler):
    """A9 - ``formats[7:] = value`` wrote under a slice, not under the column.

    The intent is in the name: the key is what follows ``format_``. The slice
    belongs to ``k``, and writing it on the dict instead did two different
    wrong things depending on the runtime. Slice objects became hashable in
    3.12, so from 3.12 on the value landed under ``slice(7, None)`` and the
    format was silently dropped, while on 3.11 the same line raised
    ``TypeError: unhashable type: 'slice'`` and the call never returned.
    """
    pars = dict(table='invc.invoice', columns='$inv_number,$total',
                order_by='$inv_number', limit=1)
    plain = list(handler.getSelection(**pars)[0])[0].attr['total']
    formatted = list(handler.getSelection(format_total='#,###.00', **pars)[0])[0].attr['total']
    assert formatted != plain
    assert formatted.endswith('.00') or ',' in formatted


def test_selection_without_a_format_kwarg_is_unchanged(handler):
    """The control: no ``format_`` keyword, nothing to key."""
    rows, _ = handler.getSelection(table='invc.invoice', columns='$inv_number,$total',
                                   order_by='$inv_number', limit=1)
    assert list(rows)[0].attr['total'] is not None


# ---------------------------------------------------------------------------
#  D9 - the caption of freezedSelectionPkeys
# ---------------------------------------------------------------------------

def test_freezed_selection_pkeys_reads_the_column_caption_field_names(handler):
    """D9 - the caption was read under the literal key ``'caption_field'``.

    No row carries a column of that name, so the documented parameter raised
    ``KeyError`` every time it was used: it was unusable rather than wrong.
    """
    pars = dict(table='invc.customer', columns='$account_name',
                order_by='$account_name', selectionName='d9_selection', limit=3)
    handler.getSelection(**pars)
    captioned = handler.freezedSelectionPkeys(table='invc.customer',
                                              selectionName='d9_selection',
                                              caption_field='account_name')
    assert len(captioned) == 3
    assert all(set(entry) == {'pkey', 'caption'} for entry in captioned)
    assert all(entry['caption'] for entry in captioned)


def test_freezed_selection_pkeys_without_a_caption_returns_plain_pkeys(handler):
    """The control: with no caption_field the answer is the list of pkeys."""
    pars = dict(table='invc.customer', columns='$account_name',
                order_by='$account_name', selectionName='d9_plain', limit=3)
    handler.getSelection(**pars)
    pkeys = handler.freezedSelectionPkeys(table='invc.customer',
                                          selectionName='d9_plain')
    assert len(pkeys) == 3
    assert all(isinstance(pkey, str) for pkey in pkeys)


# ---------------------------------------------------------------------------
#  F4 - the end of a bracket column group
# ---------------------------------------------------------------------------

def test_bracket_group_closes_on_its_last_column(either_handler):
    """F4 - the group end was tested after the bracket had been stripped.

    ``col`` has already lost its ``]`` when the closing test runs, so
    ``maintable`` is never emptied and every column after the group keeps the
    prefix of the group: ``$account_name`` became ``@state.$account_name`` and
    the query looked for it on the related table.
    """
    tblobj = either_handler.db.table('invc.customer')
    columns, _ = either_handler._getSelection_columns(tblobj, '@state[name,code],$account_name')
    assert columns == '@state.name,@state.code,$account_name'


def test_bracket_group_query_runs(either_handler):
    """The column list the group produces is one the database accepts."""
    rows, _ = either_handler.getSelection(table='invc.customer',
                                          columns='@state[name],$account_name',
                                          order_by='$account_name', limit=2)
    rows = list(rows)
    assert len(rows) == 2
    assert rows[0].attr['account_name'] is not None


def test_columns_without_a_group_are_unchanged(handler):
    """The control: no bracket, nothing to close."""
    tblobj = handler.db.table('invc.customer')
    columns, _ = handler._getSelection_columns(tblobj, '$account_name,@state.name')
    assert columns == '$account_name,@state.name'


# ---------------------------------------------------------------------------
#  DS5 - the sqlArgs of the two search stages
# ---------------------------------------------------------------------------

def test_search_stages_do_not_share_their_sqlargs(handler, db_sqlite):  # noqa: F811
    """DS5 - one dict was handed to both ``contains`` and ``startswith``. A pin.

    The second stage received the dict the first had already filled. That
    changed no answer: the second stage takes its own label from the length of
    the dict (``storeArgs``), so its condition binds ``:v_1`` and the leftover
    ``v_0`` is an unused parameter. This pins the dict each stage is handed,
    not a result. The spy lets the real method run and records only the state
    of the dict.
    """
    calls = []
    tblobj = db_sqlite.table('invc.customer')
    original = tblobj.__class__.opTranslate

    def spy(column, op, value, dtype=None, sqlArgs=None):
        calls.append((op, dict(sqlArgs or {})))
        return original(tblobj, column, op, value, dtype=dtype, sqlArgs=sqlArgs)

    tblobj.opTranslate = spy
    try:
        handler.dbSelect(dbtable='invc.customer', columns='$account_name',
                         querystring='a', limit=1)
    finally:
        del tblobj.opTranslate
    assert [op for op, _ in calls] == ['contains', 'startswith']
    assert calls[0][1] == {}
    assert calls[1][1] == {}


# ---------------------------------------------------------------------------
#  D8 - the width of a narrow column
# ---------------------------------------------------------------------------

def _width_for(handler, db, size):
    """The width gridSelectionStruct computes for a column declared *size* wide."""
    selection = db.table('invc.customer').query(columns='$account_name',
                                                limit=1).selection()
    selection.colAttrs['account_name']['size'] = str(size)
    selection.colAttrs['account_name'].pop('print_width', None)
    structure = handler.gridSelectionStruct(selection)
    # child() numbers its labels: the one cell is view_0.row_0.account_name
    cell = structure.getNode('#0.#0.#0')
    return int(cell.attr['width'].replace('em', ''))


@pytest.mark.parametrize('size,expected', [(1, 1), (2, 2), (4, 3), (8, 5), (25, 11)])
def test_column_width_is_pinned_across_the_size_chain(handler, db_sqlite,    # noqa: F811
                                                      size, expected):
    """D8 - the chain of widths, pinned. Not a ratchet, and that is the point.

    The D8 fix changes no width at all. ``if size < 6`` where the chain needed
    ``elif`` did let both branches run for a size under 3, but ``int(width)``
    truncates before the ``.7`` factor, so 1.1 collapses to 1 and 2.2 to 2 and
    the em value is the same either way. The code was wrong and is now right;
    nothing a user can see moved, and these cases pass before and after.
    """
    assert _width_for(handler, db_sqlite, size) == expected
