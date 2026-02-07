#!/usr/bin/env python3
# encoding: utf-8
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrbag : an advanced data storage system
# Copyright (c) : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
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
this test module focus on SqlQuery's methods
"""

import datetime
import logging

gnrlogger = logging.getLogger('gnr')
hdlr = logging.FileHandler('logs.log')
gnrlogger.addHandler(hdlr)

from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.gnrsqldata import SqlQuery, SqlSelection, SqlCompiledQuery
from gnr.sql import gnrsqldata as gsd

from .common import BaseGnrSqlTest, configurePackage

class BaseSql(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.init()
        # create database (actually create the DB file or structure)

        cls.db.createDb(cls.dbname)
        # read the structure of the db from xml file: this is the recipe only
        # cls.db.loadModel(cls.SAMPLE_XMLSTRUCT)
        configurePackage(cls.db.packageSrc('video'))

        # build the python db structure from the recipe
        cls.db.startup()
        cls.db.checkDb(applyChanges=True)
        cls.db.importXmlData(cls.SAMPLE_XMLDATA)
        cls.db.commit()

    def test_selection(self):
        query = self.db.query('video.movie', columns='title',
                              where="$id=:id", sqlparams={'id': 0})
        result = query.selection()
        assert isinstance(result, SqlSelection)

    def test_sqlrecordbag(self):
        rb = gsd.SqlRecordBag(self.db, "video.movie")
        assert rb.isNew == True
        rb.save(title="Babbala")
        rb = gsd.SqlRecordBag(None, "video.movie")
        rb.db = self.db
        assert rb.db is not None
        rb.isNew = False
        rb.db = self.db
        rb.save(title="Babbala 2", id=2000)
        assert self.db.query('video.movie').count() == 12
        
    def test_query(self):
        result = self.db.query('video.movie')
        assert isinstance(result, SqlQuery)

    def test_query_count(self):
        assert self.db.query('video.movie').count() == 12
        assert self.db.query('video.movie', where='$year=:y', sqlparams={'y': 2005}).count() == 2


    def test_query_fetch(self):
        fetch = self.db.query('video.movie',
                              columns='*',
                              where='$title=:title',
                              title='Scoop').fetch()
        assert fetch[0][0] == fetch[0]['id'] == 1

    def test_query_cursor(self):
        query = self.db.query('video.movie',
                              columns='*',
                              where='$title=:title',
                              sqlparams={'title': 'Scoop'})
        cursor = query.cursor()
        result = cursor.fetchall()
        assert result[0][0] == result[0]['id'] == 1

    def xtest_query_servercursor(self):
        # fix the adapter
        servercursor = self.db.query('video.movie',
                                     columns='*',
                                     where='$title=:title',
                                     title='Scoop').servercursor()
        result = servercursor.fetchall()
        assert result[0][0] == result[0]['id'] == 1

    def test_where_statement(self):
        query = self.db.query('video.movie',
                              columns='title',
                              where="$id=:id",
                              sqlparams={'id': 0})

        result = query.selection().output('list')
        assert result[0][0] == "Match point"

    def test_in_statement(self):
        query = self.db.query('video.movie',
                              where='$year IN :years',
                              sqlparams={'years': (2005, 2006)})
        result = query.count()
        assert result == 4

    def test_not_in_statement(self):
        query = self.db.query('video.movie',
                              where='$year NOT IN :years',
                              sqlparams={'years': (1960, 1975)})
        result = query.count()
        assert result == 9

    def test_sqlparams_date(self):
        query = self.db.query('video.dvd',
                              columns='$purchasedate',
                              where='$purchasedate BETWEEN :d1 AND :d2',
                              sqlparams={'d1': datetime.date(2005, 4, 1), 'd2': datetime.date(2005, 4, 30)})
        result = query.selection().output('list')
        assert result[0][0] == datetime.date(2005, 4, 7)

    def test_between_syntax(self):
        # test blank handling
        query = self.db.query('video.location',
                              order_by="$rating",
                              columns='$id',
                              where='#BETWEEN(  $rating  ,:lower, :upper     )',
                              sqlparams={'lower': -1, 'upper': 0})
        result = query.selection().output('list')
        assert result[0][0] == 2
        assert len(result) == 2

        # test between using int
        lower = -6
        upper = 5
        params_cases = [
            {
                "params": {"upper": None, "lower": None},
                "expected": -8,
                "n_records": 11
            },
            {
                "params": {"upper": upper, "lower": None},
                "expected": -8,
                "n_records": 9
            },
            {
                "params": {"upper": None, "lower": lower},
                "expected": -6,
                "n_records": 10
            },
            {
                "params": {"upper": upper, "lower": lower},
                "expected": -6,
                "n_records": 8
            }
        ]
        for params in params_cases:
            query = self.db.query('video.location',
                                  order_by="$rating",
                                  columns='$rating',
                                  where='#BETWEEN($rating, :lower, :upper)',
                                  sqlparams=params.get("params"))
            result = query.selection().output('list')
            print('PARAMS', params.get("params"))
            print('RESULT', result)
            assert result[0][0] == params.get("expected")
            assert len(result) == params.get("n_records")

        # test between using dates
        lower = datetime.date(2005,4,1)
        upper = datetime.date(2005,4,30)
        params_cases = [
            {
                "params": {"upper": None, "lower": None},
                "expected": datetime.date(2004,3,5),
                "n_records": 17
            },
            {
                "params": {"upper": upper, "lower": None},
                "expected": datetime.date(2004,3,5),
                "n_records": 3
            },
            {
                "params": {"upper": None, "lower": lower},
                "expected": datetime.date(2005,4,7),
                "n_records": 15
            },
            {
                "params": {"upper": upper, "lower": lower},
                "expected": datetime.date(2005,4,7),
                "n_records": 1
            },
            {
                "params": {"upper": datetime.date(2005,5,8), "lower": lower},
                "expected": datetime.date(2005,4,7),
                "n_records": 2
            }
        ]
        for params in params_cases:
            query = self.db.query('video.dvd',
                                  order_by="$purchasedate",
                                  columns='$purchasedate',
                                  where='#BETWEEN($purchasedate, :lower, :upper)',
                                  sqlparams=params.get("params"))
            result = query.selection().output('list')
            assert result[0][0] == params.get("expected")
            assert len(result) == params.get("n_records")


    def test_joinSimple(self):
        tbl = self.db.table('video.dvd')
        #raise str(tbl.fields['@movie_id'].keys())
        result = tbl.query(columns='$title',
                           relationDict={'title': '@movie_id.title'},
                           where="$code = :code", code=0).fetch()
        assert result[0]['title'] == "Match point"

    def test_joinDistinct(self):
        result = self.db.query('video.dvd', columns='$year',
                               relationDict={'year': '@movie_id.year'},
                               distinct=True, order_by='$year').fetch()
        assert [r['year'] for r in result] == [1960, 1975, 1983, 1987, 1999, 2004, 2005, 2006]

    def test_joinGroupBy(self):
        result = self.db.query('video.dvd', columns='$nationality, count(*)',
                               relationDict={'nationality': '@movie_id.nationality'},
                               group_by='$nationality', order_by='$nationality').fetch()
        assert [(r[0], r[1]) for r in result] == [('UK', 6), ('USA', 6), ('USA,UK', 5)]

    def test_query_subtables(self):
        tbl = self.db.table("video.cast")
        assert tbl.subtable('first_movie') is not None
        assert tbl.subtable('accalla') is None
        r = self.db.query("video.cast", columns='movie_id').fetch()
        total_records = len(r)
        r1 = self.db.query("video.cast", columns='movie_id', subtable="first_movie").fetch()
        assert len(r1) == 3
        r2 = self.db.query("video.cast", columns='movie_id', subtable="!first_movie").fetch()
        assert len(r2) == (total_records-len(r1))
        r3 = self.db.query("video.cast", columns='movie_id', subtable="first_movie|second_movie").fetch()
        assert len(r3) < total_records
        
    def test_query_limit(self):
        result = self.db.query('video.cast', columns='person_id',
                               where="@person_id.id=:id",
                               sqlparams={'id': 1}, limit=1).fetch()
        assert len(result) == 1

    def test_query_offset(self):
        result = self.db.query('video.cast', columns='@person_id.name',
                               where="$role=:role", role="director",
                               limit=1, order_by='@person_id.year',
                               offset=1).fetch()
        assert result[0][0] == 'Stanley Kubrick'

    def _broken_test_query_groupBy(self):
        #also test the resolver use
        query = self.db.query('video.cast',
                              columns='@person_id.name, count($role) as nm',
                              group_by='@person_id.name',
                              order_by='@person_id.name')
        myresolver = query.resolver('list')
        assert myresolver[0][0] == 'Al Pacino'
        result = myresolver(having='count($role) > 1')
        assert result[0][0] == 'Brian De Palma'

    def test_query_namedCursor(self):
        cursor = self.db.query('video.movie', columns='$title',
                               where="$id=:id", sqlparams={'id': 0}).cursor()
        result = cursor.fetchall()
        assert result[0]['title'] == "Match point"

    def test_join_relationDict(self):
        #raise str(tbl.fields['@movie_id'].keys())
        result = self.db.query('video.dvd', columns='$title',
                               relationDict={'title': '@movie_id.title'},
                               where="$code = :code", code=0).fetch()
        assert result[0]['title'] == "Match point"

    def test_mangler_sqltext(self):
        query = self.db.query('video.movie',
                              columns='$title',
                              where='$year = :year AND $nationality = :nat',
                              year=2005, nat='USA',
                              mangler='q0')
        sqltext, sqlparams = query.test()
        assert ':q0_year' in sqltext
        assert ':q0_nat' in sqltext
        assert ':year' not in sqltext
        assert ':nat' not in sqltext

    def test_mangler_sqlparams(self):
        query = self.db.query('video.movie',
                              columns='$title',
                              where='$year = :year',
                              year=2005,
                              mangler='q0')
        sqltext, sqlparams = query.test()
        assert 'q0_year' in sqlparams
        assert sqlparams['q0_year'] == 2005
        assert 'year' in sqlparams

    def test_mangler_none_unchanged(self):
        query_no_mangler = self.db.query('video.movie',
                              columns='$title',
                              where='$year = :year',
                              year=2005)
        sqltext, sqlparams = query_no_mangler.test()
        assert ':year' in sqltext
        assert 'year' in sqlparams

    def test_mangler_fetch(self):
        query = self.db.query('video.movie',
                              columns='$title',
                              where='$year = :year',
                              year=2005,
                              mangler='q0')
        result = query.fetch()
        assert len(result) == 2

    def test_mangler_count(self):
        query = self.db.query('video.movie',
                              columns='$title',
                              where='$year = :year',
                              year=2005,
                              mangler='q0')
        assert query.count() == 2

    def test_compound_union_sqltext(self):
        self.db.currentEnv['_mangler_counters'] = {}
        q1 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        q2 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2006)
        compound = q1 + q2
        sqltext, sqlparams = compound.test()
        assert 'UNION' in sqltext
        assert ':cq0_year' in sqltext
        assert ':cq1_year' in sqltext
        assert sqlparams['cq0_year'] == 2005
        assert sqlparams['cq1_year'] == 2006

    def test_compound_union_fetch(self):
        q1 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        q2 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2006)
        result = (q1 + q2).fetch()
        titles = sorted([r['title'] for r in result])
        assert titles == ['Match point', 'Munich', 'Scoop', 'The Departed']

    def test_compound_union_all(self):
        q1 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        q2 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        result = (q1 | q2).fetch()
        titles = sorted([r['title'] for r in result])
        assert titles == ['Match point', 'Match point', 'Munich', 'Munich']

    def test_compound_intersect(self):
        q1 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        q2 = self.db.query('video.movie', columns='$title', where='$nationality = :nat', nat='USA')
        result = (q1 & q2).fetch()
        assert len(result) == 1
        assert result[0]['title'] == 'Munich'

    def test_compound_except(self):
        q1 = self.db.query('video.movie', columns='$title,$year', where='$year = :year', year=2005)
        q2 = self.db.query('video.movie', columns='$title,$year', where='$nationality = :nat', nat='USA')
        result = (q1 - q2).fetch()
        assert len(result) == 1
        assert result[0]['title'] == 'Match point'

    def test_compound_chain(self):
        q1 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        q2 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2006)
        q3 = self.db.query('video.movie', columns='$title', where='$year = :year', year=1999)
        compound = q1 + q2 + q3
        titles = sorted([r['title'] for r in compound.fetch()])
        assert titles == ['Eyes wide shut', 'Match point', 'Munich', 'Scoop', 'The Departed']

    def test_compound_count(self):
        q1 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        q2 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2006)
        assert (q1 + q2).count() == 4

    def test_compound_parentheses(self):
        q1 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        q2 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2006)
        q3 = self.db.query('video.movie', columns='$title', where='$year = :year', year=1999)
        q4 = self.db.query('video.movie', columns='$title', where='$year = :year', year=2005)
        compound = (q1 + q2) & (q3 + q4)
        sqltext, sqlparams = compound.test()
        assert 'INTERSECT' in sqltext
        assert sqltext.count('UNION') == 2
        result = compound.fetch()
        titles = sorted([r['title'] for r in result])
        assert titles == ['Match point', 'Munich']

    def test_formulaColumn_pure(self):
        result = self.db.query('video.movie',
                              columns='$title,$title_upper',
                              where='$id = :id', id=0).fetch()
        assert result[0]['title_upper'] == 'MATCH POINT'

    def test_formulaColumn_pure_relation(self):
        result = self.db.query('video.cast',
                              columns='$movie_year,$role',
                              where='$id = :id', id=0).fetch()
        assert result[0]['movie_year'] == 2005

    def test_aliasColumn(self):
        result = self.db.query('video.cast',
                              columns='$movie_title,$role',
                              where='$id = :id', id=0).fetch()
        assert result[0]['movie_title'] == 'Match point'

    def test_formulaColumn_with_subquery(self):
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count',
                              where='$id = :id', id=0).fetch()
        assert result[0]['dvd_count'] == 3

    def test_formulaColumn_subquery_no_match(self):
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count',
                              where='$id = :id', id=3).fetch()
        assert result[0]['dvd_count'] == 0

    def test_formulaColumn_mixed(self):
        result = self.db.query('video.movie',
                              columns='$title,$title_upper,$dvd_count',
                              where='$id = :id', id=1).fetch()
        assert result[0]['title_upper'] == 'SCOOP'
        assert result[0]['dvd_count'] == 2

    def test_formulaColumn_multi_col(self):
        result = self.db.query('video.movie',
                              columns='$title_year',
                              where='$id = :id', id=0).fetch()
        assert result[0]['title_year'] == 'Match point (2005)'

    def test_formulaColumn_col_and_rel(self):
        result = self.db.query('video.cast',
                              columns='$role_in_movie',
                              where='$id = :id', id=0).fetch()
        assert result[0]['role_in_movie'] == 'director in Match point'

    def test_aliasColumn_in_where(self):
        result = self.db.query('video.cast',
                              columns='$movie_title,$role',
                              where='$movie_title = :title',
                              title='Match point').fetch()
        assert len(result) == 3
        assert all(r['movie_title'] == 'Match point' for r in result)

    def test_formulaColumn_with_var(self):
        result = self.db.query('video.movie',
                              columns='$title_with_label',
                              where='$id = :id', id=0).fetch()
        assert result[0]['title_with_label'] == 'Match point [DVD]'

    def test_formulaColumn_with_var_via_relation(self):
        result = self.db.query('video.cast',
                              columns='@movie_id.title_with_label,$role',
                              where='$id = :id', id=0).fetch()
        assert result[0]['_movie_id_title_with_label'] == 'Match point [DVD]'

    def test_formulaColumn_with_var_multiple_rows(self):
        result = self.db.query('video.cast',
                              columns='@movie_id.title_with_label,$role',
                              where='$movie_id = :mid', mid=0).fetch()
        assert len(result) == 3
        assert all(r['_movie_id_title_with_label'] == 'Match point [DVD]' for r in result)

    def test_formulaColumn_with_var_and_other_formulas(self):
        result = self.db.query('video.movie',
                              columns='$title_with_label,$title_upper,$dvd_count',
                              where='$id = :id', id=0).fetch()
        assert result[0]['title_with_label'] == 'Match point [DVD]'
        assert result[0]['title_upper'] == 'MATCH POINT'
        assert result[0]['dvd_count'] == 3

    def test_formulaColumn_subquery_with_params(self):
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count_available',
                              where='$id = :id', id=0).fetch()
        assert result[0]['dvd_count_available'] == 3  # movie 0 has 3 dvds with available='yes'

    def test_formulaColumn_subquery_params_and_count(self):
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count,$dvd_count_available',
                              where='$id = :id', id=0).fetch()
        assert result[0]['dvd_count'] == 3
        assert result[0]['dvd_count_available'] == 3

    def test_formulaColumn_subquery_order_by(self):
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count',
                              order_by='$dvd_count DESC',
                              limit=3).fetch()
        counts = [r['dvd_count'] for r in result]
        assert counts == sorted(counts, reverse=True)
        assert counts[0] == 3

    # --- SqlCompiledQuery __eq__ / __hash__ / identity_hash tests ---

    def test_compiled_eq_same_identity_hash(self):
        a = SqlCompiledQuery('video_movie')
        b = SqlCompiledQuery('video_movie')
        a.where = 'x = :p'
        b.where = 'x = :p'
        a.mangled_params = {'p': 'val'}
        b.mangled_params = {'p': 'val'}
        assert a == b

    def test_compiled_eq_different_identity_hash(self):
        a = SqlCompiledQuery('video_movie')
        b = SqlCompiledQuery('video_movie')
        a.where = 'x = :p'
        b.where = 'x = :p'
        a.mangled_params = {'p': 'val1'}
        b.mangled_params = {'p': 'val2'}
        assert a != b

    def test_compiled_eq_different_table(self):
        a = SqlCompiledQuery('video_movie')
        b = SqlCompiledQuery('video_dvd')
        a.where = 'x = :p'
        b.where = 'x = :p'
        a.mangled_params = {'p': 'val'}
        b.mangled_params = {'p': 'val'}
        assert a != b

    def test_compiled_eq_no_mangled_params(self):
        a = SqlCompiledQuery('video_movie')
        b = SqlCompiledQuery('video_movie')
        # entrambi senza mangled_params → identity_hash è None
        assert a != b

    def test_compiled_eq_one_without_mangled(self):
        a = SqlCompiledQuery('video_movie')
        b = SqlCompiledQuery('video_movie')
        a.where = 'x = :p'
        a.mangled_params = {'p': 'val'}
        # b senza mangled_params
        assert a != b

    def test_compiled_eq_not_implemented(self):
        a = SqlCompiledQuery('video_movie')
        a.where = 'x = :p'
        a.mangled_params = {'p': 'val'}
        assert a.__eq__("not a compiled") is NotImplemented

    def test_compiled_hash_with_identity(self):
        a = SqlCompiledQuery('video_movie')
        a.where = 'x = :p'
        a.mangled_params = {'p': 'val'}
        assert hash(a) == hash(('video_movie', 'x = val'))

    def test_compiled_hash_without_identity(self):
        a = SqlCompiledQuery('video_movie')
        assert hash(a) == id(a)

    def test_compiled_in_set(self):
        a = SqlCompiledQuery('video_movie')
        b = SqlCompiledQuery('video_movie')
        a.where = 'x = :p'
        b.where = 'x = :p'
        a.mangled_params = {'p': 'val'}
        b.mangled_params = {'p': 'val'}
        s = {a, b}
        assert len(s) == 1

    def test_compiled_as_dict_key(self):
        a = SqlCompiledQuery('video_movie')
        b = SqlCompiledQuery('video_movie')
        a.where = 'x = :p'
        b.where = 'x = :p'
        a.mangled_params = {'p': 'val'}
        b.mangled_params = {'p': 'val'}
        d = {a: 'value_a'}
        assert d[b] == 'value_a'

    def test_compiled_different_in_set(self):
        a = SqlCompiledQuery('video_movie')
        b = SqlCompiledQuery('video_movie')
        a.where = 'x = :p1'
        b.where = 'x = :p2'
        a.mangled_params = {'p1': 'val1'}
        b.mangled_params = {'p2': 'val2'}
        s = {a, b}
        assert len(s) == 2

    # --- compileQuery produce SqlCompiledQuery ---

    def test_compileQuery_returns_compiled_object(self):
        q = self.db.query('video.movie', columns='$title', where='$id = :id', id=0)
        compiled = q.compileQuery()
        assert isinstance(compiled, SqlCompiledQuery)

    def test_compiled_has_maintable(self):
        q = self.db.query('video.movie', columns='$title', where='$id = :id', id=0)
        compiled = q.compileQuery()
        assert 'movie' in compiled.maintable

    def test_compiled_tpl_none_by_default(self):
        q = self.db.query('video.movie', columns='$title', where='$id = :id', id=0)
        compiled = q.compileQuery()
        assert compiled.tpl is None

    def test_compiled_identity_hash_none_for_main_query(self):
        """Le query principali non hanno identity_hash (è per le subquery)"""
        q = self.db.query('video.movie', columns='$title', where='$id = :id', id=0)
        compiled = q.compileQuery()
        assert compiled.identity_hash is None

    # --- get_sqltext template handling ---

    def test_get_sqltext_without_tpl(self):
        q = self.db.query('video.movie', columns='$title', where='$id = :id', id=0)
        compiled = q.compileQuery()
        sql = compiled.get_sqltext(self.db)
        assert '%s' not in sql
        assert 'SELECT' in sql.upper()

    def test_get_sqltext_with_tpl(self):
        q = self.db.query('video.movie', columns='$title', where='$id = :id', id=0)
        compiled = q.compileQuery()
        compiled.tpl = ' ( %s ) '
        sql = compiled.get_sqltext(self.db)
        assert sql.strip().startswith('(')
        assert sql.strip().endswith(')')

    def test_get_sqltext_cast_tpl(self):
        q = self.db.query('video.movie', columns='$title', where='$id = :id', id=0)
        compiled = q.compileQuery()
        compiled.tpl = ' CAST( ( %s ) AS integer) '
        sql = compiled.get_sqltext(self.db)
        assert 'CAST' in sql
        assert 'integer' in sql

    def test_get_sqltext_exists_tpl(self):
        q = self.db.query('video.dvd', columns='$code', where='$movie_id = :mid', mid=0)
        compiled = q.compileQuery()
        compiled.tpl = ' EXISTS( %s ) '
        sql = compiled.get_sqltext(self.db)
        assert 'EXISTS' in sql

    # --- Subquery tramite formulaColumn: risultati corretti ---

    def test_subquery_dvd_count_all_movies(self):
        """Verifica dvd_count sui film noti — la subquery funziona per ogni riga"""
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count',
                              where='$id <= :maxid', maxid=10,
                              order_by='$id').fetch()
        expected = {
            'Match point': 3, 'Scoop': 2, 'Munich': 2,
            'Saving private Ryan': 0, 'Eyes wide shut': 2,
            'Barry Lindon': 2, 'Scarface': 1, 'The untouchables': 1,
            'Psycho': 2, 'The Aviator': 1, 'The Departed': 1
        }
        for r in result:
            assert r['dvd_count'] == expected[r['title']]

    def test_subquery_with_params_all_movies(self):
        """Verifica dvd_count_available — subquery con parametri extra (:avail)"""
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count_available',
                              order_by='$id').fetch()
        for r in result:
            assert isinstance(r['dvd_count_available'], int)

    def test_subquery_params_preserved_in_sqlparams(self):
        """I parametri della subquery devono essere nei sqlparams della query principale"""
        q = self.db.query('video.movie',
                         columns='$title,$dvd_count_available',
                         where='$id = :id', id=0)
        sqltext, sqlparams = q.test()
        has_avail = any('avail' in k for k in sqlparams)
        assert has_avail

    def test_subquery_sqltext_contains_subselect(self):
        """L'SQL generato deve contenere la subquery wrappata tra parentesi"""
        q = self.db.query('video.movie',
                         columns='$title,$dvd_count',
                         where='$id = :id', id=0)
        sqltext, sqlparams = q.test()
        upper = sqltext.upper()
        assert upper.count('SELECT') >= 2  # main query + subquery

    def test_two_subqueries_in_same_query(self):
        """Due formulaColumn con subquery nella stessa query"""
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count,$dvd_count_available',
                              where='$id = :id', id=0).fetch()
        assert result[0]['dvd_count'] == 3
        assert result[0]['dvd_count_available'] == 3

    def test_subquery_zero_when_no_match(self):
        """COUNT deve dare 0 quando non ci sono righe corrispondenti"""
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count',
                              where='$id = :id', id=3).fetch()
        assert result[0]['dvd_count'] == 0
        assert result[0]['title'] == 'Saving private Ryan'

    def test_subquery_available_zero_when_no_match(self):
        """dvd_count_available deve dare 0 quando nessun dvd è available"""
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count_available',
                              where='$id = :id', id=1).fetch()
        # movie_id=1 (Scoop) ha 2 dvd ma entrambi available='no'
        assert result[0]['dvd_count_available'] == 0

    def test_subquery_mixed_with_formula_and_alias(self):
        """Combinazione di formulaColumn pura, aliasColumn e subquery nella stessa query"""
        result = self.db.query('video.movie',
                              columns='$title,$title_upper,$dvd_count,$title_year',
                              where='$id = :id', id=0).fetch()
        assert result[0]['title_upper'] == 'MATCH POINT'
        assert result[0]['dvd_count'] == 3
        assert result[0]['title_year'] == 'Match point (2005)'

    def test_subquery_with_order_by_subquery_column(self):
        """ORDER BY su colonna subquery"""
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count',
                              order_by='$dvd_count DESC',
                              limit=3).fetch()
        counts = [r['dvd_count'] for r in result]
        assert counts == sorted(counts, reverse=True)

    def test_subquery_with_where_on_main(self):
        """Subquery combinata con WHERE sulla tabella principale"""
        result = self.db.query('video.movie',
                              columns='$title,$dvd_count',
                              where='$genre = :genre',
                              genre='DRAMA').fetch()
        assert len(result) == 4
        for r in result:
            assert isinstance(r['dvd_count'], int)

    def test_compiled_sqltext_stable(self):
        """Due compilazioni identiche producono lo stesso SQL"""
        q1 = self.db.query('video.movie', columns='$title,$dvd_count',
                          where='$id = :id', id=0)
        q2 = self.db.query('video.movie', columns='$title,$dvd_count',
                          where='$id = :id', id=0)
        sql1, _ = q1.test()
        sql2, _ = q2.test()
        # La struttura dell'SQL deve essere uguale (i mangler possono variare)
        assert sql1.upper().count('SELECT') == sql2.upper().count('SELECT')

    def teardown_class(cls):
        cls.db.closeConnection()
        cls.db.dropDb(cls.dbname)


class TestGnrSqlDb_sqlite(BaseSql):
    def init(cls):
        cls.name = 'sqlite'
        cls.dbname = cls.CONFIG['db.sqlite?filename']
        cls.db = GnrSqlDb(dbname=cls.dbname)
        
    init = classmethod(init)

class TestGnrSqlDb_postgres(BaseSql):
    def init(cls):
        cls.name = 'postgres'
        cls.dbname = 'test2'
        cls.db = GnrSqlDb(implementation='postgres',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password")
                          )
        
    init = classmethod(init)

# FIXME: reintroduce Mysql tests ASAP
# class TestGnrSqlDb_mysql(BaseSql):
#     def init(cls):
#         cls.name = 'mysql'
#         cls.dbname = 'genrotest2'
#         cls.db = GnrSqlDb(implementation='mysql',
#                           host=cls.mysql_conf.get("host"),
#                           dbname=cls.dbname,
#                           user=cls.mysql_conf.get("user"),
#                           password=cls.mysql_conf.get("password")
#                           )

#     init = classmethod(init)


class TestGnrSqlDb_postgres3(BaseSql):
    def init(cls):
        cls.name = 'postgres3'
        cls.dbname = 'test2'
        cls.db = GnrSqlDb(implementation='postgres3',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password")
                          )
        
    init = classmethod(init)

