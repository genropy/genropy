"""Shared infrastructure of the GnrWebAppHandler / GnrWebAppHandlerNext suites.

The two handlers are compared flow by flow, one test module per flow, and they
all need the same three things: a real ``test_invoice`` database, a stand-in
page carrying the page services the flows use, and one handler of each class
built on it.  They live here so the flow modules hold only their own cases.

The database is real: the ``test_invoice`` project on a temporary sqlite file,
with the CSV data of projects/test_invoice/data/export imported by the same
loader the sql suite uses.  Queries, selections, records and adm.userobject
rows are real too.  Only the HTTP page context is replaced, because the suite
has no infrastructure that produces a live GnrWebPage: the stand-in carries the
page services the flows need (page store, user store, freezing, locale,
permissions, rpc method lookup, eagers, maintable) and nothing else.
"""

import os
import shutil
import tempfile

import pytest

from core.common import BaseGnrTest
from sql.conftest import _db_pg, _import_csv_data

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.lib.services.storage import BaseLocalService, StorageNode
from gnr.web._gnrbasewebpage import GnrBaseWebPage
from gnr.web.gnrwebpage import EXCEPTIONS as PAGE_EXCEPTIONS
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler
from gnr.web.gnrwebpage_proxy.apphandler_next import GnrWebAppHandlerNext


# ---------------------------------------------------------------------------
#  The stand-in page
# ---------------------------------------------------------------------------

class _MemoryStore:
    """In memory replacement for the daemon backed page/user store.

    One instance per store, so the page store of one page is not the page
    store of another and the cross page writes of ``_handleLinkedSelection``
    land where a real :class:`GnrWebPage` would put them.

    ``__enter__`` and ``__exit__`` append to the shared *log* of the page
    instead of locking a daemon, so a test can assert how many stores a flow
    opens and in which order it nests them.

    What it does not reproduce: ``getItem`` returns the live :class:`Bag`,
    while the real ``ServerStore`` returns a detached one, so a mutation of a
    fetched bag that is never written back with ``setItem`` persists here and
    would be lost there.
    """

    def __init__(self, name, log):
        self.name = name
        self.log = log
        self.data = Bag()
        self.enter_count = 0
        self.exit_count = 0

    def __enter__(self):
        self.enter_count += 1
        self.log.append(('enter', self.name))
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.exit_count += 1
        self.log.append(('exit', self.name))
        return False

    def getItem(self, path, default=None, **kwargs):
        value = self.data[path]
        return default if value is None else value

    def setItem(self, path, value=None, **kwargs):
        self.data.setItem(path, value)

    def popNode(self, path, **kwargs):
        return self.data.popNode(path)


class _StandInRegister:
    """Only the page ids added to ``live_pages`` are registered."""

    def __init__(self):
        self.live_pages = set()

    def exists(self, page_id, register_name=None):
        return page_id in self.live_pages


class _StandInSite:
    """The site services the flows use: the register, and a local storage.

    ``storageNode`` is unavailable until ``mountStorage`` has been called with a
    folder, because the flows that need it are the file system ones and nothing
    else should reach a filesystem by accident.  Once mounted it is the real
    :class:`gnr.lib.services.storage.BaseLocalService` rooted at that folder, as
    ``tests/core/pdfsite.py`` does, so the storage nodes, the resolvers and the
    deletions are real.
    """

    external_host = 'http://localhost/'

    def __init__(self, gnrapp):
        self.gnrapp = gnrapp
        self.register = _StandInRegister()
        self.storage_service = None

    def mountStorage(self, base_path, service_name='temp'):
        """Root a real local storage service at *base_path*."""
        service = BaseLocalService(parent=self, base_path=base_path)
        service.service_name = service_name
        self.storage_service = service
        return service

    def storageNode(self, path, **kwargs):
        if self.storage_service is None:
            raise RuntimeError('no storage mounted on the stand-in site')
        if isinstance(path, StorageNode):
            return path
        return StorageNode(parent=self, path=str(path).split(':', 1)[-1],
                           service=self.storage_service)


class _StandInUtils:
    """The ``page.utils`` services the flows use.

    ``quickThermo`` yields the rows one by one, as the real one does, and
    records the call so a test can assert the title and the label field the
    flow chose instead of the progress it would have sent to a client.
    """

    def __init__(self):
        self.thermo_calls = []

    def quickThermo(self, iterator, maxidx=None, labelfield=None, title=None,
                    **kwargs):
        rows = list(iterator)
        self.thermo_calls.append(dict(maxidx=maxidx, labelfield=labelfield,
                                      title=title, rowcount=len(rows)))
        for row in rows:
            yield row


class _StandInPage:
    """The page services of the compared flows, and nothing more.

    Freezing is not reimplemented: the four freeze methods call the real
    GnrBaseWebPage implementations unbound, as _gnrbasewebpage_test.py does.
    ``exception`` is the body of :meth:`gnr.web.gnrwebpage.GnrWebPage.exception`
    on the real exception registry; ``checkTablePermission`` is the one service
    the stand-in decides by itself, because the real one reads the user table
    configuration out of ``adm`` — a test sets ``forbidden_permissions`` and the
    calls land in ``permission_calls``.
    """

    def __init__(self, db, connectionFolder, page_id='test_page'):
        self.db = db
        self.connectionFolder = connectionFolder
        self.page_id = page_id
        self.locale = 'en'
        self.user = 'admin'
        self.avatar = None
        self.site = _StandInSite(db.application)
        self.rpc_methods = {}
        self.published = []
        self.eagers = {}
        self.maintable = None
        self._event_subscribers = {}
        self.store_log = []
        self._stores = {}
        self.utils = _StandInUtils()
        self.forbidden_permissions = set()
        self.permission_calls = []

    # --- proxy machinery ---

    def _subscribe_event(self, event, caller):
        self._event_subscribers.setdefault(event, []).append(caller)

    @property
    def application(self):
        return self.site.gnrapp

    # --- page services ---

    @property
    def permissionPars(self):
        return dict(user=self.user, user_group=None)

    def _store(self, name):
        """The store called *name*, created on first use."""
        if name not in self._stores:
            self._stores[name] = _MemoryStore(name, self.store_log)
        return self._stores[name]

    def pageStore(self, page_id=None, triggered=True):
        return self._store('page:%s' % (page_id or self.page_id))

    def userStore(self, user=None, triggered=True):
        return self._store('user:%s' % (user or self.user))

    def getPublicMethod(self, prefix, method):
        if callable(method):
            return method
        return self.rpc_methods.get(method)

    def clientPublish(self, topic, **kwargs):
        self.published.append((topic, kwargs))

    def onLoadingRelatedMethod(self, table, sqlContextName=None):
        """The implementation of GnrWebPage:1032, which th_lib.py repeats."""
        return 'onLoading_%s' % table.replace('.', '_')

    def checkTablePermission(self, table=None, permissions=None):
        """True unless the test listed one of *permissions* as forbidden."""
        self.permission_calls.append((table, permissions))
        if not permissions:
            return True
        asked = set(permissions.split(',') if isinstance(permissions, str)
                    else permissions)
        return not asked.intersection(self.forbidden_permissions)

    def exception(self, exception, **kwargs):
        """The body of GnrWebPage.exception, on the real exception registry."""
        if isinstance(exception, str):
            exception = PAGE_EXCEPTIONS[exception]
        return exception(user=self.user, localizer=self.application.localizer,
                         **kwargs)

    def _(self, value):
        """The localizer the relation captions go through."""
        return value

    # --- freezing, on the real implementations ---

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


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def gnr_test_config():
    """A genro configuration for the module, as tests/sql/conftest.py does."""
    if os.environ.get('GENRO_GNRFOLDER'):
        yield
        return
    BaseGnrTest.setup_class()
    try:
        yield
    finally:
        BaseGnrTest.teardown_class()


@pytest.fixture(scope='module')
def db(gnr_test_config):
    """The test_invoice application on a temporary sqlite database."""
    tmpdir = tempfile.mkdtemp()
    app = None
    try:
        app = GnrApp('test_invoice', db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(tmpdir, 'testing'),
        ))
        app.db.model.check(applyChanges=True)
        _import_csv_data(app.db)
        yield app.db
    finally:
        if app is not None:
            app.db.closeConnection()
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope='module')
def db_with_external_store(db):
    """The same database, also registered as the auxiliary store ``extstore``.

    ``SelectionHandler.mergeExternalStoreColumns`` opens ``db.tempEnv(storename=...)`` on
    the store name the rows carry in their ``_external_store`` column, so its
    body cannot run without a second registered store.  Registering the sqlite
    file of the ``db`` fixture under a second name gives a real store, with its
    own connection parameters and its own connection, and the data the
    assertions need is already in it.
    """
    storename = 'extstore'
    db.stores_handler.add_auxstore(storename, dbattr=dict(
        dbname=db.dbname, implementation='sqlite'))
    try:
        yield db
    finally:
        db.auxstores.pop(storename, None)


@pytest.fixture(scope='module')
def db_postgres(request, gnr_test_config):
    """The test_invoice application on postgres.

    adm.userobject carries formula columns built on ``string_to_array``, which
    sqlite does not have, so ``loadUserObject`` — and with it every saved query
    and saved view — can only be exercised here.
    """
    yield from _db_pg(request, 'postgres')


@pytest.fixture
def make_handlers(tmp_path):
    """Build one handler of each class on a given database."""
    def build(db):
        handlers = []
        for name, handler_class in (('legacy', GnrWebAppHandler),
                                    ('next', GnrWebAppHandlerNext)):
            page = _StandInPage(db, str(tmp_path / name))
            handler = handler_class(page)
            # _prepareRpcQuery reaches the handler back through page.app
            page.app = handler
            handlers.append(handler)
        return tuple(handlers)
    return build


@pytest.fixture
def handlers(make_handlers, db):
    return make_handlers(db)


@pytest.fixture
def pg_handlers(make_handlers, db_postgres):
    return make_handlers(db_postgres)


@pytest.fixture
def external_store_handlers(make_handlers, db_with_external_store):
    return make_handlers(db_with_external_store)


@pytest.fixture
def storage_handlers(handlers, tmp_path):
    """The two handlers, with a real local storage mounted on both sites.

    The file system flows read and delete through
    :class:`gnr.lib.services.storage.BaseLocalService` rooted at *tmp_path*, so
    the storage nodes, the resolvers, the XML reads and the deletions are the
    real ones and only the folder is temporary.  The handlers share the folder,
    which is what lets a file written once be seen by both.

    Returns:
        ``(legacy, next, root)``, the two handlers and the folder they see.
    """
    for handler in handlers:
        handler.page.site.mountStorage(str(tmp_path))
    return handlers[0], handlers[1], tmp_path


# ---------------------------------------------------------------------------
#  Comparison helpers
# ---------------------------------------------------------------------------

VOLATILE_ATTRIBUTES = ('servertime', 'newproc')


def normalized_attributes(attributes, ignore=()):
    """Drop the volatile attributes, and the ones a divergence covers."""
    return {k: v for k, v in attributes.items()
            if k not in VOLATILE_ATTRIBUTES and k not in ignore}
