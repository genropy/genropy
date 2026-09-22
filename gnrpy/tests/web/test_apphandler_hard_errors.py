"""Four defects of GnrWebAppHandler that fail outright on the path they sit on.

Each one raises, or hands the caller a value the caller cannot use, the first
time the flow is exercised. They were found while building the handler copy of
#1387 and are recorded there as D4, D7, DS7 and E10; this module fixes them in
the handler every instance actually runs. DS6 comes along because it sits on the
same three lines of ``getMultiFetch`` as DS7.

The database is real: the ``test_invoice`` project on sqlite, with the CSV data
of projects/test_invoice/data/export imported by the loader the sql suite uses.
Only the HTTP page context is replaced by a stand-in, because the suite has no
infrastructure that produces a live GnrWebPage.
"""

import os

import pytest

from core.common import BaseGnrTest
from sql.conftest import db_sqlite, sqlite_temp_dir        # noqa: F401  (fixtures)

from gnr.core.gnrbag import Bag
from gnr.web._gnrbasewebpage import GnrBaseWebPage
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler


class _MemoryStore:
    """In memory replacement for the daemon backed page/user store."""

    def __init__(self):
        self.data = Bag()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        return False

    def getItem(self, path, default=None, **kwargs):
        value = self.data[path]
        return default if value is None else value

    def setItem(self, path, value=None, **kwargs):
        self.data.setItem(path, value)

    def popNode(self, path, **kwargs):
        return self.data.popNode(path)


class _StandInRegister:

    def exists(self, page_id, register_name=None):
        return False


class _StandInSite:

    def __init__(self, gnrapp):
        self.gnrapp = gnrapp
        self.register = _StandInRegister()


class _PageException(Exception):
    """What GnrWebPage.exception builds, reduced to what these flows need."""

    def __init__(self, kind, description=None):
        self.kind = kind
        self.description = description
        super().__init__(description)


class _StandInPage:
    """The page services these four flows use, and nothing more."""

    def __init__(self, db, connectionFolder, page_id='test_page'):
        self.db = db
        self.connectionFolder = connectionFolder
        self.page_id = page_id
        self.locale = 'en'
        self.user = 'admin'
        self.avatar = None
        self.site = _StandInSite(db.application)
        self.permissions = True
        self.published = []
        self._event_subscribers = {}
        self._page_store = _MemoryStore()
        self._user_store = _MemoryStore()

    def _subscribe_event(self, event, caller):
        self._event_subscribers.setdefault(event, []).append(caller)

    @property
    def application(self):
        return self.site.gnrapp

    @property
    def permissionPars(self):
        return dict(user=self.user, user_group=None)

    def checkTablePermission(self, table=None, permissions=None):
        return self.permissions

    def exception(self, kind, description=None, **kwargs):
        return _PageException(kind, description=description)

    def pageStore(self, page_id=None, triggered=True):
        return self._page_store

    def userStore(self, user=None, triggered=True):
        return self._user_store

    def getPublicMethod(self, prefix, method):
        return method if callable(method) else None

    def clientPublish(self, topic, **kwargs):
        self.published.append((topic, kwargs))

    def pageLocalDocument(self, docname, page_id=None):
        return GnrBaseWebPage.pageLocalDocument(self, docname, page_id=page_id)

    def freezeSelection(self, selection, name, **kwargs):
        return GnrBaseWebPage.freezeSelection(self, selection, name, **kwargs)

    def freezeSelectionUpdate(self, selection):
        return GnrBaseWebPage.freezeSelectionUpdate(self, selection)

    def unfreezeSelection(self, dbtable=None, name=None, page_id=None):
        return GnrBaseWebPage.unfreezeSelection(self, dbtable=dbtable, name=name,
                                                page_id=page_id)

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        return GnrBaseWebPage.freezedPkeys(self, dbtable=dbtable, name=name,
                                           page_id=page_id)


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


# ---------------------------------------------------------------------------
#  D4 - the denial message of deleteDbRows and duplicateDbRows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('method_name', ['deleteDbRows', 'duplicateDbRows'])
def test_denial_message_is_built_and_names_the_table(handler, page, method_name):
    """D4 - the message read ``table %`` followed by a space.

    ``'% f'`` is a valid format spec, the one for a float with a space flag, so
    the interpolation raised ``TypeError: must be real number, not str`` while
    building the description. The user was denied with a crash instead of a
    refusal, and the table name never reached the message.
    """
    page.permissions = False
    with pytest.raises(_PageException) as excinfo:
        getattr(handler, method_name)(table='invc.invoice', pkeys=['whatever'])
    assert excinfo.value.kind == 'generic'
    assert 'invc.invoice' in excinfo.value.description
    assert 'admin' in excinfo.value.description


# ---------------------------------------------------------------------------
#  D7 - the pkey saveRecord returns for a new record
# ---------------------------------------------------------------------------

def test_saveRecord_returns_the_pkey_the_insert_wrote(handler, db_sqlite):
    """D7 - on ``*newrecord*`` it returned ``data[pkey]``, which the client never sent.

    The client sends the literal ``'*newrecord*'`` as the pkey and a payload
    with no pkey of its own, so the answer carried ``None`` from a Bag payload
    and raised ``KeyError`` from a plain dict. The form kept ``*newrecord*`` as
    its current pkey and the record it had just written was unreachable.
    """
    tblobj = db_sqlite.table('invc.customer')
    result = handler.saveRecord(table='invc.customer', pkey='*newrecord*',
                                data=dict(account_name='D7 new customer'))
    saved_pkey = result['pkey']
    assert saved_pkey
    written = tblobj.record(pkey=saved_pkey).output('dict')
    assert written['account_name'] == 'D7 new customer'


def test_saveRecord_on_an_update_keeps_the_pkey_of_the_payload(handler, db_sqlite):
    """The update branch is unchanged: the pkey is the one *data* carries."""
    tblobj = db_sqlite.table('invc.customer')
    pkey = tblobj.query(columns='$id', limit=1).fetch()[0]['id']
    result = handler.saveRecord(table='invc.customer', pkey=pkey,
                                data={tblobj.pkey: pkey, 'account_name': 'D7 renamed'})
    assert result['pkey'] == pkey
    assert tblobj.record(pkey=pkey).output('dict')['account_name'] == 'D7 renamed'


# ---------------------------------------------------------------------------
#  DS7 - the documented default of getMultiFetch
# ---------------------------------------------------------------------------

def test_getMultiFetch_accepts_its_documented_star_default(handler):
    """DS7 - ``columns='*'`` went through ``columnsFromString`` and became ``$*``.

    ``'*'`` is the default the signature documents, and no caller has to spell
    it out to hit this: omitting ``columns`` altogether reaches the same line.
    The database rejected ``$*``, so the documented default never worked.
    """
    queries = Bag()
    queries.setItem('all_columns', None, table='invc.customer', limit=2)
    queries.setItem('star', None, table='invc.customer', columns='*', limit=2)
    result = handler.getMultiFetch(queries=queries)
    for label in ('all_columns', 'star'):
        rows = result[label]
        assert len(rows) == 2
        # fetchAsBag puts the row in the attributes of its node: '*' has to
        # bring every column, not merely avoid the crash
        columns = rows.getNode('#0').attr
        assert columns['account_name'] is not None
        assert {'email', 'phone', 'customer_type_code'} <= set(columns)


def test_getMultiFetch_leaves_the_caller_bag_alone(handler):
    """DS6 - ``columns`` and ``table`` were popped off the caller's own node.

    The attributes were read with ``query.attr.pop``, which empties the Bag the
    caller passed in: a second call on the same Bag found no table and raised
    ``KeyError``. The copy is taken first, so the caller keeps what it built.
    """
    queries = Bag()
    queries.setItem('first', None, table='invc.customer',
                    columns='$account_name', limit=2)
    handler.getMultiFetch(queries=queries)
    assert queries.getNode('first').attr['table'] == 'invc.customer'
    assert queries.getNode('first').attr['columns'] == '$account_name'
    again = handler.getMultiFetch(queries=queries)['first']
    assert len(again) == 2


def test_getMultiFetch_still_resolves_a_named_column_list(handler):
    """A real column list keeps going through columnsFromString."""
    queries = Bag()
    queries.setItem('named', None, table='invc.customer',
                    columns='$account_name', limit=2)
    rows = handler.getMultiFetch(queries=queries)['named']
    assert len(rows) == 2
    columns = rows.getNode('#0').attr
    assert 'account_name' in columns
    assert 'email' not in columns


# ---------------------------------------------------------------------------
#  E10 - hardQueryLimitOver on a selection replayed from its pickle
# ---------------------------------------------------------------------------

def test_hard_query_limit_over_on_a_frozen_selection(handler):
    """E10 - ``resultAttributes['totalrows']`` is written on the new path only.

    A selection read back from its pickle skips the branch that writes it, so
    the line that computes ``hardQueryLimitOver`` raised ``KeyError:
    'totalrows'`` and the whole call died. The count comes from the selection
    itself, which both paths have.
    """
    pars = dict(table='invc.customer', columns='$account_name',
                order_by='$account_name', selectionName='e10_selection',
                hardQueryLimit=3)
    first_rows, first_attrs = handler.getSelection(**pars)
    assert first_attrs['hardQueryLimitOver'] is True
    replayed_rows, replayed_attrs = handler.getSelection(**pars)
    assert replayed_attrs['debug'] == 'fromPickle'
    assert replayed_attrs['hardQueryLimitOver'] is True
    assert len(replayed_rows) == len(first_rows)


def test_hard_query_limit_not_over_keeps_the_flag_false(handler):
    """Under the limit the flag stays false on both paths."""
    pars = dict(table='invc.customer', columns='$account_name',
                order_by='$account_name', selectionName='e10_under',
                limit=2, hardQueryLimit=5000)
    _, first_attrs = handler.getSelection(**pars)
    _, replayed_attrs = handler.getSelection(**pars)
    assert first_attrs['hardQueryLimitOver'] is False
    assert replayed_attrs['hardQueryLimitOver'] is False
