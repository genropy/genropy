#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Surface tests for SqlRecord public API.
Tests out_dict, out_json, out_record, out_bag, out_newrecord, out_template.
"""

from gnr.sql.gnrsql import GnrSqlDb
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqldata import SqlRecord, SqlRecordBag
from gnr.sql.gnrsql_exceptions import RecordNotExistingError, SelectionExecutionError

import pytest

from .common import BaseGnrSqlTest, configureDb


class BaseRecordSurface(BaseGnrSqlTest):
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
        cls.db.closeConnection()
        cls.db.dropDb(cls.dbname)

    # --- out_bag ---

    def test_out_bag(self):
        tbl = self.db.table('video.movie')
        record = tbl.record(pkey=0, mode='bag')
        assert isinstance(record, Bag)
        assert record['title'] == 'Match point'

    # --- out_dict ---

    def test_out_dict(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('dict')
        assert isinstance(result, dict)
        assert result['title'] == 'Match point'

    # --- out_json ---

    def test_out_json(self):
        import json
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('json')
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['title'] == 'Match point'

    # --- out_record ---

    def test_out_record(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('record')
        assert isinstance(result, Bag)
        assert result['title'] == 'Match point'

    # --- out_newrecord ---

    def test_out_newrecord(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=None, ignoreMissing=True)
        result = rec.output('newrecord')
        assert isinstance(result, SqlRecordBag)

    # --- out_template ---

    def test_out_template(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('template', recordtemplate='Film: $title ($year)')
        assert 'Match point' in result

    # --- ignoreMissing ---

    def test_ignoreMissing_true(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=99999, ignoreMissing=True)
        result = rec.output('bag')
        assert isinstance(result, Bag)

    def test_ignoreMissing_false(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=99999, ignoreMissing=False)
        with pytest.raises(RecordNotExistingError):
            rec.output('bag')

    # --- invalid output mode ---

    def test_invalid_output_mode(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        with pytest.raises(SelectionExecutionError):
            rec.output('nonexistent')

    # --- setJoinCondition ---

    def test_setJoinCondition(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        rec.setJoinCondition(target_fld='video.cast.movie_id',
                             from_fld='video.movie.id',
                             condition='TRUE')
        result = rec.output('bag')
        assert isinstance(result, Bag)

    # --- compiled property ---

    def test_compiled_property(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        compiled = rec.compiled
        assert compiled is not None
        assert hasattr(compiled, 'resultmap')

    # --- SqlRecordBag ---

    def test_sqlrecordbag_init(self):
        rb = SqlRecordBag(self.db, 'video.movie')
        assert rb.isNew is True
        assert rb.db is self.db
        assert rb.tablename == 'video.movie'

    def test_sqlrecordbag_db_property(self):
        rb = SqlRecordBag(None, 'video.movie')
        assert rb.db is None
        rb.db = self.db
        assert rb.db is self.db

    # --- out_sample ---

    def test_out_sample(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=None, ignoreMissing=True)
        result = rec.output('sample')
        assert isinstance(result, SqlRecordBag)

    # --- out_bag with resolver ---

    def test_out_bag_with_resolvers(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('bag', resolver_one=True, resolver_many=True)
        assert isinstance(result, Bag)
        assert result['title'] == 'Match point'

    # --- record with where clause ---

    def test_record_with_where(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, where='$title=:t', sqlparams={'t': 'Match point'})
        result = rec.output('bag')
        assert isinstance(result, Bag)
        assert result['title'] == 'Match point'

    # --- record with kwargs ---

    def test_record_with_kwargs(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, id=0)
        result = rec.output('bag')
        assert isinstance(result, Bag)
        assert result['title'] == 'Match point'

    # --- out_dict keys ---

    def test_out_dict_keys(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('dict')
        assert 'title' in result
        assert 'year' in result
        assert 'nationality' in result

    # --- record with virtual_columns ---

    def test_record_with_bagFields_false(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0, bagFields=False)
        result = rec.output('bag')
        assert isinstance(result, Bag)

    # --- ignoreDuplicate ---

    def test_ignoreDuplicate(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0, ignoreDuplicate=True)
        result = rec.output('bag')
        assert isinstance(result, Bag)

    # --- record via table.record ---

    def test_table_record_mode_dict(self):
        tbl = self.db.table('video.movie')
        result = tbl.record(pkey=0, mode='dict')
        assert isinstance(result, dict)
        assert result['title'] == 'Match point'

    def test_table_record_mode_json(self):
        import json
        tbl = self.db.table('video.movie')
        result = tbl.record(pkey=0, mode='json')
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['title'] == 'Match point'

    # --- record with cast relations ---

    def test_record_cast_with_relation(self):
        tbl = self.db.table('video.cast')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('bag', resolver_one=True)
        assert isinstance(result, Bag)

    # --- newrecord defaults ---

    def test_out_newrecord_is_new(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=None, ignoreMissing=True)
        result = rec.output('newrecord')
        assert isinstance(result, SqlRecordBag)
        assert result.isNew is True

    # --- SqlRecordBag tablename ---

    def test_sqlrecordbag_tablename(self):
        rb = SqlRecordBag(self.db, 'video.movie')
        assert rb.tablename == 'video.movie'

    def test_sqlrecordbag_isNew_defaults(self):
        rb = SqlRecordBag(self.db, 'video.movie')
        assert rb.isNew is True

    # --- record with relations traversed ---

    def test_record_with_relation_one(self):
        tbl = self.db.table('video.cast')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('bag', resolver_one=True, resolver_many=True)
        assert isinstance(result, Bag)
        assert result['role'] is not None

    def test_record_movie_with_many_relation(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('bag', resolver_one=True, resolver_many=True)
        assert isinstance(result, Bag)
        assert result['title'] == 'Match point'

    # --- record out_dict complete ---

    def test_out_dict_complete(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('dict')
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'title' in result
        assert 'year' in result
        assert 'nationality' in result
        assert 'genre' in result

    # --- record compiled resultmap ---

    def test_compiled_resultmap(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        compiled = rec.compiled
        assert isinstance(compiled.resultmap, Bag)
        assert len(compiled.resultmap) > 0

    # --- record compiled where ---

    def test_compiled_where(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        compiled = rec.compiled
        assert compiled.where is not None
        assert 'pkey' in compiled.where

    # --- record with for_update ---

    def test_record_compiled_for_update(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0, for_update=True)
        compiled = rec.compiled
        assert compiled.for_update is True

    # --- record compiled get_sqltext ---

    def test_compiled_get_sqltext(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=0)
        sql = rec.compiled.get_sqltext(self.db)
        assert isinstance(sql, str)
        assert 'SELECT' in sql.upper()

    # --- record output record mode ---

    def test_out_record_empty_on_missing(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=99999, ignoreMissing=True)
        result = rec.output('record')
        assert isinstance(result, Bag)

    # --- newrecord with defaults ---

    def test_newrecord_has_table_defaults(self):
        tbl = self.db.table('video.movie')
        rec = SqlRecord(tbl, pkey=None, ignoreMissing=True)
        result = rec.output('newrecord')
        assert isinstance(result, SqlRecordBag)

    # --- dvd record with relation ---

    def test_dvd_record_with_movie_relation(self):
        tbl = self.db.table('video.dvd')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('bag', resolver_one=True)
        assert isinstance(result, Bag)

    # --- cast record with multiple relations ---

    def test_cast_record_all_relations(self):
        tbl = self.db.table('video.cast')
        rec = SqlRecord(tbl, pkey=0)
        result = rec.output('bag', resolver_one=True, resolver_many=False)
        assert isinstance(result, Bag)


class TestRecordSurface_sqlite(BaseRecordSurface):
    @classmethod
    def init(cls):
        cls.name = 'sqlite'
        cls.dbname = cls.CONFIG['db.sqlite?filename']
        cls.db = GnrSqlDb(dbname=cls.dbname)


class TestRecordSurface_postgres(BaseRecordSurface):
    @classmethod
    def init(cls):
        cls.name = 'postgres'
        cls.dbname = 'test_rec_surface'
        cls.db = GnrSqlDb(implementation='postgres',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password"))
