#!/usr/bin/env python3
# encoding: utf-8
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""
Baseline tests for SqlSelection behaviour.

These tests document the current (eager) behaviour of SqlSelection so that
the lazy-selection refactoring (issue #488) can be validated against them.
Every test here MUST pass both before and after the lazy change.
"""

import os
import datetime

from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.gnrsqldata import SqlQuery, SqlSelection
from gnr.core.gnrbag import Bag
from gnr.core import gnrstring

from .common import BaseGnrSqlTest, configureDb


# ---------------------------------------------------------------------------
#  Base class: sets up a real DB with video sample data
# ---------------------------------------------------------------------------

class BaseSelectionTest(BaseGnrSqlTest):
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

    # -- helpers ------------------------------------------------------------

    def _movie_query(self, **kwargs):
        return self.db.query('video.movie', columns='$id,$title,$year,$genre',
                             order_by='$id', **kwargs)

    def _movie_selection(self, **kwargs):
        return self._movie_query(**kwargs).selection()

    def _cast_query(self, **kwargs):
        return self.db.query('video.cast',
                             columns='$id,@person_id.name AS person,'
                                     '@movie_id.title AS movie,$role',
                             **kwargs)

    def _cast_selection(self, **kwargs):
        return self._cast_query(**kwargs).selection()

    # -----------------------------------------------------------------------
    #  1. Basic creation
    # -----------------------------------------------------------------------

    def test_selection_is_instance(self):
        sel = self._movie_selection()
        assert isinstance(sel, SqlSelection)

    def test_selection_has_data(self):
        sel = self._movie_selection()
        assert sel.data is not None
        assert len(sel.data) > 0

    def test_selection_has_index(self):
        sel = self._movie_selection()
        assert sel._index is not None
        assert 'id' in sel._index
        assert 'title' in sel._index

    def test_selection_has_colAttrs(self):
        sel = self._movie_selection()
        assert sel.colAttrs is not None
        assert 'title' in sel.colAttrs

    def test_selection_has_querypars(self):
        sel = self._movie_selection()
        assert sel.querypars is not None
        assert isinstance(sel.querypars, dict)

    def test_selection_has_dbtable(self):
        sel = self._movie_selection()
        assert sel.dbtable is not None
        assert sel.tablename == 'video.movie'

    # -----------------------------------------------------------------------
    #  2. len()
    # -----------------------------------------------------------------------

    def test_len(self):
        sel = self._movie_selection()
        n = len(sel)
        assert n == 11  # 11 movies in sample data

    def test_len_with_where(self):
        sel = self._movie_selection(where='$year=:y', sqlparams={'y': 2005})
        assert len(sel) == 2

    # -----------------------------------------------------------------------
    #  3. Iteration
    # -----------------------------------------------------------------------

    def test_iter(self):
        sel = self._movie_selection()
        titles = [row['title'] for row in sel]
        assert 'Match point' in titles
        assert 'Scoop' in titles
        assert len(titles) == 11

    # -----------------------------------------------------------------------
    #  4. data property
    # -----------------------------------------------------------------------

    def test_data_is_list(self):
        sel = self._movie_selection()
        assert isinstance(sel.data, list)

    def test_data_rows_are_accessible_by_name(self):
        sel = self._movie_selection()
        row = sel.data[0]
        assert 'id' in row.keys() if hasattr(row, 'keys') else row['id'] is not None

    # -----------------------------------------------------------------------
    #  5. allColumns
    # -----------------------------------------------------------------------

    def test_allColumns(self):
        sel = self._movie_selection()
        cols = sel.allColumns
        assert isinstance(cols, list)
        assert 'id' in cols
        assert 'title' in cols
        assert 'year' in cols
        assert 'genre' in cols
        assert 'pkey' in cols

    # -----------------------------------------------------------------------
    #  6. sort
    # -----------------------------------------------------------------------

    def test_sort_single_column(self):
        sel = self._movie_selection()
        sel.sort('title')
        titles = [row['title'] for row in sel]
        assert titles == sorted(titles)

    def test_sort_descending(self):
        sel = self._movie_selection()
        sel.sort('year:d')
        years = [row['year'] for row in sel]
        assert years == sorted(years, reverse=True)

    def test_sort_multiple_columns(self):
        sel = self._cast_selection()
        sel.sort('movie', 'role:d', 'person')
        first = sel.data[0]
        assert first['movie'] == 'Barry Lindon'
        assert first['role'] == 'director'

    # -----------------------------------------------------------------------
    #  7. setKey
    # -----------------------------------------------------------------------

    def test_setKey(self):
        sel = self._movie_selection()
        sel.setKey('pkey')
        assert sel.key == 'pkey'
        for i, row in enumerate(sel.data):
            assert row['pkey'] == i

    def test_key_auto_pkey(self):
        sel = self._movie_selection()
        assert sel.key == 'pkey'

    # -----------------------------------------------------------------------
    #  8. keyDict
    # -----------------------------------------------------------------------

    def test_keyDict(self):
        sel = self._movie_selection()
        kd = sel.keyDict
        assert isinstance(kd, dict)
        assert len(kd) == len(sel)

    def test_getByKey(self):
        sel = self._movie_selection()
        sel.sort('id')
        row = sel.getByKey(0)
        assert row['title'] == 'Match point'

    # -----------------------------------------------------------------------
    #  9. filter
    # -----------------------------------------------------------------------

    def test_filter_apply(self):
        sel = self._movie_selection()
        original_len = len(sel)
        sel.filter(lambda r: r['genre'] == 'DRAMA')
        assert len(sel) < original_len
        for row in sel:
            assert row['genre'] == 'DRAMA'

    def test_filter_clear(self):
        sel = self._movie_selection()
        original_len = len(sel)
        sel.filter(lambda r: r['genre'] == 'DRAMA')
        sel.filter()
        assert len(sel) == original_len

    # -----------------------------------------------------------------------
    #  10. output modes
    # -----------------------------------------------------------------------

    def test_output_list(self):
        sel = self._movie_selection()
        result = sel.output('list')
        assert isinstance(result, list)
        assert isinstance(result[0], list)

    def test_output_dictlist(self):
        sel = self._movie_selection()
        result = sel.output('dictlist')
        assert isinstance(result, list)
        assert isinstance(result[0], dict)
        assert 'title' in result[0]

    def test_output_json(self):
        sel = self._movie_selection()
        result = sel.output('json')
        assert isinstance(result, (str, bytes))
        parsed = gnrstring.fromJson(result)
        assert isinstance(parsed, list)
        assert isinstance(parsed[0], dict)

    def test_output_pkeylist(self):
        sel = self._movie_selection()
        result = sel.output('pkeylist')
        assert isinstance(result, list)
        assert len(result) == len(sel)

    def test_output_bag(self):
        sel = self._movie_selection()
        result = sel.output('bag')
        assert isinstance(result, Bag)

    # -----------------------------------------------------------------------
    #  11. freeze / unfreeze (pickle)
    # -----------------------------------------------------------------------

    def test_freeze_unfreeze(self):
        sel = self._movie_selection()
        freeze_dir = os.path.join(os.path.dirname(__file__), 'data')
        freeze_path = os.path.join(freeze_dir, 'test_lazy_sel')
        try:
            sel.freeze(freeze_path)
            restored = self.db.table('video.movie').frozenSelection(freeze_path)
            assert len(restored) == len(sel)
            assert restored.data == sel.data
        finally:
            for suffix in ('', '.pik', '_data.pik', '_filtered.pik',
                           '_pkeys.pik'):
                p = freeze_path + suffix
                if os.path.exists(p):
                    os.remove(p)

    # -----------------------------------------------------------------------
    #  12. pyWhere (callback during fetch)
    # -----------------------------------------------------------------------

    def test_pyWhere(self):
        q = self._movie_query()
        sel = q.selection(pyWhere=lambda r: r['year'] >= 2005)
        assert len(sel) > 0
        for row in sel:
            assert row['year'] >= 2005

    # -----------------------------------------------------------------------
    #  13. query object accessibility
    # -----------------------------------------------------------------------

    def test_query_returns_selection_with_querypars(self):
        q = self._movie_query(where='$year=:y', sqlparams={'y': 2006})
        sel = q.selection()
        assert sel.querypars is not None
        assert 'where' in sel.querypars

    def test_query_sqltext_available(self):
        q = self._movie_query()
        assert q.sqltext is not None
        assert isinstance(q.sqltext, str)
        assert 'SELECT' in q.sqltext.upper()

    # -----------------------------------------------------------------------
    #  14. colAttrs detail
    # -----------------------------------------------------------------------

    def test_colAttrs_dataType(self):
        sel = self._movie_selection()
        assert 'dataType' in sel.colAttrs['year']

    def test_colAttrs_label(self):
        sel = self._movie_selection()
        assert 'label' in sel.colAttrs['title']

    # -----------------------------------------------------------------------
    #  15. selection with sortedBy in constructor
    # -----------------------------------------------------------------------

    def test_sortedBy_in_query(self):
        q = self.db.query('video.movie', columns='$id,$title,$year',
                          order_by='$year')
        sel = q.selection()
        years = [row['year'] for row in sel]
        assert years == sorted(years)

    # -----------------------------------------------------------------------
    #  16. extend
    # -----------------------------------------------------------------------

    def test_extend(self):
        sel1 = self.db.query('video.movie', columns='$id,$title',
                             where='$year=:y', sqlparams={'y': 2005}).selection()
        sel2 = self.db.query('video.movie', columns='$id,$title',
                             where='$year=:y', sqlparams={'y': 2006}).selection()
        len1 = len(sel1)
        len2 = len(sel2)
        sel1.extend(sel2)
        assert len(sel1) == len1 + len2

    # -----------------------------------------------------------------------
    #  17. isChanged flags
    # -----------------------------------------------------------------------

    def test_isChanged_after_creation(self):
        sel = self._movie_selection()
        assert sel.isChangedSelection is True
        assert sel.isChangedData is True

    def test_isChanged_after_sort(self):
        sel = self._movie_selection()
        sel.isChangedSelection = False
        sel.sort('title')
        assert sel.isChangedSelection is True

    # -----------------------------------------------------------------------
    #  18. selection with dates (type preservation)
    # -----------------------------------------------------------------------

    def test_date_type_preserved(self):
        sel = self.db.query('video.dvd',
                            columns='$purchasedate,$code').selection()
        row = sel.data[0]
        assert isinstance(row['purchasedate'], datetime.date)

    # -----------------------------------------------------------------------
    #  19. count via query
    # -----------------------------------------------------------------------

    def test_query_count(self):
        q = self._movie_query()
        n = q.count()
        sel = q.selection()
        assert n == len(sel)

    # -----------------------------------------------------------------------
    #  20. selection from join query
    # -----------------------------------------------------------------------

    def test_join_selection(self):
        sel = self._cast_selection()
        assert len(sel) > 0
        row = sel.data[0]
        assert 'person' in row.keys() if hasattr(row, 'keys') else True
        assert 'movie' in row.keys() if hasattr(row, 'keys') else True

    # -----------------------------------------------------------------------
    #  21. multiple selections from same query
    # -----------------------------------------------------------------------

    def test_multiple_selections_independent(self):
        q = self._movie_query()
        sel1 = q.selection()
        sel2 = q.selection()
        sel1.sort('title')
        titles1 = [r['title'] for r in sel1]
        titles2 = [r['title'] for r in sel2]
        assert titles1 != titles2 or len(sel1) <= 1

    # -----------------------------------------------------------------------
    #  22. empty selection
    # -----------------------------------------------------------------------

    def test_empty_selection(self):
        sel = self._movie_selection(where='$year=:y', sqlparams={'y': 9999})
        assert len(sel) == 0
        assert sel.data == []
        assert list(sel) == []


# ---------------------------------------------------------------------------
#  Concrete test classes per backend
# ---------------------------------------------------------------------------

class TestLazySelection_sqlite(BaseSelectionTest):
    @classmethod
    def init(cls):
        cls.name = 'sqlite'
        cls.dbname = cls.CONFIG['db.sqlite?filename']
        cls.db = GnrSqlDb(dbname=cls.dbname)


class TestLazySelection_postgres(BaseSelectionTest):
    @classmethod
    def init(cls):
        cls.name = 'postgres'
        cls.dbname = 'test_lazy_sel'
        cls.db = GnrSqlDb(implementation='postgres',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password"))


class TestLazySelection_postgres3(BaseSelectionTest):
    @classmethod
    def init(cls):
        cls.name = 'postgres3'
        cls.dbname = 'test_lazy_sel'
        cls.db = GnrSqlDb(implementation='postgres3',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password"))
