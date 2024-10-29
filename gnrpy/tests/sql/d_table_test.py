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
this test module focus on SqlTable's methods
"""
import os
import datetime
import tempfile

import pytest
import logging

gnrlogger = logging.getLogger('gnr')
hdlr = logging.FileHandler('logs.log')
gnrlogger.addHandler(hdlr)

from gnr.sql.gnrsql import GnrSqlDb

from gnr.core.gnrbag import Bag


from .common import BaseGnrSqlTest, configurePackage

class BaseSql(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.init()
        # create database (actually create the DB file or structure)
        cls.db.createDb(cls.dbname)
        
        # read the structure of the db from xml file: this is the recipe only
        cls.db.loadModel(cls.SAMPLE_XMLSTRUCT)

        # build the python db structure from the recipe
        cls.db.startup()
        cls.db.checkDb(applyChanges=True)
        cls.db.importXmlData(cls.SAMPLE_XMLDATA)
        cls.db.commit()

    #------------setup test-----------------------------------------
    def test_modelSrc(self):
        assert self.db.model.src['packages.video.tables.people?pkey'] == 'id'

    def test_modelObj(self):
        assert list(self.db.packages.keys()) == ['video']
        tbl = self.db.table('video.dvd')

    def test_noStructDiff(self):
        check = self.db.checkDb()
        assert not check

    def test_execute1(self):
        result = self.db.execute('SELECT 1;').fetchall()
        assert result[0][0] == 1

    def test_execute_env(self):
        self.db.updateEnv(workdate="2020-01-01", storename="babbala")
        r = self.db.execute("SELECT :env_workdate;", storename=False).fetchall()
        self.db.clearCurrentEnv()
        r = self.db.execute("SELECT :env_workdate;", sqlargs=dict(a=b'ciao', b=r"\$hello")).fetchall()

        def fake_debugger(*args, **kwargs):
            pass
        
        self.db.debugger = fake_debugger
        r = self.db.execute("SELECT :env_workdate;",
                            autocommit=False,
                            # FIXME: investigate server side cursors
                            #cursorname="*",
                            dbtable="video.people",
                            sqlargs=dict(a=b'ciao', b=r"\$hello")).fetchall()
        assert self.db.debugger is fake_debugger
        assert len(r) > 0
        self.db.debugger = None
        
        def get_fake_cursor():
            return [self.db.adapter.cursor(self.db.connection) for x in range(2)]
        
        r = self.db.execute("SELECT :env_workdate;",
                            autocommit=True,
                            cursor=get_fake_cursor(),
                            dbtable="video.people",
                            sqlargs=dict(a=b'ciao', b=r"\$hello"))
        assert len(r) is 2
        
    #------------table test-----------------------------------------
    def test_insert(self):
        tbl = self.db.table('video.movie')
        tbl.insert({'id': 11, 'title': 'Forrest Gump'})
        result = tbl.record(columns='*',
                            where="$id = :id", id=11, mode='bag')
        self.db.commit()
        assert result['title'] == 'Forrest Gump'
        tbl.delete(result)
        self.db.commit()

    def test_insertMany(self):
        tbl = self.db.table('video.movie')
        tbl.insertMany([
            {'id': 12, 'title': 'Forrest Gump 2'},
            {'id': 13, 'title': 'Forrest Gump 3'}
            ])
    def test_raw(self):
        tbl = self.db.table('video.movie')
        tbl.raw_insert(
            {'id': 14, 'title': 'Apollo 14'}
            )
        tbl.raw_update(
            {'id': 14},
            {'title': 'Apollo 15'}
            )
    def test_update(self):
        self.db.table('video.movie').update({'id': 10, 'nationality': 'TIBET'})
        self.db.commit()
        result = self.db.query('video.movie', columns='$title, $nationality',
                               where="$id = :id", id=10).fetch()
        assert result[0][1] == 'TIBET'
        self.db.table('video.movie').update({'id': 10, 'nationality': 'USA'})
        self.db.commit()

    def test_insertExisting(self):
        pytest.raises(self.db.connection.IntegrityError,
                       self.db.table('video.movie').insert,
                       {'id': 10, 'title': 'The Departed'})
        self.db.connection.rollback()

    def test_executeAfterRollback(self):
        result = self.db.query('video.movie', columns='title', where="$id=:id", id=0).fetch()
        assert result[0][0] == "Match point"

    def test_insertNoId(self):
        today = datetime.date.today()
        self.db.table('video.dvd').insert({'movie_id': 2, 'purchasedate': today})
        result = self.db.query('video.dvd', columns='@movie_id.title AS title',
                               where="$purchasedate = :today", today=today).fetch()
        self.db.commit()
        assert result[0][0] == 'Munich'

    def test_record(self):
        result = self.db.table('video.dvd').record(1, mode='bag')
        assert result['@movie_id.title'] == 'Scoop'
        assert result['purchasedate'] == datetime.date(2006, 3, 2)

    def test_recordKwargs(self):
        result = self.db.table('video.movie').record(title='Munich', mode='bag')
        assert result['genre'] == 'DRAMA'

    def test_record_modeDict(self):
        result = self.db.table('video.dvd').record(1, mode='dict')
        assert isinstance(result, dict)

    def test_createStructureFromCode(self):
        configurePackage(self.db.packageSrc('video'))
        with tempfile.NamedTemporaryFile(delete=True) as tmpdbfile:
            self.db.saveModel(tmpdbfile.name)
        assert self.db.model.src['packages.video.tables.people?pkey'] == 'id'

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
