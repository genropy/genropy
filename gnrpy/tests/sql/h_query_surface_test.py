#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Surface tests for SqlQuery public API.
Tests fetchAsDict, fetchGrouped, fetchAsBag, fetchPkeys, fetchAsJson,
test(), sqltext property, setJoinCondition.
"""

import json
from collections import OrderedDict

from gnr.sql.gnrsql import GnrSqlDb
from gnr.core.gnrbag import Bag

from .common import BaseGnrSqlTest, configureDb


class BaseQuerySurface(BaseGnrSqlTest):
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

    # --- sqltext property ---

    def test_sqltext_property(self):
        q = self.db.query('video.movie', columns='$title')
        sqltext = q.sqltext
        assert isinstance(sqltext, str)
        assert 'SELECT' in sqltext.upper()

    # --- test() method ---

    def test_test_method(self):
        q = self.db.query('video.movie', columns='$title',
                          where='$year=:y', sqlparams={'y': 2005})
        sqltext, params = q.test()
        assert isinstance(sqltext, str)
        assert params['y'] == 2005

    # --- fetchPkeys ---

    def test_fetchPkeys(self):
        q = self.db.query('video.movie', columns='$id,$title', order_by='$id')
        pkeys = q.fetchPkeys()
        assert isinstance(pkeys, list)
        assert len(pkeys) == 11

    # --- fetchAsJson ---

    def test_fetchAsJson(self):
        q = self.db.query('video.movie', columns='$title,$year',
                          where='$id=:id', sqlparams={'id': 0})
        result = q.fetchAsJson()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]['title'] == 'Match point'

    # --- fetchAsDict ---

    def test_fetchAsDict_default_key(self):
        q = self.db.query('video.movie', columns='$id,$title,$year')
        result = q.fetchAsDict()
        assert isinstance(result, dict)
        assert len(result) == 11

    def test_fetchAsDict_custom_key(self):
        q = self.db.query('video.movie', columns='$id,$title,$year')
        result = q.fetchAsDict(key='title')
        assert 'Match point' in result
        assert result['Match point']['year'] is not None

    def test_fetchAsDict_ordered(self):
        q = self.db.query('video.movie', columns='$id,$title,$year', order_by='$id')
        result = q.fetchAsDict(ordered=True)
        assert isinstance(result, OrderedDict)

    def test_fetchAsDict_pkeyOnly(self):
        q = self.db.query('video.movie', columns='$id,$title,$year')
        result = q.fetchAsDict(key='title', pkeyOnly=True)
        assert isinstance(result, dict)
        first_val = next(iter(result.values()))
        assert not isinstance(first_val, dict)

    # --- fetchAsBag ---

    def test_fetchAsBag(self):
        q = self.db.query('video.movie', columns='$id,$title,$year')
        result = q.fetchAsBag()
        assert isinstance(result, Bag)
        assert len(result) == 11

    # --- fetchGrouped ---

    def test_fetchGrouped_default(self):
        q = self.db.query('video.movie', columns='$title,$year,$nationality')
        result = q.fetchGrouped(key='nationality')
        assert isinstance(result, dict)
        for v in result.values():
            assert isinstance(v, list)

    def test_fetchGrouped_ordered(self):
        q = self.db.query('video.movie', columns='$title,$year,$nationality')
        result = q.fetchGrouped(key='nationality', ordered=True)
        assert isinstance(result, OrderedDict)

    def test_fetchGrouped_asBag(self):
        q = self.db.query('video.movie', columns='$title,$year,$nationality')
        result = q.fetchGrouped(key='nationality', asBag=True)
        assert isinstance(result, Bag)

    # --- setJoinCondition ---

    def test_setJoinCondition(self):
        q = self.db.query('video.dvd', columns='$code,@movie_id.title')
        q.setJoinCondition(target_fld='video.movie.id',
                           from_fld='video.dvd.movie_id',
                           condition='$tbl.year > 2000')
        result = q.selection()
        assert len(result) > 0

    # --- compiled property ---

    def test_compiled_property(self):
        q = self.db.query('video.movie', columns='$title')
        compiled = q.compiled
        assert compiled is not None
        assert hasattr(compiled, 'columns')
        assert hasattr(compiled, 'where')

    # --- count ---

    def test_count(self):
        q = self.db.query('video.movie', columns='$title')
        n = q.count()
        assert n == 11

    def test_count_with_where(self):
        q = self.db.query('video.movie', columns='$title',
                          where='$year=:y', sqlparams={'y': 2005})
        n = q.count()
        assert n == 2

    # --- star columns ---

    def test_star_columns(self):
        q = self.db.query('video.movie', columns='*')
        sel = q.selection()
        assert len(sel) == 11
        cols = sel.allColumns
        assert 'title' in cols
        assert 'year' in cols
        assert 'nationality' in cols

    # --- relations ---

    def test_relation_columns(self):
        q = self.db.query('video.cast',
                          columns='$id,@person_id.name,@movie_id.title,$role')
        sel = q.selection()
        assert len(sel) > 0
        result = sel.output('dictlist')
        assert '_person_id_name' in result[0]
        assert '_movie_id_title' in result[0]

    # --- distinct ---

    def test_distinct_query(self):
        q = self.db.query('video.movie', columns='$nationality',
                          distinct=True)
        sel = q.selection()
        nationalities = sel.output('dictlist')
        values = [r['nationality'] for r in nationalities]
        assert len(values) == len(set(values))

    # --- group_by ---

    def test_group_by(self):
        q = self.db.query('video.movie',
                          columns='$nationality,count($id) AS cnt',
                          group_by='$nationality')
        sel = q.selection()
        assert len(sel) > 0

    # --- order_by ---

    def test_order_by_desc(self):
        q = self.db.query('video.movie', columns='$id,$title,$year',
                          order_by='$year DESC')
        sel = q.selection()
        result = sel.output('dictlist')
        years = [r['year'] for r in result]
        assert years == sorted(years, reverse=True)

    # --- where with multiple conditions ---

    def test_where_multiple_conditions(self):
        q = self.db.query('video.movie', columns='$id,$title',
                          where='$year > :min_year AND $year < :max_year',
                          sqlparams={'min_year': 2004, 'max_year': 2007})
        sel = q.selection()
        assert len(sel) > 0

    # --- selection with sortedBy ---

    def test_selection_sorted_by(self):
        q = self.db.query('video.movie', columns='$id,$title,$year')
        sel = q.selection(sortedBy='year')
        result = sel.output('dictlist')
        years = [r['year'] for r in result]
        assert years == sorted(years)

    # --- limit / offset in query ---

    def test_query_limit(self):
        q = self.db.query('video.movie', columns='$id,$title',
                          order_by='$id', limit=3)
        sel = q.selection()
        assert len(sel) == 3

    def test_query_offset(self):
        q = self.db.query('video.movie', columns='$id,$title',
                          order_by='$id', limit=3, offset=2)
        sel = q.selection()
        assert len(sel) == 3

    # --- fetchAsJson with dates ---

    def test_fetchAsJson_with_dates(self):
        q = self.db.query('video.dvd', columns='$code,$purchasedate,$movie_id',
                          where='$code=:c', sqlparams={'c': 0})
        result = q.fetchAsJson()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    # --- fetchGrouped pkeyOnly ---

    def test_fetchGrouped_pkeyOnly(self):
        q = self.db.query('video.movie',
                          columns='$id,$title,$year,$nationality')
        result = q.fetchGrouped(key='nationality')
        assert isinstance(result, dict)
        for v in result.values():
            assert isinstance(v, list)

    # --- compiled: resultmap, explodingColumns ---

    def test_compiled_resultmap(self):
        q = self.db.query('video.movie', columns='$title,$year')
        compiled = q.compiled
        assert hasattr(compiled, 'resultmap')

    def test_compiled_sqltext(self):
        q = self.db.query('video.movie', columns='$title,$year')
        sql = q.compiled.get_sqltext(self.db)
        assert isinstance(sql, str)
        assert 'SELECT' in sql.upper()

    # --- star columns with relation prefix ---

    def test_star_relation_columns(self):
        q = self.db.query('video.cast', columns='$id,*@movie_id')
        sel = q.selection()
        assert len(sel) > 0
        cols = sel.allColumns
        assert '_movie_id_title' in cols

    # --- IN_RANGE in where (renamed from BETWEEN, issue #622) ---

    def test_in_range_in_where(self):
        """Test #IN_RANGE macro in where clause."""
        q = self.db.query('video.movie', columns='$id,$title,$year',
                          where='#IN_RANGE($year,:y_low,:y_high)',
                          sqlparams={'y_low': 2004, 'y_high': 2006})
        sel = q.selection()
        assert len(sel) > 0
        result = sel.output('dictlist')
        for r in result:
            assert 2004 <= r['year'] <= 2006

    # --- explodingColumns / aggregateRows ---

    def test_exploding_columns(self):
        q = self.db.query('video.cast',
                          columns='$id,$role,@movie_id.title,@person_id.name',
                          order_by='$id')
        sel = q.selection()
        assert len(sel) > 0

    # --- count with distinct ---

    def test_count_distinct(self):
        q = self.db.query('video.movie', columns='$nationality',
                          distinct=True)
        n = q.count()
        assert n > 0

    # --- count with group_by ---

    def test_count_group_by(self):
        q = self.db.query('video.movie',
                          columns='$nationality,count($id) AS cnt',
                          group_by='$nationality')
        n = q.count()
        assert n > 0

    # --- having ---

    def test_having(self):
        q = self.db.query('video.movie',
                          columns='$nationality,count($id) AS cnt',
                          group_by='$nationality',
                          having='count($id) > 1')
        sel = q.selection()
        assert len(sel) > 0

    # --- for_update ---

    def test_compiled_for_update(self):
        q = self.db.query('video.movie', columns='$title',
                          for_update=True)
        compiled = q.compiled
        assert compiled.for_update is True

    # --- multiple relations ---

    def test_multiple_relation_depth(self):
        q = self.db.query('video.cast',
                          columns='$id,$role,@person_id.name,@movie_id.title,@movie_id.year')
        sel = q.selection()
        assert len(sel) > 0
        result = sel.output('dictlist')
        assert '_movie_id_year' in result[0]

    # --- query with AS alias ---

    def test_columns_with_as_alias(self):
        q = self.db.query('video.movie',
                          columns='$title AS film_title,$year AS anno')
        sel = q.selection()
        result = sel.output('dictlist')
        assert 'film_title' in result[0]
        assert 'anno' in result[0]

    # --- SqlCompiledQuery methods ---

    def test_compiled_get_sqltext(self):
        q = self.db.query('video.movie', columns='$title,$year',
                          where='$year > :y', sqlparams={'y': 2000},
                          order_by='$year')
        compiled = q.compiled
        sql = compiled.get_sqltext(self.db)
        assert 'WHERE' in sql.upper()
        assert 'ORDER BY' in sql.upper()

    def test_compiled_get_sqltext_with_group(self):
        q = self.db.query('video.movie',
                          columns='$nationality,count($id) AS cnt',
                          group_by='$nationality',
                          having='count($id) > 0')
        compiled = q.compiled
        sql = compiled.get_sqltext(self.db)
        assert 'GROUP BY' in sql.upper()
        assert 'HAVING' in sql.upper()

    def test_compiled_get_sqltext_with_limit(self):
        q = self.db.query('video.movie', columns='$title',
                          limit=5, offset=2)
        compiled = q.compiled
        sql = compiled.get_sqltext(self.db)
        assert 'LIMIT' in sql.upper()


class TestQuerySurface_sqlite(BaseQuerySurface):
    @classmethod
    def init(cls):
        cls.name = 'sqlite'
        cls.dbname = cls.CONFIG['db.sqlite?filename']
        cls.db = GnrSqlDb(dbname=cls.dbname)


class TestQuerySurface_postgres(BaseQuerySurface):
    @classmethod
    def init(cls):
        cls.name = 'postgres'
        cls.dbname = 'test_query_surface'
        cls.db = GnrSqlDb(implementation='postgres',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password"))
