# -*- coding: utf-8 -*-
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

from gnr.core.gnrdict import dictExtract
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrdecorator import public_method,extract_kwargs
from gnr.core.gnrstring import slugify
import os


IMAGES_EXT = ('.png','.jpg','.jpeg','.gif')



class ViewAtcMobile(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('fileurl',width='100%', 
                    template='<div class="atc_iframe_wrapper"><iframe src="#" width="100%" height="100%" class="atc_iframe_resizer" frameBorder="0"></iframe><div>')

class ViewAtcMobileNoPreview(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('description',width='100%', 
                    template='<div class="atc_description">#<div>')


class FormAtcMobile(BaseComponent):
    def th_form(self, form):
        bc = form.center.borderContainer()
        bc.contentPane(region='center',datapath='.record').iframe(src='^.fileurl',_virtual_column='fileurl',height='100%',width='100%',border=0)

    def th_options(self):
        return dict(formCaption=True,modal='navigation')

    


class AttachManagerViewBase(BaseComponent):

    def th_hiddencolumns(self):
        return '$fileurl,$is_foreign_document'

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('_row_count',counter=True,hidden=True)
        r.fieldcell('description',edit=True,width='20em')
    
    def th_order(self):
        return '_row_count'

class AttachManagerView(AttachManagerViewBase):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('full_external_url',hidden=True)
        r.fieldcell('_row_count',counter=True,hidden=True)
        #tbl.column('filepath' ,name_long='!!Filepath')
        r.fieldcell('description',edit=True,width='20em')
        #r.fieldcell('mimetype')
        if hasattr(r.tblobj,'atc_types'):
            r.fieldcell('atc_type',edit=True,name='Type')
        if hasattr(r.tblobj,'atc_download'):
            r.fieldcell('atc_download',edit=True,name='DL')
        r.cell('copyurl',calculated=True,name='Copy url',cellClasses='cellbutton',
                    format_buttonclass='copy iconbox',
                    format_isbutton=True,
                    format_onclick="""
            var row = this.widget.rowByIndex($1.rowIndex);
            var external_url = row.full_external_url;
            genro.textToClipboard(external_url,_T('Copied into clipboard'));
            """)
        if r.tblobj.attributes.get('handle_ocr'):
            r.cell('imp',calculated=True,name='!!Imp.',format_isbutton=True,format_buttonclass='iconbox document',
                format_onclick="""
                    genro.serverCall('_table.'+this.attr.table+'.atc_importAttachment',{pkey:this.widget.rowIdByIndex($1.rowIndex)},
                                     function(){console.log("ocr done")});
                """,width='22px')
        for field,c in r.tblobj.columns.items():
            cellkw = dictExtract(c.attributes,'cell_')
            if cellkw:
                r.fieldcell(field,**cellkw)


class AttachGalleryView(AttachManagerViewBase):
    def th_hiddencolumns(self):
        return '$fileurl,$description'

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('_row_count',counter=True,hidden=True)
        r.cell('gallerycell',width='100%',calculated=True)

    @public_method
    def th_applymethod(self,selection):
        def apply_gallerycell(row):
            url = row['fileurl']
            if not url:
                return dict(gallerycell="<div class='gallerybox_caption'>%s</div>" %row['description'])
            n,ext = os.path.splitext(url)
            if ext not in IMAGES_EXT:
                url = '/_gnr/11/css/icons/base256/empty_iframe.png'
            return dict(gallerycell='<div class="gallerybox"" ><div class="gallerybox_caption" >%s</div><img style="height:90px;max-width:100%%;" border=0 draggable="false" src="%s" /></div>' % (row['description'],url))
        selection.apply(apply_gallerycell)

class Form(BaseComponent):

 
    def th_form(self, form):
        sc = form.center.stackContainer(datapath='.record')
        bc = sc.borderContainer()
        if hasattr(self,'atc_metadata'):
            self.atc_metadata(bc)
        bc.attachmentPreviewViewer(src='^.fileurl',selectedPage='^#FORM.viewerMode',region='center',overflow='hidden',currentPreviewZoom='^#FORM.currentPreviewZoom')
        da = sc.contentPane().div(position='absolute',top='10px',left='10px',right='10px',bottom='10px',
            text_align='center',border='3px dotted #999',rounded=8)
        upload_message = '!!Drag here or double click to upload' if not self.isMobile else "!!Double click to upload"
        

        center_cell = da.table(height='100%',width='100%').tr().td()
        center_cell.div(upload_message,width='100%',font_size='30px',color='#999',hidden='^#FORM.controller.locked')
        fattr = form.attributes
        askMetadata = fattr.pop('askMetadata',None)
        da.dropUploader(position='absolute',top=0,bottom=0,left=0,right=0,z_index=10,
                        _class='attachmentDropUploader',
                        ask = askMetadata,
                        selfsubscribe_inserted_attachment="""this.form.goToRecord($1.record_id);""",
                        onUploadingMethod=self.onUploadingAttachment,
                        onUploadedMethod=self.onUploadedAttachment,
                        rpc_maintable_id='=#FORM.record.maintable_id',
                        rpc_attachment_table=fattr.get('table'),
                        nodeId='%(frameCode)s_uploader' %fattr)
        form.dataController("sc.switchPage(newrecord?1:0)",newrecord='^#FORM.controller.is_newrecord',sc=sc.js_widget)

    def th_options(self):
        return dict(showtoolbar=False,showfooter=False,autoSave=True)

    @public_method
    def th_onLoading(self, record, newrecord, loadingParameters, recInfo):
        if newrecord:
            record['id'] = self.db.table(record.tablename).newPkeyValue()


class ViewPalette(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('description',width='100%',name='!!Attachment')
        r.fieldcell('fileurl',hidden=True)

    def th_view(self,view):
        view.top.popNode('bar')

class FormPalette(Form):
    pass

class UploaderViewerPane(BaseComponent):
    js_requires='gnrcomponents/attachmanager/attachmanager'
    css_requires = 'gnrcomponents/attachmanager/attachmanager'

    @struct_method
    def upv_viewerStack(self,parent,src=None,currentPreviewZoom=None,**kwargs):
        sc = parent.stackContainer(**kwargs)
        sc.contentPane(pageName='document').iframe(src=src,height='100%',
                                  avoidCache=True,width='100%',border='0px',documentClasses=True)
        sc.contentPane(pageName='image').img(src=src,zoom=currentPreviewZoom)
        parent.dataController("""
        let ext = src.split("?")[0].split('.').pop()
        SET .$ext = src.split("?")[0].split('.').pop();
        sc.switchPage(['jpg','jpeg','png','svg'].includes(ext)?1:0);
        """,src=src,_if='src',sc=sc.js_widget)

    @extract_kwargs(uploader=True)
    @struct_method
    def upv_uploaderViewerPane(self,parent,fileurl=None,upload_message=None,uploader_kwargs=None,**kwargs):
        sc = parent.stackContainer(_workspace=True,**kwargs)
        bc = sc.borderContainer()
        bc.attachmentPreviewViewer(src=fileurl,
                                   region='center',overflow='hidden',
                                   currentPreviewZoom='^#WORKSPACE.currentPreviewZoom')
        da = sc.contentPane().div(position='absolute',top='10px',left='10px',right='10px',bottom='10px',
            text_align='center',border='3px dotted #999',rounded=8)
        if not upload_message:
            upload_message = '!!Drag here or double click to upload' if not self.isMobile else "!!Double click to upload"
        center_cell = da.table(height='100%',width='100%').tr().td()
        center_cell.div(upload_message,width='100%',font_size='30px',color='#999')
        da.dropUploader(position='absolute',top=0,bottom=0,left=0,right=0,z_index=10,
                        _class='attachmentDropUploader',
                        **uploader_kwargs)
        bc.dataController("""console.log('fileurl',fileurl);
                                sc.switchPage(fileurl?0:1)""",fileurl=fileurl,sc=sc.js_widget)

class AttachManager(BaseComponent):
    py_requires = 'gnrcomponents/attachmanager/attachmanager:UploaderViewerPane'
    js_requires='gnrcomponents/attachmanager/attachmanager'
    css_requires = 'gnrcomponents/attachmanager/attachmanager'

    @struct_method
    def at_attachmentBottomDrawer(self,bottom,title=None,**kwargs):
        title = title or '!![en]Attachments'
        bottom.attributes.update(
            height='300px',
            closable_label=title,closable='close', closable__class='drawer_allegati'
        )
        th = bottom.attachmentViewer(preview=False,margin='5px',margin_top=0,title=title,**kwargs)
        th.view.grid_envelope.attributes['border'] = '1px solid silver'
        th.view.grid_envelope.attributes['border_radius'] = '10px'
        th.view.grid_envelope.attributes['margin'] = '10px'
        th.view.grid_envelope.attributes['margin_top'] = '0'

    @extract_kwargs(default=True)
    @struct_method
    def at_attachmentViewer(self,pane,title=None,
                            datapath='.attachments',maintable_id=None,
                            relation=None,table=None,preview=True,delrow=False,
                            uploaderButton=None,ask=None,default_kwargs=None,
                            **kwargs):
        if not table:
            relation=relation or '@atc_attachments'
        viewResource = 'gnrcomponents/attachmanager/attachmanager:ViewAtcMobile' if preview else 'gnrcomponents/attachmanager/attachmanager:ViewAtcMobileNoPreview'
        th = pane.dialogTableHandler(relation=relation,table=table,
                                    title=title or '!![en]Attachments',
                                        viewResource=viewResource,
                                        formResource='gnrcomponents/attachmanager/attachmanager:FormAtcMobile',
                                        mobileTemplateGrid=True,
                                        searchOn=False,datapath=datapath,configurable=False,delrow=delrow,
                                     **kwargs)
        if uploaderButton:
            th.view.bottom.dropUploader(
                            label='<div class="atc_galleryDropArea"><div>Drop document here</div><div>or double click</div></div>',
                            height='40px',
                            ask=ask,
                            onUploadingMethod=self.onUploadingAttachment,
                            rpc_maintable_id= maintable_id.replace('^','=') if maintable_id else '=#FORM.pkey',
                            rpc_attachment_table= th.view.grid.attributes['table'],
                            _class='importerPaletteDropUploaderBox',
                            cursor='pointer',nodeId='%(nodeId)s_uploader' %th.attributes,
                            **{f'rpc_{k}':v for k,v in default_kwargs.items()})

        view = th.view
        view.top.pop('bar')
        return th 

    @struct_method
    def at_attachmentPreviewViewer(self,parent,src=None,currentPreviewZoom=None,**kwargs):
        sc = parent.stackContainer(_virtual_column='fileurl',**kwargs)
        sc.contentPane(pageName='document').iframe(src=src,height='100%',
                                  avoidCache=True,width='100%',border='0px',documentClasses=True)
        sc.contentPane(pageName='image').img(src=src,zoom=currentPreviewZoom)
        parent.dataController("""
        let ext = src.split("?")[0].split('.').pop()
        SET .$ext = src.split("?")[0].split('.').pop();
        sc.switchPage(['jpg','jpeg','png','svg'].includes(ext)?1:0);
        """,src=src,_if='src',sc=sc.js_widget)

    @extract_kwargs(default=True,vpane=True,fpane=True)
    @struct_method
    def at_attachmentGrid(self,pane,title=None,searchOn=False,pbl_classes=True,datapath='.attachments',
                            screenshot=False,viewResource=None,
                            design=None,maintable_id=None,uploaderButton=False,ask=None,default_kwargs=None,vpane_kwargs=None,
                            fpane_kwargs=None,**kwargs):
        design = design or 'sidebar'
        bc = pane.borderContainer(design=design)
        d = dict(sidebar=dict(region='left',width='400px'),headline=dict(region='top',height='300px'))
        kwargs.setdefault('grid_selfDragRows',True)
        kwargs.setdefault('autoSave',True)
        d[design].update(vpane_kwargs)
        th = bc.contentPane(splitter=True,**d[design]).inlineTableHandler(relation='@atc_attachments',
                                        viewResource=viewResource or 'gnrcomponents/attachmanager/attachmanager:AttachManagerView',
                                        hider=True,statusColumn=True,
                                        addrow=False,pbl_classes=pbl_classes,
                                     semaphore=False, searchOn=searchOn,datapath=datapath,**kwargs)
        if screenshot:
            th.view.top.bar.replaceSlots('delrow','delrow,screenshot,5')
        th.view.bottom.dropUploader(
                            label='<div class="atc_galleryDropArea"><div>Drop document here</div><div>or double click</div></div>',
                            height='40px',
                            ask=ask,
                            onUploadingMethod=self.onUploadingAttachment,
                            rpc_maintable_id= maintable_id.replace('^','=') if maintable_id else '=#FORM.pkey',
                            rpc_attachment_table= th.view.grid.attributes['table'],
                            _class='importerPaletteDropUploaderBox',
                            cursor='pointer',nodeId='%(nodeId)s_uploader' %th.attributes,
                            **{f'rpc_{k}':v for k,v in default_kwargs.items()})
        fpane_kw = dict(margin='2px',border='1px solid silver')
        fpane_kw.update(fpane_kwargs)
        readerpane = bc.contentPane(region='center',datapath=datapath,overflow='hidden',**fpane_kw)
        readerpane.dataController('SET .reader_url=fileurl',fileurl='^.view.grid.selectedId?fileurl')
        readerpane.iframe(src='^.reader_url',height='100%',width='100%',avoidCache=True,
                            border=0,documentClasses=True)
        return th

    @struct_method
    def at_attachmentPane(self,pane,title=None,searchOn=False,pbl_classes=True,
                        datapath='.attachments',mode=None,viewResource=None,**kwargs):
        frame = pane.framePane(frameCode='attachmentPane_#')
        bc = frame.center.borderContainer()
        mode = mode or 'sidebar'
        d = dict(sidebar=dict(region='left',width='400px'),headline=dict(region='top',height='300px'))
        th = bc.contentPane(splitter=True,childname='atcgrid',**d[mode]).inlineTableHandler(relation='@atc_attachments',
                                        viewResource= viewResource or 'gnrcomponents/attachmanager/attachmanager:AttachManagerView',
                                        hider=True,autoSave=True,statusColumn=True,
                                        addrow=False,delrow=False,pbl_classes=pbl_classes,
                                        autoSelect=True,
                                     semaphore=False, searchOn=False,datapath=datapath,**kwargs)
        th.view.top.popNode('bar')
        th.view.grid.attributes.update(dropTarget_grid='Files',onDrop='AttachManager.onDropFiles(this,files);',
                                        dropTypes='Files',_uploader_fkey='=#FORM.pkey',
                                        _uploader_onUploadingMethod=self.onUploadingAttachment)
        readerpane = bc.contentPane(region='center',datapath=datapath,margin='2px',border='1px solid #efefef',
                                rounded=6,childname='atcviewer',overflow='hidden')
        readerpane.iframe(src='^.reader_url',height='100%',width='100%',
                            avoidCache=True, border=0, documentClasses=True)
        readerpane.dataController('SET .reader_url=fileurl',fileurl='^.view.grid.selectedId?fileurl')
        bar = frame.top.slotToolbar('5,vtitle,*,delrowbtn',vtitle=title or '!!Attachments')
        bar.delrowbtn.slotButton('!!Delete attachment',iconClass='iconbox delete_row',
                        action='gr.publish("delrow")',gr=th.view.grid)
        return frame

    @struct_method
    def at_slotbar_screenshot(self,pane,**kwargs):
        pane.slotButton('"Snapshot',iconClass='iconbox photo',action="""FIRE .takeSnapshot;""")
        pane.dataController("""
                        var attachment_table = this.getInheritedAttributes()['table'];
                        var kw = {attachment_table:attachment_table,maintable_id:fkey,onUploadingMethod:onUploadingMethod,uploaderId:'attachmentManager'};
                        var fm = genro.getParentGenro().framedIndexManager;
                        if(fm){
                            fm.callOnCurrentIframe('dev','takePicture',[kw]);
                        }else{
                            genro.dev.takePicture(kw);
                        }
            """,_fired='^.takeSnapshot',fkey='=#FORM.pkey',onUploadingMethod=self.onUploadingAttachment)

    @struct_method
    def at_attachmentGallery(self,pane,title=None,searchOn=False,
                        datapath='.attachments',mode=None,viewResource=None,
                        table=None,maintable_id=None,nodeId=None,
                        parentStack=None,
                        uploaderButton=True,
                        **kwargs):
        #it will replace at_attachmentPane and at_attachmentGrid

        frame = pane.framePane(frameCode='attachmentPane_#',title=title,datapath=datapath,**kwargs)
        bc = frame.center.borderContainer()
        mode = mode or 'sidebar'
        d = dict(sidebar=dict(region='left',width='180px'),headline=dict(region='top',height='300px'))
        thkwargs = dict()
        if not table:
            thkwargs['relation'] = '@atc_attachments'
        else:
            thkwargs['table'] = table
            thkwargs['condition'] = "$maintable_id=:maintable_id"
            thkwargs['condition_maintable_id'] = maintable_id
        th = bc.contentPane(splitter=True,childname='atcgrid',border_right='1px solid silver',closable=True,**d[mode]).plainTableHandler(
                                        viewResource= viewResource or 'gnrcomponents/attachmanager/attachmanager:AttachGalleryView',
                                        hider=True,addrow=False,delrow=False,_class='noheader atc_gallerygrid',
                                        nodeId=nodeId or 'thattachments_#',
                                        datapath='.th',
                                        configurable=False,
                                        autoSelect=True,semaphore=False,
                                        view_grid_connect_onRowDblClick="""
                                                                        var row = this.widget.rowByIndex($1.rowIndex);
                                                                        FIRE .changeDescription = {pkey:row._pkey,description:row.description}
                                                                        """,
                                        searchOn=False,
                                        **thkwargs)
        th.view.top.bar.replaceSlots('#','2,searchOn,*',toolbar=False,background='#DBDBDB',border_bottom='1px solid silver')
        readerpane = bc.contentPane(region='center',childname='atcviewer',overflow='hidden')
        iframe = readerpane.iframe(src='^.reader_url',height='100%',width='100%',border=0,documentClasses=True,
                        avoidCache=True,
                        connect_onload="""
                            if(this.domNode.getAttribute('src') && this.domNode.getAttribute('src').indexOf('.pdf')<0){
                                var cw = this.domNode.contentWindow;
                                cw.document.body.style.zoom = GET .currentPreviewZoom;
                            }
                            """)
        readerpane.dataController('SET .reader_url=fileurl',fileurl='^.th.view.grid.selectedId?fileurl')
        bar = frame.top.slotToolbar('2,vtitle,*,previewZoom,delrowbtn',vtitle=title or '!!Attachments')
        bar.previewZoom.horizontalSlider(value='^.currentPreviewZoom', minimum=0, maximum=1,
                                 intermediateChanges=False, width='15em',default_value=.5)
        bar.delrowbtn.slotButton('!!Delete attachment',iconClass='iconbox delete_row',
                        action='gr.publish("delrow")',gr=th.view.grid)

        if uploaderButton:
            th.view.bottom.dropUploader(
                            label='<div class="atc_galleryDropArea"><div>Drop document here</div><div>or double click</div></div>',
                            height='40px',
                            onUploadingMethod=self.onUploadingAttachment,
                            rpc_maintable_id= maintable_id.replace('^','=') if maintable_id else '=#FORM.pkey' ,
                            rpc_attachment_table= th.view.grid.attributes['table'],
                            _class='importerPaletteDropUploaderBox',
                            cursor='pointer',nodeId='%(nodeId)s_uploader' %th.attributes)
        th.view.grid.dataController("""
            genro.dlg.prompt(dlgtitle,{lbl:_T('Description'),dflt:pars.description,action:function(result){
                    genro.serverCall(rpcmethod,{pkey:pars.pkey,description:result,table:table},function(){},null,'POST');
                }})
            """,pars='^.changeDescription',dlgtitle='!!Change description',
            table=th.view.grid.attributes['table'],rpcmethod=self.atc_updateDescription)

        th.view.dataController("genro.publish('changed_attachments_number',{table:table.slice(0,-4),pkey:maintable_id,count:(totalrows || 0)});",
                                totalrows='^.store?totalrows',
                                table=th.view.grid.attributes['table'],
                                maintable_id=maintable_id.replace('^','=') if maintable_id else '=#FORM.pkey')
        readerpane.dataController("""
                                    if(iframe.getAttribute('src') && iframe.getAttribute('src').indexOf('.pdf')<0){
                                        iframe.contentWindow.document.body.style.zoom = currentPreviewZoom;
                                    }
                                    """,iframe=iframe.js_domNode,
                        currentPreviewZoom='^.currentPreviewZoom')

        return frame

    @public_method
    def atc_updateDescription(self,pkey=None,description=None,table=None,**kwargs):
        with self.db.table(table).recordToUpdate(pkey) as record:
            record['description'] = description
        self.db.commit()



    @struct_method
    def at_attachmentMultiButtonFrame(self,pane,datapath='.attachments',formResource=None,parentForm=True,ask=None,
                                      toolbarPosition=None,**kwargs):   
        toolbarPosition = toolbarPosition or 'top'
        frame = pane.multiButtonForm(frameCode='attachmentPane_#',datapath=datapath,
                            relation='@atc_attachments',
                            caption='description',parentForm=parentForm,
                            form_askMetadata=ask,
                            formResource= formResource or 'gnrcomponents/attachmanager/attachmanager:Form',
                            multibutton_deleteAction="""
                                if(this.form && this.form.isDisabled()){
                                    return;
                                }
                                var s = this._value.getNode('store').gnrwdg.store;
                                s.deleteAsk([value]);
                            """,
                            multibutton_deleteSelectedOnly=True,
                            toolbarPosition=toolbarPosition,
                            store_order_by='$_row_count')
        frame.multiButtonView.item(code='add_atc',caption='+',frm=frame.form.js_form,
                                    action='frm.newrecord();',
                parentForm=parentForm,deleteAction=False,disabled='==!_store || _store.len()==0 || (this.form?this.form.isDisabled():false)',
                _store='^.store',_flock='^#FORM.controller.locked')
        table = frame.multiButtonView.itemsStore.attributes['table']
        bar = getattr(frame,toolbarPosition).bar.replaceSlots('#','2,mbslot,15,changeName,*,previewZoom,externalUrl,2')
        bar.previewZoom.horizontalSlider(value='^.form.currentPreviewZoom', minimum=0, maximum=1,
                                         hidden='^.form.viewerMode?=#v!="image"',
                                 intermediateChanges=True, width='15em',default_value=1)
        fb = bar.changeName.div(_class='iconbox tag',hidden='^.form.controller.is_newrecord',tip='!!Change description').tooltipPane(
                connect_onClose='FIRE .saveDescription;',
            ).div(padding='10px').formbuilder(cols=1,border_spacing='3px',datapath='.form.record')
        fb.textbox(value='^.description',lbl='!!Description')
        frame.parametersForm = fb
        fb = bar.externalUrl.div(_class='iconbox globe',hidden='^.form.controller.filepath',tip='!!External url').tooltipPane(
                connect_onClose='FIRE .saveDescription;',
            ).div(padding='10px').formbuilder(cols=1,border_spacing='3px')
        fb.textbox(value='^.form.record.external_url',lbl='!!External url')
        frame.dataController("""
            if(frm.getParentForm().isNewRecord()){
                frame.setHiderLayer(true,{message:newrecordmessage,background_color:'white'});
            }else{
                frame.setHiderLayer(false);
                frm.newrecord();
            }
            """,store='^.store',_delay=100,newrecordmessage="!!Save record before upload attachments",
            _fired='^#FORM.controller.loaded',
            _if='!store || store.len()==0',
            frm=frame.form.js_form,frame=frame)
        frame.dataController("frm.lazySave()",frm=frame.form.js_form,_fired='^.saveDescription')
        return frame

    @public_method
    def onUploadingAttachment(self,kwargs):
        attachment_table = kwargs.get('attachment_table')
        maintable_id = kwargs.get('maintable_id')
        filename = kwargs.get('filename')
        attachment_tblobj =  self.db.table(attachment_table)
        uploaderId = kwargs.get('uploaderId')
        atcNode = attachment_tblobj._getDestAttachmentNode(maintable_id=maintable_id,filename=filename)
        kwargs['uploadPath'] = atcNode.dirname
        kwargs['filename'] = atcNode.basename
        record = attachment_tblobj.newrecord(maintable_id=maintable_id,mimetype=kwargs.get('mimetype'),
                    description=atcNode.cleanbasename,filepath=atcNode.fullpath)
        for k,v in kwargs.items():
            if v is not None and attachment_tblobj.column(k) is not None:
                record[k] = v
        attachment_tblobj.insert(record)
        kwargs['attachment_id'] = record['id']
        self.db.commit()        
        self.clientPublish('inserted_attachment',nodeId=uploaderId,record_id=record['id'])


    @public_method
    def onUploadedAttachment(self,file_url=None, file_path=None, file_ext=None, action_results=None,
                                attachment_id=None, **kwargs):
        attachment_table = kwargs.get('attachment_table')
        maintable_id = kwargs.get('maintable_id')
        filename = kwargs.get('filename')
        attachment_tblobj =  self.db.table(attachment_table)
        attachment_tblobj.onUploadedAttachment(attachment_id)
        