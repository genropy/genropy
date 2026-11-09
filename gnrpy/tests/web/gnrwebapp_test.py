"""Db-events of a transaction on a real database, with no page observing (#1821).

The events recorded by ``GnrWsgiWebApp.notifyDbEvent`` are read server side too:
by ``Table.dbevents`` and by ``db.autoCommit()``, which every resource batch calls
at the end of its run. Neither may depend on which pages happen to be open.

GnrDummySite has no page register: ``allSubscribedTables()`` answers ``[]``, so
nothing is observed, and its ``FakeRegister`` has no ``notifyDbEvents``, so an
event leaking into the send path makes the commit fail.
"""

import pytest

from core.common import BaseGnrTest

import gnr.web.gnrwebapp  # noqa: F401
from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import getUuid
from gnr.web.gnrdummysite import GnrDummySite


class TestDbEventsWithoutObservers(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        cls.db = cls.site.db
        cls.tblobj = cls.db.table('adm.userobject')

    def setup_method(self):
        self.db.clearCurrentEnv()

    def teardown_method(self):
        self.db.rollback()

    def _newrecord(self):
        return self.tblobj.newrecord(code=getUuid(), objtype='dbevents_test')

    def _stored(self, record):
        return self.tblobj.existsRecord(record['id'])

    def test_a_commit_callback_reads_the_events_of_an_unobserved_table(self):
        seen = []
        record = self._newrecord()
        self.tblobj.insert(record)
        self.tblobj.delete(record)
        self.db.deferToCommit(lambda: seen.extend(self.tblobj.dbevents))
        self.db.commit()
        assert [(e['dbevent'], e['pkey']) for e in seen] == [('I', record['id']),
                                                              ('D', record['id'])]
        assert not any('objtype' in e for e in seen)

    def test_auto_commit_persists_a_flagged_write(self):
        record = self._newrecord()
        with self.db.tempEnv(autoCommit=True):
            self.tblobj.insert(record)
        self.db.autoCommit()
        self.db.rollback()
        assert self._stored(record)

    def test_auto_commit_refuses_an_unflagged_write(self):
        flagged = self._newrecord()
        with self.db.tempEnv(autoCommit=True):
            self.tblobj.insert(flagged)
        unflagged = self._newrecord()
        self.tblobj.insert(unflagged)
        with pytest.raises(self.db.exceptions['missedCommit']):
            self.db.autoCommit()
        self.db.rollback()
        assert not self._stored(flagged)
        assert not self._stored(unflagged)
