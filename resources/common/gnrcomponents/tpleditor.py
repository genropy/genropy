# -*- coding: utf-8 -*-

# tpleditor.py
# Created by Francesco Porcari on 2011-06-22.
# Copyright (c) 2011 Softwell. All rights reserved.

import os

from past.builtins import basestring
from gnr.web.gnrbaseclasses import BaseComponent,TableScriptToHtml
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrdecorator import public_method,extract_kwargs
from gnr.core.gnrbag import Bag
from io import StringIO
from gnr.core.gnrstring import templateReplace
#from gnr.core.gnrbaghtml import BagToHtml
HT = None
TEMPLATEROW = None
try:
    import lxml.html as HT
    import re
    TEMPLATEROW = re.compile(r"<!--TEMPLATEROW:(.*?)-->")
except:
    pass



class TemplateEditorBase(BaseComponent):
    py_requires='public:Public'

    @public_method
    def te_getPreviewPkeys(self, maintable=None):
        path = self.userStore().getItem('current.table.%s.last_selection_path' % maintable.replace('.', '_'))
        selection = self.db.unfreezeSelection(path)
        if selection:
            result = selection.output('pkeylist')
        else:
            result = self.db.table(maintable).query(limit=10, order_by='$__ins_ts').selection().output('pkeylist')
        return "%s::JS" % str(result).replace("u'", "'")
    
    @public_method
    def te_getPreview(self, record_id=None, compiled=None,templates=None,template_id=None,**kwargs):
        if template_id:
            templates = self.db.table('adm.htmltemplate').readColumns(columns='$name',pkey=template_id)
        tplbuilder = self.te_getTemplateBuilder(compiled=compiled, templates=templates)
        return self.te_renderTemplate(tplbuilder, record_id=record_id, extraData=Bag(dict(host=self.request.host)))

    @public_method
    def te_renderChunk(self, record_id=None,template_address=None,templates=None,template_id=None,template_bag=None,plainText=False,**kwargs):
        result = Bag()
        empty_chunk ='Template not yet created' if plainText else '<div class="chunkeditor_emptytemplate">Template not yet created</div>'
        empty_chunk = 'missing_template'
        if template_bag:
            data = template_bag
            compiled = template_bag['compiled']
            dataInfo = {}
        elif not template_address:
            return Bag(dict(rendered=empty_chunk),data=Bag()),{} 
        else:
            data,dataInfo = self.loadTemplate(template_address=template_address,asSource=True)
            if not data:
                return empty_chunk,dataInfo
            compiled = data['compiled']
            if not compiled:
                content = data['content']
                record = self.db.table(template_address.split(':')[0]).recordAs(record_id)
                result['rendered'] = templateReplace(content,record)
                result['template_data'] = data
                return result,dataInfo
        tplbuilder = self.te_getTemplateBuilder(compiled=compiled, templates=templates)
        rendered = self.te_renderTemplate(tplbuilder, record_id=record_id, extraData=Bag(dict(host=self.request.host)),contentOnly=True)
        result['rendered'] = rendered
        result['template_data'] = data
        return result,dataInfo
    
    def te_getTemplateBuilder(self, compiled=None, templates=None):
        tblobj = self.db.table(compiled.getItem('main?maintable'))
        htmlbuilder = TableScriptToHtml(page=self,templates=templates, resource_table=tblobj,templateLoader=self.db.table('adm.htmltemplate').getTemplate)
        htmlbuilder.doctemplate = compiled
        htmlbuilder.virtual_columns = compiled.getItem('main?virtual_columns')
        htmlbuilder.locale = compiled.getItem('main?locale')
        htmlbuilder.formats = compiled.getItem('main?formats')
        htmlbuilder.masks = compiled.getItem('main?masks')
        htmlbuilder.editcols = compiled.getItem('main?editcols')
        htmlbuilder.df_templates = compiled.getItem('main?df_templates')
        htmlbuilder.dtypes = compiled.getItem('main?dtypes')
        htmlbuilder.data_tblobj = tblobj
        return htmlbuilder
        
    def te_renderTemplate(self, templateBuilder, record_id=None, extraData=None, locale=None,contentOnly=False,**kwargs):
        if record_id:
            record = templateBuilder.data_tblobj.record(pkey=record_id,ignoreMissing=record_id=='*sample*',
                                                        virtual_columns=templateBuilder.virtual_columns,
                                                        ).output('bag')
                                                        
        else:
            record = templateBuilder.data_tblobj.record(pkey='*sample*',ignoreMissing=True,
                                                        virtual_columns=templateBuilder.virtual_columns).output('sample')
        if extraData:
            record.update(extraData)
        locale = locale or templateBuilder.locale
        formats = templateBuilder.formats or dict()
        masks = templateBuilder.masks or dict()
        editcols = templateBuilder.editcols or dict()

        df_templates = templateBuilder.df_templates or dict()
        dtypes = templateBuilder.dtypes or dict()

        record.setItem('_env_', Bag(self.db.currentEnv))
        #record.setItem('_template_', templateBuilder.doctemplate_info)
        htmlContent = templateReplace(templateBuilder.doctemplate,record, safeMode=True,noneIsBlank=False,locale=locale, 
                                                            formats=formats,masks=masks,editcols=editcols,df_templates=df_templates,
                                                            dtypes=dtypes,localizer=self.localizer,
                                                            urlformatter=self.externalUrl)
        if contentOnly:
            return htmlContent
        body = templateBuilder(htmlContent=htmlContent,
                            record=record,page_debug='silver',**kwargs)
        return body
    
    def te_compileBagForm(self,table=None,sourcebag=None,varsbag=None,parametersbag=None,record_id=None,templates=None):
        result = Bag()
        varsdict = dict()
        for varname,fieldpath in varsbag.digest('#v.varname,#v.fieldpath'):
            varsdict[varname] = '$%s' %fieldpath
        for k,v in list(sourcebag.items()):
            if v:
                result[k] = templateReplace(v, varsdict, True,False,urlformatter=self.externalUrl)
        return result
            
        
    @public_method
    def te_compileTemplate(self,table=None,datacontent=None,content_css=None,varsbag=None,parametersbag=None,record_id=None,templates=None,template_id=None,email_meta=None,**kwargs):
        result = Bag()
        formats = dict()
        editcols = dict()
        masks = dict()
        df_templates = dict()
        dtypes = dict()
        columns = []
        virtual_columns = []
        varsdict = dict()
        if varsbag:
            tplvars =  varsbag.digest('#v.varname,#v.fieldpath,#v.virtual_column,#v.required_columns,#v.format,#v.mask,#v.editable,#v.df_template,#v.dtype,#v.fieldname')
            for varname,fldpath,virtualcol,required_columns,format,mask,editable,df_template,dtype,fieldname in tplvars:
                varname = varname or fieldname
                fldpath = fldpath or varname
                fk=''
                if format:
                    fk=varname
                    formats[varname] = format
                if mask:
                    fk=varname
                    masks[varname] = mask
                if editable:
                    fk=varname
                    editcols[varname] = editable
                if df_template:
                    fk=varname
                    df_templates[varname] = df_template
                if dtype:
                    dtypes[varname] = dtype
                if fk:
                    fk='^%s'%fk
                if table:
                    varsdict[varname] = '$%s%s' %(fldpath,fk)
                colname = (varsdict.get(varname) or fldpath).split('^')[0].replace('$@','@')
                columns.append(colname)
                if virtualcol:
                    virtual_columns.append(fldpath)
                if required_columns:
                    prefix = '.'.join(fldpath.split('.')[0:-1])
                    for c in required_columns.split(','):
                        if not c in virtual_columns:
                            virtual_columns.append('%s.%s' %(prefix,c.replace('$','')) if prefix else c)
        if parametersbag:
            tplpars = parametersbag.digest('#v.code,#v.format,#v.mask')
            for code,format,mask in tplpars:
                formats[code] = format
                masks[code] = mask
        template = templateReplace(datacontent, varsdict, True,False,conditionalMode=False)
        compiled = Bag()
        cmain = template
        if HT:
            doc = HT.parse(StringIO(template)).getroot()
            
            innerdatasources = doc.xpath("//*[@row_datasource]")
            if innerdatasources:
                for t in innerdatasources:
                    attributes = t.attrib
                    subname = attributes['row_datasource']
                    if t.tag=='table':
                        repeating_container = t.xpath('tbody')[0]
                        repeating_item = repeating_container.getchildren()[-1]
                    else:
                        repeating_item = t
                        repeating_container = t.getparent()
                    repeating_container.replace(repeating_item,HT.etree.Comment('TEMPLATEROW:$%s' %subname))
                    subtemplate= HT.tostring(repeating_item).decode().replace('%s.'%subname,'').replace('%24','$')
                    compiled.setItem(subname.replace('.','_'),subtemplate)
                body = doc.xpath('//body')[0]
                bodycontent = '\n'.join([HT.tostring(el).decode() for el in body.getchildren()])
                cmain = TEMPLATEROW.sub(lambda m: '\n%s\n'%m.group(1),bodycontent.replace('%24','$'))
        if content_css:
            cmain =f'<style>{content_css}</style>{cmain}'
        compiled.setItem('main', cmain,
                            maintable=table,locale=self.locale,virtual_columns=','.join(virtual_columns),
                            columns=','.join(columns),formats=formats,masks=masks,editcols=editcols,df_templates=df_templates,dtypes=dtypes)
        result.setItem('compiled',compiled)
        if email_meta:
            result.setItem('email_compiled',self.te_compileBagForm(table=table,sourcebag=email_meta,
                                                                    varsbag=varsbag,parametersbag=parametersbag))
        if record_id:
            result.setItem('preview',self.te_getPreview(compiled=compiled,record_id=record_id,templates=templates,template_id=template_id))
        return result

class TemplateEditor(TemplateEditorBase):
    py_requires='gnrcomponents/framegrid:FrameGrid,public:Public'
    css_requires='public'
    @struct_method
    def te_templateEditor(self,pane,storepath=None,maintable=None,editorConstrain=None,plainText=False,datasourcepath=None,**kwargs):
        sc = self._te_mainstack(pane,table=maintable)
        self._te_frameInfo(sc.framePane(title='!!Metadata',pageName='info',childname='info'),table=maintable,datasourcepath=datasourcepath)
        self._te_frameEdit(sc.framePane(title='!!Edit',pageName='edit',childname='edit',editorConstrain=editorConstrain,plainText=plainText))
        self._te_framePreview(sc.framePane(title='!!Preview',pageName='preview',childname='preview'),table=maintable)
        #self._te_frameHelp(sc.framePane(title='!!Help',pageName='help',childname='help'))
        
        return sc
    
    def _te_mainstack(self,pane,table=None):
        sc = pane.stackContainer(selectedPage='^.status',_anchor=True)
        sc.dataRpc('dummy',self.te_compileTemplate,varsbag='=.data.varsbag',
                        content_css='=.data.content_css',
                        parametersbag='=.data.parameters',
                    datacontent='=.data.content',table=table,_if='_status=="preview"&&datacontent&&varsbag',
                    _POST=True,
                    _status='^.status',record_id='=.preview.selected_id',templates='=.preview.html_template_name',
                    _onResult="""
                    SET .data.compiled = result.getItem('compiled').deepCopy();
                    SET .preview.renderedtemplate = result.getItem('preview');
                    var curr_letterehead =GET .preview.letterhead_id;
                    if(!curr_letterehead){
                        SET .preview.letterhead_id = GET .data.metadata.default_letterhead;
                    }
                    """)
        return sc
    
    def _te_varsgrid_struct(self,struct):
        r = struct.view().rows()
        r.cell('fieldname', name='Field', width='20em',edit=True)
        r.cell('varname', name='As', width='15em',edit=True)
        r.cell('dtype', name='Dtype', width='5em',
            edit=dict(values='T:Text,N:Decimal,L:Integer,D:Date,H:Time,B:Boolean,X:Bag'),
            hidden='^.table')
        r.cell('format', name='Format', width='10em',edit=True)
        r.cell('mask', name='Mask', width='20em',edit=True)
        if self.isDeveloper():
            r.cell('editable', name='!!Edit pars', width='20em',edit=True)
            r.cell('df_template', name='!!Df', width='10em',edit=True)
            r.cell('fieldpath', name='!!', width='10em',edit=True)
            r.cell('required_columns', name='!!Req columns', width='10em',edit=True)


    def _te_info_top(self,pane):
        fb = pane.div(margin_right='15px').formbuilder(cols=7, border_spacing='4px',fld_width='100%',width='100%',
                                               datapath='.data.metadata',coswidth='auto')
        fb.textbox(value='^.author',lbl='!!Author',tdf_width='12em')
        fb.numberTextBox(value='^.version',lbl='!!Version',width='4em')
        fb.dateTextBox(value='^.date',lbl='!!Date',width='6em')
        fb.checkbox(value='^.is_print',label='!!Print')
        fb.checkbox(value='^.is_mail',label='!!Mail')
        fb.checkbox(value='^.is_row',label='!!Row')
        fb.numberTextBox(value='^.row_height',width='3em',hidden='^.is_row?=!#v',lbl_hidden='^.is_row?=!#v',lbl='Height')
        fb.dataController("""var result = [];
                             if(is_mail){result.push('is_mail');}
                             if(is_print){result.push('is_print');}
                             if(is_row){result.push('is_row');}
                             if(flags){result.push(flags);}
                             SET #ANCHOR.userobject_meta.flags = result.join(',');""",
                        is_mail="^.is_mail",is_print='^.is_print',is_row='^.is_row',flags='^.flags')
        fb.dbSelect(value='^.default_letterhead',dbtable='adm.htmltemplate',
                    lbl='!!Letterhead',hasDownArrow=True,colspan=3)
        fb.textbox(value='^.summary',lbl='!!Summary',colspan=4)
        if self.isDeveloper():
            fb.textbox(value='^#ANCHOR.userobject_meta.flags',lbl='!!Flags',colspan=7)
    
    @extract_kwargs(fieldsTree=dict(slice_prefix=False))
    def _te_info_vars(self,bc,table=None,datasourcepath=None,fieldsTree_kwargs=None,**kwargs):
        frame = bc.bagGrid(datapath='.varsgrid',title='!!Variables',
                                storepath='#ANCHOR.data.varsbag',
                                struct=self._te_varsgrid_struct,
                                parentForm=False,
                                addrow= not table,
                                splitter=True,**kwargs)
        
        if not (table or datasourcepath):
            return
        if table:
            frame.left.slotBar('5,fieldsTree,*',
                            fieldsTree_table=table,
                            fieldsTree_dragCode='fieldvars',
                            border_right='1px solid silver',
                            closable=True,width='150px',fieldsTree_height='100%',
                            splitter=True,**fieldsTree_kwargs)
        else:
            bar = frame.left.slotBar('5,sourceTree,*',
                            #fieldsTree_dragCode='fieldvars',
                            border_right='1px solid silver',
                            closable=True,width='150px',
                            splitter=True)

            bar.sourceTree.div(text_align='left').tree(storepath=datasourcepath,
                     _class='branchtree noIcon',hideValues=True,margin_top='6px',font_size='.9em',
                      labelAttribute='caption',draggable=True,
                      onDrag="""let kw = {...treeItem.attr};
                                objectUpdate(kw,dragValues.treenode);
                                kw.fieldpath = kw.relpath;
                                kw.dtype = kw.dtype;
                                let val = treeItem.getValue()
                                if(!kw.dtype && val!==null){
                                    kw.dtype = guessDtype(val)
                                }
                                kw.fullcaption = kw.caption || kw.fieldpath.replaceAll('.','/');
                                dragValues["fieldvars"] = kw""")


        grid = frame.grid
        grid.data('.table',table)
        grid.dragAndDrop(dropCodes='fieldvars')
        #tplnames = self.db.table(table).column('df_custom_templates').attributes.get('templates') or ''
        grid.dataController(r"""
                                var caption = data.fullcaption;
                                var varname = caption.replace(/\W/g,'_').toLowerCase();
                                var df_template =null;
                                var fieldpath = data.fieldpath;
                                var dtype = data.dtype;
                                if(fieldpath.indexOf(':')>=0){
                                    fieldpath = fieldpath.split(':');
                                    df_template = fieldpath[1];
                                    fieldpath = fieldpath[0];
                                }
                                grid.gridEditor.addNewRows([{'fieldpath':fieldpath,
                                                                            dtype:dtype,
                                                                            fieldname:caption,
                                                                            varname:varname,
                                                                            virtual_column:data.virtual_column,
                                                                            required_columns:data.required_columns,
                                                                            df_template:df_template}]);
                                """,
                                data="^.dropped_fieldvars",grid=grid.js_widget)    
        


    
    def _te_info_parameters(self,bc,**kwargs):
        bc.bagGrid(datapath='.parametersgrid',title='!!Parameters',
                                storepath='#ANCHOR.data.parameters', 
                                struct=self._te_parameters_struct,
                                parentForm=False,
                                selfDragRows=True,**kwargs)
        
    def _te_frameInfo(self,frame,table=None,datasourcepath=None,**kwargs):
        frame.top.slotToolbar('5,parentStackButtons,*',parentStackButtons_font_size='8pt')
        bc = frame.center.borderContainer()
        self._te_info_top(bc.contentPane(region='top'))
        self._te_info_vars(bc,table=table,region='bottom',height='60%',
                fieldsTree_currRecordPath=datasourcepath)
        self._te_info_parameters(bc,region='center')
        
    def _te_pickers(self,tc):
        tc.dataController("""var result = new gnr.GnrBag();
                            var varfolder= new gnr.GnrBag();
                            var parsfolder = new gnr.GnrBag();
                            var varname,v,parscode;
                            varsbag.forEach(function(n){
                                n.delAttr('_newrecord');
                                n._value.popNode('_newrecord');
                                varname = n._value.getItem('varname') || n._value.getItem('fieldname');
                                varfolder.setItem(n.label,null,{caption:n._value.getItem('fieldname'),code:varname});
                            },'static');
                            result.setItem('variables',varfolder,{caption:varcaption})
                            if (parameters){
                                parameters.forEach(function(n){
                                    n.delAttr('_newrecord');
                                    n._value.popNode('_newrecord');
                                    v = n.getValue();
                                    parscode = v.getItem('code');
                                    parsfolder.setItem(n.label,null,{caption:v.getItem('description') || parscode,code:parscode})
                                },'static');
                                result.setItem('pars',parsfolder,{caption:parscaption})
                            }
                            SET .allvariables = result;
                            FIRE .tree_rebuild;""",
            varsbag="=.data.varsbag",parameters='=.data.parameters',
            varcaption='!!Fields',parscaption='!!Parameters',_if='status=="edit"',status='^.status')
        vartab = tc.contentPane(title='Variables',overflow='auto',text_align='left',margin='2px',_class='pbl_roundedGroup')
        vartab.tree(storepath='.allvariables',_fired='^.tree_rebuild',onDrag="dragValues['text/plain'] = '$'+treeItem.attr.code;",
                hideValues=True,draggable=True,_class='fieldsTree',labelAttribute='code'
                )
        if 'flib' in self.db.packages:
            self.mixinComponent('flib:FlibPicker')
            tc.contentPane(title='!!Files').flibPickerPane(viewResource='ViewFromTemplate', preview=True,
                            gridpane_region='center', gridpane_margin='2px',
                            treepane_region='top',treepane_margin='2px',treepane_splitter=True,
                            treepane__class='pbl_roundedGroup',treepane_height='25%')

        
    def _te_attachedReports(self,pane):
        pane.bagGrid(title='!![en]Attached reports',pbl_classes=True,margin='2px',
                        storepath='#ANCHOR.data.email.attached_reports',
                        datapath='.attached_reports',
                        struct=self._te_attachmentReportStruct)

    def _te_attachmentReportStruct(self,struct):
        r = struct.view().rows()
        r.cell('relation',name='!![en]Relation',width='15em',edit=True)
        r.cell('report',name='!![en]Report',width='15em',edit=True)
        r.cell('resource',name='!![en]Resource',width='15em',edit=True)
        r.cell('condition',name='!![en]Condition',width='15em',edit=True)

    def _te_emailParsFull(self,bc):
        metadatapane = bc.roundedGroup(region='left',title='!![en]Email metadata',width='500px',datapath='.data.metadata.email')
        fb = metadatapane.div(margin_right='10px').formbuilder(cols=1, border_spacing='2px',width='100%',fld_width='100%',tdl_width='8em')
        fb.textbox(value='^.subject', lbl='!!Subject',dropTypes = 'text/plain')
        fb.textbox(value='^.to_address', lbl='!!To',dropTypes = 'text/plain')
        fb.textbox(value='^.from_address', lbl='!!From',dropTypes = 'text/plain')
        fb.textbox(value='^.cc_address', lbl='!!CC',dropTypes = 'text/plain')
        fb.textbox(value='^.bcc_address', lbl='!!BCC',dropTypes = 'text/plain')
        fb.simpleTextArea(value='^.attachments', lbl='!!Attachments',dropTypes = 'text/html')
        self._te_attachedReports(bc.contentPane(region='center'))
        

    def _te_frameEdit(self,frame,editorConstrain=None,plainText=None,emailChunk=None):
        frame.top.slotToolbar(slots='5,parentStackButtons,*',parentStackButtons_font_size='8pt')
        bc = frame.center.borderContainer(design='sidebar')
        self._te_pickers(frame.tabContainer(region='left',width='200px',splitter=True))                
        frame.dataController("bc.setRegionVisible('top',mail)",bc=bc.js_widget,mail='^.data.metadata.is_mail',_if='mail!==null')
        
        if emailChunk:
            if emailChunk=='*':
                self._te_emailParsFull(bc.borderContainer(region='top',height='180px'))
            else:
                fb = bc.contentPane(region='top').div(margin_right='20px').formbuilder(cols=1, border_spacing='2px',width='100%',fld_width='100%',
                                                            datapath='.data.metadata.email',colswidth='auto')
                fb.textbox(value='^.subject', lbl='!!Subject',dropTypes = 'text/plain')
                fb.textbox(value='^.from_address', lbl='!!From',dropTypes = 'text/plain')
        else:
            self._te_emailParsFull(bc.borderContainer(region='top',height='180px',hidden=True))

        editorConstrain = editorConstrain or dict()
        constrain_height = editorConstrain.pop('constrain_height',False)
        constrain_width = editorConstrain.pop('constrain_width',False)
        bc.dataController("""SET .editor.height = letterhead_center_height?letterhead_center_height+'mm': constrain_height;
                             SET .editor.width = letterhead_center_width?letterhead_center_width+'mm':constrain_width;
            """,constrain_height=constrain_height,
                constrain_width=constrain_width,
                letterhead_center_height='^.preview.letterhead_record.center_height',
                letterhead_center_width='^.preview.letterhead_record.center_width',
                _init=True)
        if plainText:
            bc.simpleTextArea(value='^.data.content',region='center',
                            margin='3px',margin_left='6px',border='1px solid silver',
                            dropTarget=True,dropTypes="text/plain",
                            onDrop_text_plain="""let v = this.widget.getValue()
                            v += (' ' + data);
                            this.widget.setValue(v,true);
                            """,
                            rounded=6,padding='5px')
        else:
            bc.ExtendedCkeditor(region='center',margin='2px',margin_left='5px',
                            value='^.data.content',css_value='^.data.content_css',
                            constrain_height='^.editor.height',
                            constrain_width='^.editor.width',**editorConstrain)

    def _te_framePreview(self,frame,table=None):
        bar = frame.top.slotToolbar('5,parentStackButtons,10,fb,*',parentStackButtons_font_size='8pt')                   
        fb = bar.fb.formbuilder(cols=2, border_spacing='0px',margin_top='2px')
        fb.dbSelect(dbtable='adm.htmltemplate', value='^.preview.letterhead_id',
                    selected_name='.preview.html_template_name',lbl='!!Letterhead',
                    width='10em', hasDownArrow=True)
        fb.dbSelect(dbtable=table, value='^.preview.selected_id',lbl='!!Record', width='12em',lbl_width='6em',excludeDraft=False)
        fb.dataRpc('.preview.renderedtemplate', self.te_getPreview,
                   _POST =True,record_id='^.preview.selected_id',
                   #templates='^.preview.html_template_name',
                   compiled='=.data.compiled')
        bc = frame.center.borderContainer()
        
        bc.contentPane(region='center',overflow='hidden',border='1px solid silver',margin='3px'
                            ).iframeDiv(value='^.preview.renderedtemplate',
                                                contentCss='^.data.content_css',
                                                height='100%',width='100%')

        
      # pagedHtml(sourceText=value,pagedText=pagedText,letterheads='^#WORKSPACE.letterheads',editor=editor,letterhead_id=letterhead_id,
      #                         printAction=printAction,bodyStyle=bodyStyle,datasource=datasource,extra_bottom=extra_bottom,**tpl_kwargs)



    # def _te_frameHelp(self,frame):
    #     frame.top.slotToolbar(slots='5,parentStackButtons,*',parentStackButtons_font_size='8pt')
    #     bc = frame.center.borderContainer(design='sidebar')
    #     bc.div('Help')
        
    def _te_parameters_struct(self,struct):
        r = struct.view().rows()
        r.cell('code', name='!!Code', width='10em',edit=True)
        r.cell('description', name='!!Description', width='40em',edit=True)
        r.cell('fieldtype', name='!!Fieldtype', width='10em',edit=dict(values='!!T:Text,L:Integer,D:Date,N:Decimal,B:Boolean,TL:Long Text',tag='filteringSelect'))
        r.cell('format', name='!!Format', width='10em',edit=True)
        r.cell('mask', name='!!Mask', width='15em',edit=True)
        r.cell('values', name='!!Values', width='100%',edit=True)   

class PaletteTemplateEditor(TemplateEditor):
    @struct_method
    def te_paletteTemplateEditor(self,pane,paletteCode=None,maintable=None,**kwargs):
        palette = pane.palettePane(paletteCode=paletteCode or 'template_manager',
                                    title='^.caption',palette_overflow='hidden',
                                    width='750px',height='500px',maxable=True,overflow='hidden',**kwargs)
        palette.remote(self.remoteTemplateEditor,maintable=maintable)

    @public_method
    def remoteTemplateEditor(self,palette,maintable=None):
        sc = palette.templateEditor(maintable=maintable)
        infobar = sc.info.top.bar
        infobar.replaceSlots('#','#,menutemplates,deltpl,savetpl,5')
        infobar.deltpl.slotButton('!!Delete current',iconClass='iconbox trash',
                                action='FIRE .deleteCurrent',disabled='^.currentTemplate.pkey?=!#v')
        infobar.dataController('SET .currentTemplate.path="__newtpl__";',_onBuilt=True)
        infobar.dataFormula(".palette_caption", "prefix+caption",caption="^.caption",prefix='!!Edit ')
        infobar.menutemplates.div(_class='iconbox folder').menu(modifiers='*',storepath='.menu',
                action="""SET .currentTemplate.pkey=$1.pkey;
                          SET .currentTemplate.mode = $1.tplmode;
                          SET .currentTemplate.path = $1.fullpath;""",_class='smallmenu')
        infobar.savetpl.slotButton('!!Save template',iconClass='iconbox save',action='FIRE .savetemplate = genro.dom.getEventModifiers(event);',
                                disabled='^.data.content?=!#v')
        
        editbar = sc.edit.top.bar
        editbar.replaceSlots('#','#,savetpl,5')
        editbar.savetpl.slotButton('!!Save template',iconClass='iconbox save',action='FIRE .savetemplate = genro.dom.getEventModifiers(event);',
                                disabled='^.data.content?=!#v')
        
        previewbar = sc.preview.top.bar
        previewbar.replaceSlots('#','#,savetpl,5')
        previewbar.savetpl.slotButton('!!Save template',iconClass='iconbox save',
                                action="""FIRE .savetemplate = genro.dom.getEventModifiers(event);""",
                                disabled='^.data.content?=!#v')
        
        
        infobar.dataController("""
            var editorbag = this.getRelativeData();
            if(tplpath=='__newtpl__'){
                editorbag.setItem('data',new gnr.GnrBag());
                editorbag.setItem('data.metadata.author',user);
                editorbag.setItem('userobject_meta',new gnr.GnrBag());
                editorbag.setItem('caption',newcaption);
            }else if(pkey){

                genro.serverCall('_table.adm.userobject.loadUserObject',{table:table,pkey:pkey},function(result){
                    editorbag.setItem('data',result._value.deepCopy());
                    editorbag.setItem('mode','userobject');
                    editorbag.setItem('caption',result.attr.description || result.attr.code);
                    editorbag.setItem('userobject_meta',new gnr.GnrBag(result.attr));
                },null,'POST')
            }
        """,tplpath="^.currentTemplate.path",tplmode='=.currentTemplate.tplmode',
                pkey='=.currentTemplate.pkey',table=maintable,newcaption='!!New template',user=self.user)
        infobar.dataRpc('dummy',self.db.table('adm.userobject').deleteUserObject,pkey='=.currentTemplate.pkey',
                        _onResult='SET .currentTemplate.path="__newtpl__";',_fired='^.deleteCurrent')
        infobar.dataController("""
            if(genro.isDeveloper && modifiers=='Shift'){
                FIRE .savetemplateAsResource;
                return;
            }
            if(currentTemplatePkey){
                FIRE .save_userobject = currentTemplatePkey;
            }else{
                FIRE .save_userobject = '*newrecord*';
            }
        """,modifiers='^.savetemplate',currentTemplateMode='=.currentTemplate.tplmode',
                            currentTemplatePath='=.currentTemplate.path',
                            currentTemplatePkey='=.currentTemplate.pkey',
                            data='=.data')

        infobar.dataController("""
            var template_address;
            genro.dlg.prompt('Save as resource',{widget:[{lbl:'Tplname',value:'^.tplname'},{label:'Main Resource',wdg:'checkbox',lbl:'',value:'^.inMainResource'}],

                                action:function(result){
                    template_address =  table+':'+result.getItem('tplname');
                    genro.serverCall("te_saveTemplateAsResource",{table:table,template_address:template_address,data:data,inMainResource:result.getItem('inMainResource')},null,null,'POST');
                }})
        """,_fired='^.savetemplateAsResource',data='=.data',table=maintable)


        infobar.dataController("""
                var that = this;
                var savepath = this.absDatapath('.userobject_meta');
                var kw = {'tplmode':'userobject','table':table,
                        'data':data,metadata:'='+savepath}                
                genro.dev.userObjectDialog(_T('Save Template'),savepath,
                function(dialog) {
                    genro.serverCall('te_saveTemplate',kw,
                        function(result) {
                            that.setRelativeData('.currentTemplate.pkey',result['id']);
                            that.setRelativeData('.currentTemplate.path',result['code']);
                            dialog.close_action();
                        },null,'POST');
            });
            """,pkey='^.save_userobject',data='=.data',table=maintable)
        infobar.dataRemote('.menu',self.te_menuTemplates,table=maintable,cacheTime=5)
        
    @public_method
    def te_menuTemplates(self,table=None):
        result = Bag()
        from_userobject = self.db.table('adm.userobject').userObjectMenu(table,'template') #todo
        for n in from_userobject:
            result.setItem(n.label,None,tplmode='userobject',**n.attr)
        result.setItem('__newtpl__',None,caption='!!New Template')
        return result

    @public_method
    def te_saveTemplateAsResource(self,table=None,template_address=None,data=None,inMainResource=False):
        if data['metadata.email']:
            data['metadata.email_compiled'] = self.te_compileBagForm(table=table,sourcebag=data['metadata.email'],
                                                                    varsbag=data['varsbag'],parametersbag=data['parameters'])
        data['compiled'] = self.te_compileTemplate(table=table,datacontent=data['content'],content_css=data['content_css'],varsbag=data['varsbag'],parametersbag=data['parameters'])['compiled']
        self.saveTemplate(template_address=template_address,data=data,inMainResource=inMainResource)

    @public_method
    def te_saveBagFieldTemplate(self,table=None,respath=None,data=None,custom=False):
        respath = f'bagfields/{respath}'
        data['compiled'] = self.te_compileTemplate(table=table,datacontent=data['content'],content_css=data['content_css'],varsbag=data['varsbag'],parametersbag=data['parameters'])['compiled']
        data.toXml(self.packageResourcePath(table=table,filepath=f'{respath}.xml',custom=custom),autocreate=True)

    @public_method
    def te_loadBagFieldTemplate(self,table=None,respath=None,custom=False):
        respath = f'bagfields/{respath}.xml'
        fullpath = self.packageResourcePath(table=table,filepath=respath,custom=custom)
        if os.path.exists(fullpath):
            return Bag(fullpath)
        return Bag()


    @public_method
    def te_saveTemplate(self,pkey=None,data=None,tplmode=None,table=None,metadata=None,**kwargs):
        record = None
        if data['metadata.email']:
            data['metadata.email_compiled'] = self.te_compileBagForm(table=table,sourcebag=data['metadata.email'],
                                                                    varsbag=data['varsbag'],parametersbag=data['parameters'])
        data['compiled'] = self.te_compileTemplate(table=table,datacontent=data['content'],content_css=data['content_css'],varsbag=data['varsbag'],parametersbag=data['parameters'])['compiled']
        pkey,record = self.db.table('adm.userobject').saveUserObject(table=table,metadata=metadata,data=data,objtype='template')
        record.pop('data')
        return record
        
class ChunkEditor(PaletteTemplateEditor):
    @public_method
    def te_chunkEditorPane(self,pane,table=None,resource_mode=None,paletteId=None,
                            datasourcepath=None,showLetterhead=False,editorConstrain=None,plainText=False,emailChunk=False,**kwargs):
        sc = self._te_mainstack(pane,table=table)
        self._te_frameChunkInfo(sc.framePane(title='!!Metadata',pageName='info',childname='info'),table=table,datasourcepath=datasourcepath)
        bar = sc.info.top.bar
        if table:
            bar.replaceSlots('#','#,customres,menutemplates,savetpl,5')
            bar.menutemplates.div(_class='iconbox folder',tip='!!Copy From').menu(modifiers='*',storepath='.menu',
                    action="""var that = this;
                              genro.serverCall('_table.adm.userobject.loadUserObject',{table:'%s',pkey:$1.pkey},function(result){
                                    var v = result.getValue();
                                    if(!v){
                                        return;
                                    }
                                    that.setRelativeData('.data.varsbag',v.getItem('varsbag'));
                                    that.setRelativeData('.data.content',v.getItem('content'));
                                    that.setRelativeData('.data.content_css',v.getItem('content_css'));
                             },null,'POST');
            """ %table,_class='smallmenu')
            bar.dataRemote('.menu',self.te_menuTemplates,table=table,cacheTime=5)

            if resource_mode:
                bar.customres.checkbox(value='^.data.metadata.custom',label='!!Custom')
            else:
                bar.customres.div()
        else:
            bar.replaceSlots('#','#,savetpl,5')
        self._te_saveButton(bar.savetpl,table,paletteId)
        frameEdit = sc.framePane(title='!!Edit',pageName='edit',childname='edit')
        self._te_frameEdit(frameEdit,editorConstrain=editorConstrain,plainText=plainText,emailChunk=emailChunk)
        if showLetterhead:
            bar = frameEdit.top.bar.replaceSlots('parentStackButtons','parentStackButtons,letterhead_selector')
            fb = bar.letterhead_selector.formbuilder(cols=1,border_spacing='1px')
            if isinstance(showLetterhead,basestring):
                fb.data('.preview.letterhead_id',showLetterhead)
            fb.dbSelect(dbtable='adm.htmltemplate', value='^.preview.letterhead_id',
                        lbl='!!Letterhead',width='15em', hasDownArrow=True)
            fb.dataRecord('.preview.letterhead_record','adm.htmltemplate',pkey='^.preview.letterhead_id',_if='pkey')

        bar = frameEdit.top.bar
        bar.replaceSlots('#','#,savetpl,5')
        self._te_saveButton(bar.savetpl,table,paletteId)
        
        if table:
            framePreview = sc.framePane(title='!!Preview',pageName='preview',childname='preview')
            self._te_framePreviewChunk(framePreview,table=table,datasourcepath=datasourcepath)
            bar = framePreview.top.bar
            bar.replaceSlots('#','#,savetpl,5')
            self._te_saveButton(bar.savetpl,table,paletteId)

        
        
    def _te_frameChunkInfo(self,frame,table=None,datasourcepath=None):
        frame.top.slotToolbar('5,parentStackButtons,*',parentStackButtons_font_size='8pt')
        bc = frame.center.borderContainer()
        self._te_info_vars(bc,table=table,region='center',
                            datasourcepath=datasourcepath,
                            fieldsTree_currRecordPath=datasourcepath,
                            fieldsTree_explorerPath='#ANCHOR.dbexplorer')
        #self._te_info_parameters(bc,region='center')
    
    def _te_framePreviewChunk(self,frame,table=None,datasourcepath=None):
        bar = frame.top.slotToolbar('5,parentStackButtons,10,fb,*',parentStackButtons_font_size='8pt')                   
        fb = bar.fb.formbuilder(cols=1, border_spacing='0px',margin_top='2px')
        if not datasourcepath:
            fb.dbSelect(dbtable=table, value='^.preview.id',lbl='!!Record',width='15em', hasDownArrow=True)
            preview_id = '.preview.id'
        else:
            preview_id = '%s.%s' %(datasourcepath,self.db.table(table).pkey)
        record_id = '^%s' %preview_id
        frame.dataRpc('.preview.renderedtemplate', self.te_getPreview,
                   _POST =True,record_id=record_id,_status='=.status',_if='compiled && _status=="preview"',_else='return new gnr.GnrBag()',
                   compiled='^.data.compiled',template_id='^.preview.letterhead_id')
        frame.center.contentPane(margin='5px').div('^.preview.renderedtemplate')

        
        
    def _te_saveButton(self,pane,table,paletteId):
        pane.slotButton('!!Save',action="""
                                    var result = genro.serverCall('te_compileTemplate',{table:table,datacontent:dc,content_css:content_css,email_meta:email_meta,varsbag:vb,parametersbag:pb},null,null,'POST');
                                    data.setItem('compiled',result.getItem('compiled'));
                                    data.setItem('metadata.email_compiled',result.getItem('email_compiled'));
                                    genro.nodeById(paletteId).publish("savechunk",{inMainResource:$1.shiftKey});""",
                            iconClass='iconbox save',paletteId=paletteId,table=table,dc='=.data.content',
                            email_meta='=.data.metadata.email',
                            content_css='=.data.content_css',
                            vb='=.data.varsbag',pb='=.data.parametersbag',data='=.data')
        
    
        
