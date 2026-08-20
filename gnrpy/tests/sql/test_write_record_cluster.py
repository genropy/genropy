#!/usr/bin/env python3
# encoding: utf-8
"""Tests for SqlTable.writeRecordCluster / _splitRecordCluster.

Focus: degenerate relation nodes in the changeset (issue #998). Clients can
leak `@relname` nodes that are not edits — an invalidated related-one cache
(value None) or a memory-store copy of the record whose relation nodes lost
the `mode` attribute. The split must drop the former and classify the latter
through the model instead of trusting the wire attribute.
"""

import os
import shutil
import tempfile

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsql import GnrSqlDb

from .common import BaseGnrSqlTest, configureDb


class TestWriteRecordCluster(BaseGnrSqlTest):
    @classmethod
    def init(cls):
        cls.name = 'sqlite'
        cls.dbname = os.path.join(tempfile.mkdtemp(), 'test_wrc.db')
        cls.db = GnrSqlDb(dbname=cls.dbname)

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.init()
        cls.db.createDb(cls.dbname)
        configureDb(cls.db)
        cls.db.startup()
        cls.db.checkDb(applyChanges=True)
        cls.db.importXmlData(cls.SAMPLE_XMLDATA)
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        # BaseGnrSqlTest.teardown_class drops the db file: the mkdtemp folder
        # that contained it is ours to remove.
        dbfolder = os.path.dirname(cls.dbname)
        super().teardown_class()
        shutil.rmtree(dbfolder, ignore_errors=True)

    def _split(self, tblobj, cluster):
        """Route a copy of *cluster* through the split, leaving the original
        untouched for the write: _splitRecordCluster pops the relation nodes.
        """
        return tblobj._splitRecordCluster(cluster.deepcopy())

    def test_none_relation_node_is_skipped(self):
        """A `@relname` node with value None (invalidated related-one cache)
        must be dropped, not routed, and must not abort the save
        (#998: TypeError NoneType not iterable)."""
        tblobj = self.db.table('video.cast')
        cluster = Bag()
        cluster['id'] = 9001
        cluster['movie_id'] = 1
        cluster['person_id'] = 1
        cluster['role'] = 'extra'
        cluster.setItem('@movie_id', None, dtype=None, oldValue=Bag())
        main, relatedOne, relatedMany = self._split(tblobj, cluster)
        # the degenerate node is neither written as a relation...
        assert relatedOne == {}
        assert relatedMany == {}
        # ...nor left in the main record, where it would become a column.
        assert '@movie_id' not in main.keys()
        record = tblobj.writeRecordCluster(
            cluster, dict(_newrecord=True, _pkey=9001))
        self.db.commit()
        # the FK already on the record survives: nothing overwrote it
        assert record['movie_id'] == 1
        saved = tblobj.record(9001).output('dict')
        assert saved['role'] == 'extra'
        assert saved['movie_id'] == 1

    def test_none_many_relation_node_is_skipped(self):
        """Same guard on a node that would land in relatedMany (no joiner for
        its label): value None means nothing to write. Without the guard the
        node reaches the relatedMany loop and iterating None raises."""
        tblobj = self.db.table('video.movie')
        cluster = Bag()
        cluster['id'] = 9002
        cluster['title'] = 'Cluster Movie'
        cluster.setItem('@casting_removed', None)
        main, relatedOne, relatedMany = self._split(tblobj, cluster)
        assert relatedOne == {}
        assert relatedMany == {}
        assert '@casting_removed' not in main.keys()
        cast_before = self.db.table('video.cast').query().count()
        record = tblobj.writeRecordCluster(
            cluster, dict(_newrecord=True, _pkey=9002))
        self.db.commit()
        assert record['title'] == 'Cluster Movie'
        # the dropped `_removed` node must not have deleted any cast row
        assert self.db.table('video.cast').query().count() == cast_before

    def test_lost_mode_is_recovered_from_model(self):
        """A related-one cluster whose `mode` attribute was lost in a copy
        must still be routed to relatedOne via the model, writing the related
        record and back-filling the FK on the main one."""
        tblobj = self.db.table('video.cast')
        rel_cluster = Bag()
        rel_cluster['id'] = 9101
        rel_cluster['title'] = 'Recovered Movie'
        cluster = Bag()
        cluster['id'] = 9003
        cluster['person_id'] = 1
        cluster['role'] = 'lead'
        cluster.setItem('@movie_id', rel_cluster, _newrecord=True)
        main, relatedOne, relatedMany = self._split(tblobj, cluster)
        # routed through the model, not through the missing wire attribute
        assert list(relatedOne.keys()) == ['movie_id']
        assert relatedMany == {}
        assert '@movie_id' not in main.keys()
        record = tblobj.writeRecordCluster(
            cluster, dict(_newrecord=True, _pkey=9003))
        self.db.commit()
        assert record['movie_id'] == 9101
        movie = self.db.table('video.movie').record(9101).output('dict')
        assert movie['title'] == 'Recovered Movie'

    def test_explicit_mode_still_wins(self):
        """A node that carries mode='O' keeps the legacy routing untouched."""
        tblobj = self.db.table('video.cast')
        rel_cluster = Bag()
        rel_cluster['id'] = 9102
        rel_cluster['title'] = 'Explicit Movie'
        cluster = Bag()
        cluster['id'] = 9004
        cluster['person_id'] = 1
        cluster['role'] = 'cameo'
        cluster.setItem('@movie_id', rel_cluster, mode='O', _newrecord=True)
        main, relatedOne, relatedMany = self._split(tblobj, cluster)
        assert list(relatedOne.keys()) == ['movie_id']
        assert relatedMany == {}
        assert '@movie_id' not in main.keys()
        record = tblobj.writeRecordCluster(
            cluster, dict(_newrecord=True, _pkey=9004))
        self.db.commit()
        assert record['movie_id'] == 9102
