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
from gnr.sql.gnrsqldata import SqlQuery, SqlSelection
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

