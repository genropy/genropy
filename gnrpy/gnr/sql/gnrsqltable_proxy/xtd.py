# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package            : GenroPy sql - see LICENSE for details
# module gnrsqlmodel : an advanced data storage system
# Copyright (c)      : 2004 - 2007 Softwell sas - Milano 
# Written by         : Giovanni Porcari,Michele Bertoldi, 
#                      Saverio Porcari, Francesco Porcari,Francesco Cavazzana
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

from gnr.core.gnrstring import encode36
from gnr.core.gnrbag import Bag,BagResolver
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrdecorator import extract_kwargs


class XTDHandler(object):
    """docstring for XTDHandler"""
    def __init__(self, tblobj):
        self.tblobj = tblobj
        self.db = self.tblobj.db
    

    def __getattr__(self, fname): 
        return getattr(self.xtdtable, fname,None)

    @property
    def xtdtable(self):
        return self.db.table(self.tblobj.attributes['xtdtable'])

    def onDeletedMain(self,mainrecord):
        if not self.tblobj.attributes.get('copy_deleted_record'):
            self.xtdtable.delete(mainrecord[self.tblobj.pkey])
            return
        with self.xtdtable.recordToUpdate(mainrecord[self.tblobj.pkey],insertMissing=True) as xtd:
            xtd['id'] = mainrecord[self.tblobj.pkey]
            deleted_record = self.tblobj.newrecord()
            deleted_record['xtd_id'] = xtd['id']
            for k,v in mainrecord.items():
                deleted_record[k] = v
            xtd['deleted_record'] = deleted_record

    def mainChangelog(self,*args,**kwargs):
        pass
    
    def relatedChangelog(self,*args,**kwargs):
        pass