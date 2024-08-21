#!/usr/bin/env python
# encoding: utf-8

from builtins import object
from gnr.core.gnrdecorator import metadata

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('language', pkey='code', name_long='!!Language', name_plural='!!Languages',lookup=True,caption_field='name')
        self.sysFields(tbl,counter=True,id=False)
        tbl.column('code' ,size=':2',name_long='!!Code')
        tbl.column('name' ,name_long='!!Name')

    def isInStartupData(self):
        return True
        
    @metadata(mandatory=True)
    def sysRecord_it(self):
        return self.newrecord(code='it',name='Italiano')

    @metadata(mandatory=True)
    def sysRecord_en(self):
        return self.newrecord(code='en',name='English')