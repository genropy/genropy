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

    def realignRelatedRelIdxAll(self):
        f = self.tblobj.query(columns='${}'.format(self.tblobj.pkey), 
                            subtable='*',ignorePartition=True,
                            excludeDraft=False,
                            excludeLogicalDeleted=False,
                            order_by='$__ins_ts').fetch()
        for r in f:
            self.realignRelatedRelIdx(r['id'])

    def realignRelatedRelIdx(self,pkey):
        relidx_dict = {}
        for rel in self.tblobj.relations_many:
            mpkg, mtbl, fkey = rel.attr['many_relation'].split('.')
            reltbl = '{mpkg}.{mtbl}'.format(mpkg=mpkg,mtbl=mtbl)
            relatedTable = self.db.table(reltbl)
            relidx = relatedTable.attributes.get('relidx')
            if relidx==fkey:
                keyrelidx = '{}_relidx'.format(reltbl.replace('.','_'))
                cnt = self._realignRelatedRelIdx_one(relatedTable,pkey,fkey)
                if cnt:
                    relidx_dict[keyrelidx] = cnt
        if not relidx_dict:
            return
        with self.xtdtable.recordToUpdate(pkey,insertMissing=True) as xtd:
            xtd['main_id'] = pkey
            xtd.update(relidx_dict)

    def _realignRelatedRelIdx_one(self,manytable,pkey,fkey):
        rows = manytable.query(columns='*', where='${} = :pid'.format(fkey),
                            pid=pkey, for_update=True,
                            subtable='*',ignorePartition=True,
                            excludeDraft=False,
                            excludeLogicalDeleted=False,
                            order_by='$__ins_ts').fetch()
        if not rows:
            return
        for idx,r in enumerate(rows):
            idx+=1
            ur = dict(r)
            ur['_relidx'] = idx
            manytable.raw_update(ur,r)
        return idx
        



    def mainChangelog(self,record=None,old_record=None,**kwargs):
        pass
    
    def relatedChangelog(self,tblobj,record=None,old_record=None,**kwargs):
        pass
