#!/usr/bin/env python
# encoding: utf-8
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrbag : an advanced data storage system
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
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

from gnr.sql.gnrsql import GnrSqlDb

from .common import BaseGnrSqlTest, configureDb

class TestDbModelSrc(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = GnrSqlDb()
        configureDb(cls.db)

        tm = MyTblMixin()
        pm = MyPkgMixin()

        cls.db.packageMixin('video', pm)
        cls.db.tableMixin('video.people', tm)
        cls.db.startup()

    def test_package(self):
        assert self.db.packageSrc('video').attributes['comment'] == 'video package'

    def test_tables_exist(self):
        tables = list(self.db.packageSrc('video')['tables'].keys())
        for tbl in ('people', 'cast', 'movie', 'dvd', 'location'):
            assert tbl in tables

    def test_table_pkey(self):
        assert self.db.packageSrc('video').table('people').attributes['pkey'] == 'id'

    def test_column(self):
        assert self.db.packageSrc('video').table('movie').column('description').attributes[
               'name_short'] == 'Dsc'

    def test_column_upd(self):
        self.db.packageSrc('video').table('movie').column('genre', name_full='Genre')
        assert self.db.packageSrc('video').table('movie')['columns.genre?name_full'] == 'Genre'

    def test_relation(self):
        assert self.db.packageSrc('video').table('cast').column('person_id')[
               'relation?related_column'] == "people.id"

    def test_externalPackage(self):
        assert self.db.packageSrc('video').table('movie').externalPackage(
                'video') == self.db.packageSrc('video')

    def test_table_upd(self):
        self.db.packageSrc('video').table('movie', name_full='Movie')
        assert self.db.packageSrc('video').table('movie').attributes['name_full'] == 'Movie'

    def test_mixinPackage(self):
        assert self.db.packageSrc('video').table('actor').column('id') != None
        assert 'this is video package' == self.db.package('video').sayMyName()

    def test_mixinTable(self):
        assert 'foo' in list(self.db.packageSrc('video').table('people')['columns'].keys())
        assert 'Hello Genro' == self.db.table('video.people').sayHello('Genro')

    @classmethod
    def teardown_class(cls):
        pass


class MyTblMixin(object):
    def config_db(self, pkg):
        t = pkg.table('people')
        t.column('foo')

    def sayHello(self, name):
        return 'Hello %s' % name

class MyPkgMixin(object):
    def config_db(self, pkg):
        pkg.table('actor', name_short='act', name_long='actor', pkey='id').column('id', 'L')

    def sayMyName(self):
        return 'this is %s package' % self.name
