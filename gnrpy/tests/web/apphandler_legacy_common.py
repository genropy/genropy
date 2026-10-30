"""The page context these legacy app handler tests share.

The flows under test need a page, and the suite has no infrastructure that
produces a live GnrWebPage: what is replaced here is the HTTP context alone,
never the handler and never the database. The pattern comes from
``test_getselection_saved_query_1359.py``.
"""

from gnr.core.gnrbag import Bag
from gnr.web._gnrbasewebpage import GnrBaseWebPage


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

    def _(self, text, **kwargs):
        """The localizer of a real page; here the text is already what it says."""
        return text

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
