# -*- coding: UTF-8 -*-
#--------------------------------------------------------------------------
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
Component for thermo:
"""
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrdecorator import public_method
import os


class AttachManagerView(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        #tbl.column('filepath' ,name_long='!!Filepath')
        r.fieldcell('description',edit=True,width='20em')
        #r.fieldcell('mimetype')
        r.fieldcell('fileurl',hidden=True)
        r.cell('imp',calculated=True,name='!!Imp.',format_isbutton=True,format_buttonclass='iconbox document',
                format_onclick="""
                    genro.serverCall('_table.'+this.attr.table+'.atc_importAttachment',{pkey:this.widget.rowIdByIndex($1.rowIndex)},
                                     function(){console.log("ocr done")});
                """,width='22px')


        #tbl.column('description' ,name_long='!!Description')
        #tbl.column('mimetype' ,name_long='!!Mimetype')
        #tbl.column('text_content',name_long='!!Content')
        #tbl.column('info' ,'X',name_long='!!Additional info')
    
    def th_order(self):
        return '_row_count'


    def onUploading_attachmentComponent(self, file_url=None, file_path=None, file_ext=None, categories=None,
                                  description=None, title=None, action_results=None, **kwargs):
        pass
       #item_table = self.db.table('flib.item')
       #cat_table = self.db.table('flib.item_category')
       #categories = categories.split(',')
       #item_record = dict(path=file_path, url=file_url, description=description, title=title,
       #                   username=self.user, ext=file_ext)
       #versions = Bag()
       #if action_results['thumb32']:
       #    thumb_url = action_results['thumb32']['file_url']
       #    thumb_path = action_results['thumb32']['file_path']
       #    item_record['thumb_url'] = thumb_url
       #    item_record['thumb_path'] = thumb_path
       #    versions['thumb32_url'] = thumb_url
       #    versions['thumb32_path'] = thumb_path
       #item_record['versions'] = versions
       #existing_record = item_table.query(where='path=:p', p=file_path, for_update=True, addPkeyColumn=False).fetch()
       #if existing_record:
       #    r = item_record
       #    item_record = dict(existing_record[0])
       #    item_record.update(r)
       #    item_table.update(item_record)
       #    cat_table.deleteSelection('item_id', item_record['id'])
       #else:
       #    item_table.insert(item_record)
       #for category_id in categories:
       #    if category_id:
       #        cat_table.insert(dict(category_id=category_id, item_id=item_record['id']))
       #self.db.commit()




class Form(BaseComponent):
    pass


class AttachManager(BaseComponent):
    js_requires='gnrcomponents/attachmanager/attachmanager'

    @struct_method
    def at_attachmentGrid(self,pane,title=None,searchOn=False,pbl_classes=True,datapath='.attachments',**kwargs):
        bc = pane.borderContainer()
        th = bc.contentPane(region='left',width='400px',margin='2px',splitter=True).inlineTableHandler(relation='@atc_attachments',
                                        viewResource='gnrcomponents/attachmanager/attachmanager:AttachManagerView',
                                        hider=True,autoSave=True,statusColumn=True,
                                        addrow=False,pbl_classes=pbl_classes,margin='2px',
                                     semaphore=False, searchOn=False,datapath=datapath,**kwargs)
        th.view.grid.attributes.update(dropTarget_grid='Files',onDrop='AttachManager.onDropFiles(this,files);',
                                        dropTypes='Files',_uploader_fkey='=#FORM.pkey',
                                        _uploader_onUploadingMethod=self.onUploadingAttachment)

        bc.contentPane(region='center',datapath=datapath,margin='2px',border='1px solid silver').iframe(src='^.view.grid.selectedId?fileurl',
                                                                height='100%',width='100%',border=0)
        return th


    @public_method
    def onUploadingAttachment(self,kwargs):
        attachment_table = kwargs.get('attachment_table')
        maintable = attachment_table[0:-4]
        maintable_id = kwargs.get('maintable_id')
        maintableobj = self.db.table(maintable)
        filename = kwargs.get('filename')
        description,ext = os.path.splitext(filename)
        path = os.path.join(maintable.replace('.','_'),maintable_id)
        if hasattr(maintableobj,'atc_getAttachmentPath'):
            path = maintableobj.atc_getAttachmentPath(pkey=maintable_id)
        kwargs['uploadPath'] = 'vol:%s' %path
        record = dict(maintable_id=maintable_id,mimetype=kwargs.get('mimetype'),description=description,filepath=os.path.join(path,filename))
        self.db.table(attachment_table).insert(record)
        self.db.commit()
