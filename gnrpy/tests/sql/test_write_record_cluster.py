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

    def test_none_relation_node_is_skipped(self):
        """A `@relname` node with value None (invalidated related-one cache)
        must not abort the save (#998: TypeError NoneType not iterable)."""
        tblobj = self.db.table('video.cast')
        cluster = Bag()
        cluster['id'] = 9001
        cluster['movie_id'] = 1
        cluster['person_id'] = 1
        cluster['role'] = 'extra'
        cluster.setItem('@movie_id', None, dtype=None, oldValue=Bag())
        record = tblobj.writeRecordCluster(
            cluster, dict(_newrecord=True, _pkey=9001))
        self.db.commit()
        assert record['movie_id'] == 1
        saved = tblobj.record(9001).output('dict')
        assert saved['role'] == 'extra'

    def test_none_many_relation_node_is_skipped(self):
        """Same guard on a node that would land in relatedMany (no joiner
        for its label): value None means nothing to write."""
        tblobj = self.db.table('video.movie')
        cluster = Bag()
        cluster['id'] = 9002
        cluster['title'] = 'Cluster Movie'
        cluster.setItem('@casting_removed', None)
        record = tblobj.writeRecordCluster(
            cluster, dict(_newrecord=True, _pkey=9002))
        self.db.commit()
        assert record['title'] == 'Cluster Movie'

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
        record = tblobj.writeRecordCluster(
            cluster, dict(_newrecord=True, _pkey=9004))
        self.db.commit()
        assert record['movie_id'] == 9102
