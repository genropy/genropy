#!/usr/bin/env pythonw
# -*- coding: UTF-8 -*-
#
#  Migration
#
#  Created by Francesco Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.
#
import os
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrstring import boolean
from gnr.sql.gnrsql import GnrSqlDb
from gnr.app.gnrapp import GnrApp
from gnr.app.gnrdeploy import ProjectMaker, InstanceMaker, SiteMaker,PackageMaker, PathResolver,ThPackageResourceMaker
from time import time
from redbaron import RedBaron
from collections import OrderedDict
SYSFIELDS_DEFAULT = OrderedDict(id=True, ins=True, upd=True, 
                                    ldel=True, user_ins=False, 
                                    user_upd=False, 
                                    draftField=False, 
                                    counter=False,
                                    hierarchical=False,
                                    df=False)


MORE_ATTRIBUTES = 'cell_,format,validate_notnull,validate_case'

class GnrCustomWebPage(object):
    py_requires='public:Public,gnrcomponents/framegrid:FrameGrid,gnrcomponents/formhandler:FormHandler'


    def windowTitle(self):
        return '!!Package editor'

    def main(self, root, **kwargs):
        bc = root.rootBorderContainer(title='Package editor',datapath='main',design='sidebar')
        self.packageForm(bc.frameForm(frameCode='packageMaker',region='center',
                                        datapath='.packageform',store='memory',
                                        store_startKey='*newrecord*'))



    def dbConnectionPalette(self,pane):
        palette = pane.palettePane(paletteCode='dbConnectionPalette',title='DB Connection',
                        height='700px',width='900px',dockButton_label='Migration Tool')
        bc = palette.borderContainer(datapath='main')
        top = bc.contentPane(region='top').slotToolbar('2,fbconnection,*,connecbutton')
        fb = top.fbconnection.formbuilder(cols=7,border_spacing='3px',datapath='.connection_params')
        
        fb.filteringSelect(value='^.implementation',values='postgres,sqlite,mysql,mssql',
                            lbl='Implementation',width='7em')
        fb.textbox(value='^.dbname',lbl='Dbname',width='8em',hidden='^.implementation?=#v=="sqlite"')
        fb.textbox(value='^.host',lbl='Host',width='8em',hidden='^.implementation?=#v=="sqlite"')
        fb.textbox(value='^.port',lbl='Port',width='5em',hidden='^.implementation?=#v=="sqlite"')
        fb.textbox(value='^.user',lbl='User',width='7em',hidden='^.implementation?=#v=="sqlite"')
        fb.textbox(value='^.password',lbl='Password',width='5em',hidden='^.implementation?=#v=="sqlite"')
        fb.textbox(value='^.filename',lbl='Filename',width='50em',hidden='^.implementation?=#v!="sqlite"')
        top.connecbutton.slotButton('Connect',fire='main.connect')
        top.dataRpc('.connection_result',
                    self.getDbStructure,
                    connection_params='=.connection_params',
                    _fired='^.connect',
                    _lockScreen=True)
        center = bc.borderContainer(region='center')
        left = center.contentPane(region='left',width='300px',padding='10px',overflow='auto',splitter=True)
        left.tree(storepath='.connection_result', persist=False,
                    inspect='shift', labelAttribute='name',
                    _class='fieldsTree',
                    hideValues=True,
                    margin='6px',
                    onDrag=self.dbSourceTree_onDrag(),
                    draggable=True,
                    dragClass='draggedItem',
                    onChecked=True,
                    connect_ondblclick="""
                    var ew = dijit.getEnclosingWidget($1.target);
                    if(ew.item){
                        var attr = ew.item.attr;
                        if(attr.tag=='table'){
                            dojo.query('.dijitTreeLabel',ew.tree.domNode).forEach(function(n){genro.dom.removeClass(n,'selectedTreeNode')})
                            genro.dom.addClass(ew.labelNode,'selectedTreeNode')
                            this.setRelativeData('main.source.current_table',attr.name);
                            this.setRelativeData('main.source.current_columns',ew.item.getValue().deepCopy());
                            this.fireEvent('main.source.getPreviewData',attr.fullname);
                        }
                    }
                    """,
                    selected_fieldpath='.selpath',
                    getLabelClass="""var ct = this.sourceNode.getRelativeData('main.source.current_table');
                                        if (node.label==ct){
                                            return "selectedTreeNode"
                                        }
                                        """)
        bccenter = center.borderContainer(region='center')
        frame= bccenter.framePane(frameCode='previewGrid',region='top',height='300px',_class='pbl_roundedGroup',margin='2px')
        bar = frame.top.slotBar('2,vtitle,*',height='20px',_class='pbl_roundedGroupLabel')
        bar.vtitle.div('==_current_table?_current_table+" columns":"No table selected"',_current_table='^main.source.current_table')
        g = frame.quickGrid(value='^main.source.current_columns')
        g.column('name',width='10em',name='Name')
        g.column('dtype',width='5em',name='Dtype')
        g.column('is_pkey',width='5em',name='Pkey',dtype='B')
        g.column('indexed',width='5em',name='Indexed',dtype='B')
        g.column('unique',width='5em',name='Unique',dtype='B')
        g.column('size',width='5em',name='Size')
        frame = bccenter.roundedGroupFrame(title='Data',region='center')
        frame.center.contentPane().quickGrid(value='^main.source.previewData')
        frame.dataRpc('main.source.previewData',self.getPreviewData,
                    connection_params='=.connection_params',
                    table='^main.source.getPreviewData',
                    _frame=frame,
                    _onCalling=""" 
                    kwargs._frame.setHiderLayer(true,{message:'Loading data'})
                    """,_onResult="""
                    kwargs._frame.setHiderLayer(false);
                    """)

    def dbSourceTree_onDrag(self):
        return """var modifiers=dragInfo.modifiers;
                  var children=treeItem.getValue()
                  var result;
                  if(!children){
                     result = [treeItem.attr]
                  }else{
                    result=[];
                    children.walk(function(n){if (n.attr.checked && n.attr.tag=='column'){result.push(n.attr);}});
                  }
                  dragValues['source_columns']= result; 
                  
               """


    @public_method
    def getProjectPath(self,value=None,**kwargs):
        p = PathResolver()
        try:
            path = p.project_name_to_path(value)
            instances_path = os.path.join(path,'instances')
            packages_path = os.path.join(path,'packages')
            instances = [l for l in os.listdir(instances_path) if os.path.isfile(os.path.join(instances_path,l,'instanceconfig.xml'))]
            packages = [l for l in os.listdir(packages_path) if os.path.isdir(os.path.join(packages_path,l))]
            data = Bag()
            data['instances'] = ','.join(instances) if instances else None
            data['packages'] =','.join(packages) if packages else None
            return Bag(dict(errorcode=None,data=data))
        except Exception:
            return 'Not existing project'



    @public_method
    def makeNewProject(self,project_name=None,project_folder_code=None,language=None,base_instance_name=None,included_packages=None):
        path_resolver = PathResolver()
        base_path = path_resolver.project_repository_name_to_path(project_folder_code)

        project_maker = ProjectMaker(project_name, base_path=base_path)
        project_maker.do()
        packages = included_packages.split(',') if included_packages else []
        base_instance_name = base_instance_name or project_name
        site_maker = SiteMaker(project_name, base_path=project_maker.sites_path)
        site_maker.do()
        instance_maker = InstanceMaker(project_name, base_path=project_maker.instances_path,packages=packages)
        instance_maker.do()
        return project_name


    @public_method
    def makeNewPackage(self,package_name=None,name_long=None,is_main_package=None,project_name=None):
        path_resolver = PathResolver()
        project_path = path_resolver.project_name_to_path(project_name)
        packagespath = os.path.join(project_path,'packages')
        instances = os.path.join(project_path,'instances')
        sites = os.path.join(project_path,'sites')
        package_maker = PackageMaker(package_name,base_path=packagespath,helloworld=True,name_long=name_long)
        package_maker.do()
        for d in os.listdir(instances):
            configpath = os.path.join(instances,d,'instanceconfig.xml')
            if os.path.isfile(configpath):
                b = Bag(configpath)
                b.setItem('packages.%s' %package_name,'')
                b.toXml(configpath,typevalue=False,pretty=True)
        for d in os.listdir(sites):
            configpath = os.path.join(sites,d,'siteconfig.xml')
            if os.path.isfile(configpath):
                b = Bag(configpath)
                n = b.getNode('wsgi')
                n.attr['mainpackage'] = package_name
                b.toXml(configpath,typevalue=False,pretty=True)
        return package_name

    @public_method
    def applyPackageChanges(self,project=None,instance=None,package=None,tables=None,connection_params=None,**kwargs):
        path_resolver = PathResolver()
        project_path = path_resolver.project_name_to_path(project)
       
        if tables and not tables.isEmpty():
            for table_data in tables.values():
                filepath = os.path.join(project_path,'packages',package,'model','%s.py' %table_data['name'])
                self.makeOneTable(filepath,table_data)
        if instance:
            app = GnrApp(instance)
            destdb = app.db
            if destdb.model.check():
                destdb.model.applyModelChanges()
            if connection_params and (connection_params['dbname'] or connection_params['filename']):
                sourcedb = self.getSourceDb(connection_params)
                sourcedb.model.build()
                for table in destdb.tablesMasterIndex()[package].keys():
                    self._importTableOne(sourcedb,destdb,package,table)
                    destdb.commit()
                sourcedb.closeConnection()
                destdb.closeConnection()
        else:
            app = self.getFakeApplication(project,package)
        ThPackageResourceMaker(app,package=package,menu=True).makeResources()
        return 'ok'

    def get_redbaron(self,filepath):
        if os.path.exists(filepath):

            with open(filepath, "r") as f:
                source_code = f.read()
        else:
            source_code = """# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        pass
""" 
        red = RedBaron(source_code)
        return red

    def bagToArglist(self,arguments):
        if not arguments:
            return ''
        atlst = []
        for k,v in arguments.items():
            if isinstance(v,basestring):
                v = ("'%s'" if not "'" in v else '"%s"') %v
                atlst.append("%s=%s" %(k,v))
        return ',%s' %','.join(atlst)
            
    def makeOneTable(self,filepath=None,table_data=None):
        red = self.get_redbaron(filepath)
        config_db_node = red.find('def','config_db')
        table = table_data.pop('name')
        table_data['name_long'] = table_data['name_long'] or table
        table_data['name_plural'] = table_data['name_plural'] or table
        table_data['caption_field'] = table_data['caption_field'] or table_data['pkey']
        sysFields = table_data.pop('_sysFields')
        columns = table_data.pop('_columns')
        config_db_node[0].value = """tbl =  pkg.table('%s'%s)""" %(table,self.bagToArglist(table_data))
        if sysFields.pop('_enabled'):
            arguments = OrderedDict()
            for k,v in sysFields.items():
                if SYSFIELDS_DEFAULT.get(k) == v:
                    arguments[k] = v                
            config_db_node.append('sysFields(tbl%s)' %self.bagToArglist(arguments))
        for col in columns.values():
            relation = col.pop('_relation')
            s = self._columnPythonCode(col,relation)
            config_db_node.append(s)
        with open(filepath,'w') as f:
            f.write(red.dumps())
            
    
    def _columnPythonCode(self,col,relation=None):
        attributes = Bag()
        col = col.deepcopy()
        name = col.pop('name')
        dtype = col.pop('dtype')
        size = col.pop('size')
        name_long = col.pop('name_long')
        name_short = col.pop('name_short')
        more_attributes = col.pop('_more_attributes')

        if dtype and dtype not in ('A','T','C'):
            attributes['dtype'] = dtype
        if size:
            attributes['size'] = size
        attributes.setItem('name_long', name_long or name,localized=True)
        if name_short:
            attributes.setItem('name_short', name_short,localized=True)
        attributes.update(col)
        if more_attributes:
            for key,dtype,value in more_attributes.digest('#v.attribute_key,#v.attribute_dtype,#v.attribute_value'):
                dtype = dtype or 'T'
                if value not in (None,''):
                    attributes[key] = self.catalog.fromText(value,dtype)
        atlst = []
        for k,v,localized in attributes.digest('#k,#v,#a.localized'):
            if v in (None,''):
                continue
            if isinstance(v,basestring):
                v = ("'%s'" if not "'" in v else '"%s"') %v
            atlst.append("%s=%s" %(k,v))
        relationCode = ''
        if relation and relation['relation']:
            relationCode = '.%s' %self._relationPythonCode(relation)

        coltype = 'column'
        if attributes['sql_formula'] or attributes['select'] or attributes['exists']:
            coltype = 'formulaColumn'
        elif attributes['relation_path']:
            coltype = 'aliasColumn'
        elif attributes['pymethod']:
            coltype = 'pyColumn'

        return "tbl.%s('%s', %s)%s" % (coltype,name, ', '.join(atlst),relationCode)

    def _relationPythonCode(self,relation):
        relpath = relation.pop('relation')
        r = relpath.split('.')
        if len(r)==3:
            pkg,table,id = r
            if pkg == 'main':
                relpath = '%s.%s' %(table,id)
        relation_name = relation.pop('relation_name')
        one_one = relation.pop('one_one')
        foreignkey = relation.pop('foreignkey')

        attributes = Bag()
        if relation_name:
            attributes['relation_name'] = relation_name
        if foreignkey:
            attributes['mode'] = 'foreignkey'
        if one_one:
            attributes['one_one'] = '*' if not relation_name else True
        for k, v in relation.items():
            if v is not None:
                attributes[k] = v
        atlst = []
        for k,v in attributes.items():
            if isinstance(v,basestring):
                if "'" in v:
                    v = '"%s"' %v
                else:
                    v = "'%s'" %v
            atlst.append("%s=%s" %(k,v))
        return """relation('%s',%s)"""  %(relpath,', '.join(atlst))

    def packageForm(self,form):
        bar = form.top.slotToolbar('2,fbinfo,10,dbConnectionPalette,10,connectionTpl,*,applyChanges,semaphore,5')
        bar.connectionTpl.div('^main.connectionTpl')
        bar.dataController("""
                var implementation = connection_params.getItem('implementation');
                var filename = connection_params.getItem('filename');
                var dbname = connection_params.getItem('dbname');
                var r = ''
                var filepath = connection_params.getItem('filename');
                if(implementation=='sqlite' && filepath){
                    var f = filepath.split(/\//);
                    r = '<b>sqlite:</b>'+f[f.length-1];
                }else if(implementation && connection_params.getItem('dbname')){
                    r = dataTemplate('<b>$implementation:</b>$dbname',connection_params)
                }
                SET main.connectionTpl = r;
                """,connection_params='^main.connection_params',_onStart=True,color='#444')
        self.dbConnectionPalette(bar.dbConnectionPalette)
        bar.applyChanges.slotButton('Apply',action="""if(this.form.isValid()){
                FIRE #FORM.makePackage;
            }else{
                genro.dlg.alert('Invalid data','Error');
            }""")
        bar.dataRpc('dummy',self.applyPackageChanges,project='=#FORM.record.project_name',package='=#FORM.record.package_name',
                    instance='=#FORM.record.selected_instance',connection_params='=main.connection_params',
                    tables='=#FORM.record.tables',
                    _onCalling="""
                        var tables_to_send = new gnr.GnrBag();
                        kwargs.tables.forEach(function(n){
                            if(n.attr._loadedValue || n._value.getNodeByAttr('_loadedValue')){
                                tables_to_send.setItem(n.label,n._value.deepCopy(),n.attr);
                            }
                        });
                        kwargs.tables=tables_to_send;
                    """,
                    _fired='^#FORM.makePackage',_onResult='genro.dlg.alert("Package Done","Message");',
                    _lockScreen=True,timeout=0)
        bar.dataRpc('dummy',self.importTable,package='=#FORM.record.package_name',
                    instance='=#FORM.record.selected_instance',
                    subscribe_import_table=True,connection_params='=main.connection_params')

        fb = bar.fbinfo.formbuilder(cols=5,border_spacing='3px',datapath='.record')
        fb.textbox(value='^.project_name',validate_onAccept='SET .package_name=null;',validate_onReject='SET .package_name = null;',
                    validate_notnull=True,
                    validate_remote=self.getProjectPath,lbl='Project')
        p = PathResolver()
        fb.data('projectFolders',','.join(p.gnr_config['gnr.environment_xml.projects'].keys()))
        fb.dataRpc('dummy',self.makeNewProject,subscribe_makeNewProject=True,
                    _onResult='PUT .project_name=null; SET .project_name=result')
        fb.button('New Project',action="""
            genro.publish('makeNewProject',{project_name:project_name,project_folder_code:project_folder_code,
                                            language:language,base_instance_name:base_instance_name,
                                            included_packages:included_packages});
            """,project_name='=.project_name',
                    ask=dict(title='New Project',fields=[
                        dict(name='project_name',lbl='Project name'),
                        dict(name='project_folder_code',lbl='Folder',wdg='filteringSelect',values='^projectFolders'),
                        dict(name='language',lbl='Language',wdg='filteringSelect',values='EN:English,IT:Italian'),
                        dict(name='base_instance_name',lbl='Instance name'),
                        dict(name='included_packages',lbl='Packages',wdg='simpleTextArea'),
                        ]),included_packages='gnrcore:sys,gnrcore:adm',language='EN',project_folder_code='',
                    base_instance_name='=.project_name')
        fb.filteringSelect(value='^.package_name',validate_notnull=True,lbl='Package',
                    validate_onAccept='FIRE #FORM.resetPackageData; FIRE #FORM.loadPackage = value;',validate_onReject="""FIRE #FORM.resetPackageData;""",
                    values='^.packages',
                    width='7em')
        fb.dataController("""
                    SET #FORM.current_columns = null;
                    SET #FORM.record.tables = null;
                    """,_fired='^#FORM.resetPackageData')
        fb.dataRpc('#FORM.record.tables',self.loadPackageTables,package='^#FORM.loadPackage',
                project='=#FORM.record.project_name',
                _if='project&&package',_else='return gnr.GnrBag();')
        fb.button('New Package',action="""
            genro.publish('makeNewPackage',{package_name:package_name,project_name:project_name,
                                            is_main_package:is_main_package,name_long:name_long});
            """,package_name='=.package_name',project_name='=.project_name',
                    ask=dict(title='New Package',fields=[
                        dict(name='package_name',lbl='Package name'),
                        dict(name='name_long',lbl='Name long'),
                        dict(name='is_main_package',label='Is main package',wdg='checkbox'),
                        ]))
        fb.filteringSelect(value='^.selected_instance',lbl='Instance',values='^.instances')
        fb.dataRpc('dummy',self.makeNewPackage,subscribe_makeNewPackage=True,
                    _onResult='PUT .package_name=null; SET .package_name=result')

        self.packageGrids(form.center.borderContainer())

    def tables_struct(self,struct):
        r = struct.view().rows()
        r.cell('legacy_name',width='10em',name='Legacy Name',hidden='^main.connectionTpl?=!#v')
        r.cell('name',width='10em',name='Name')
        r.cell('pkey',width='10em',name='Pkey')
        r.cell('name_long',width='20em',name='Name long')
        r.cell('name_plural',width='20em',name='Name plural')
        r.cell('caption_field',width='20em',name='Caption field')
        r.cell('status',width='20em',name='Import status')

    def columns_struct(self,struct):
        r = struct.view().rows()
        r.cell('legacy_name',width='10em',name='Legacy Name',hidden='^main.connectionTpl?=!#v')
        r.cell('name',width='10em',name='Name',edit=True)
        r.cell('dtype',width='5em',name='Dtype',edit=dict(tag='filteringSelect',values='T:Text,I:Int,N:Decimal,B:Bool,D:Date,DH:Timestamp,X:Bag'))
        r.cell('size',width='5em',name='Size',edit=True)
        r.cell('group',width='5em',name='Group',edit=True)
        r.cell('name_long',width='20em',name='Name long',edit=True)
        r.cell('name_short',width='10em',name='Name short',edit=True)
        r.cell('indexed',width='5em',name='Indexed',edit=True,dtype='B')
        r.cell('unique',width='5em',name='Unique',edit=True,dtype='B')
        r.cell('_more_attributes',width='20em',name='More attributes',edit=True,editOnOpening=""" 
                                        var more_attributes = rowData.getItem(field);
                                        genro.publish('edit_more_attributes',{more_attributes:more_attributes,rowIndex:rowIndex})
                                        return false;
                                    """)

        r.cell('_relation',width='20em',name='Relation',edit=True,
                     editOnOpening="""var relation = rowData.getItem(field);
                                    if(relation){
                                        relation = relation.deepCopy();
                                    }
                                    genro.publish('edit_relation',{relation:relation,rowIndex:rowIndex})
                                    return false;
                                    """)
    def relationEditorDialog(self,bc):
        dlg = bc.dialog(title='Relation',
                        subscribe_edit_relation="""this.widget.show()
                                                   this.setRelativeData('.data',$1.relation);
                                                   this.setRelativeData('.rowIndex',$1.rowIndex)
                                                """,datapath='#FORM.relationEditor')
        frame = dlg.framePane(height='300px',width='600px')
        pane = frame.center.contentPane()
        fb = pane.formbuilder(cols=2,datapath='.data')
        fb.textbox(value='^.relation',lbl='Relation')
        fb.textbox(value='^.relation_name',lbl='Relation name')
        fb.checkbox(value='^.foreignkey',label='Foreignkey')
        fb.filteringSelect(value='^.onDelete',lbl='onDelete',values='raise,cascade,setnull')
        fb.filteringSelect(value='^.onDelete_sql',lbl='onDelete(sql)',values='raise,cascade,setnull')
        fb.filteringSelect(value='^.onUpdate',lbl='onUpdate',values='cascade,raise')
        fb.filteringSelect(value='^.onUpdate_sql',lbl='onUpdate(sql)',values='cascade,raise')
        fb.textbox(value='^.one_name',lbl='One name')
        fb.textbox(value='^.many_name',lbl='Many name')
        fb.checkbox(value='^.deferred',label='Deferred')
        fb.checkbox(value='^.one_one',label='One one')
        bar = frame.bottom.slotBar('*,cancel,10,confirm,2',margin_bottom='2px',_class='slotbar_dialog_footer')
        bar.cancel.slotButton('Cancel',action="dlg.hide()",dlg=dlg.js_widget)
        bar.confirm.slotButton('Confirm',action="""griddata.setItem('#'+rowIndex+'._relation',data.deepCopy());
                                                    dlg.hide()""",
                                        dlg=dlg.js_widget,
                                        griddata='=#FORM.current_columns',
                                        rowIndex='=.rowIndex',
                                        data='=.data')


    def moreAttributesDialog(self,bc):
        dlg = bc.dialog(title='More attributes',
                        subscribe_edit_more_attributes="""this.widget.show()
                                                   this.setRelativeData('.data',$1.more_attributes);
                                                   this.setRelativeData('.rowIndex',$1.rowIndex)
                                                """,datapath='#FORM.moreAttributes')
        def struct(struct):
            r = struct.view().rows()
            r.cell('attribute_key',name='Key',edit=dict(tag='ComboBox',values=MORE_ATTRIBUTES),width='10em')
            r.cell('attribute_dtype',name='Dtype',edit=dict(tag='filteringSelect',
                                                            values='T:Text,B:Bool,I:Int,N:Decimal'),width='10em')
            r.cell('attribute_value',name='Value',edit=True,width='10em')

        frame = dlg.bagGrid(height='200px',width='400px',storepath='#FORM.moreAttributes.data',struct=struct)
        
        bar = frame.bottom.slotBar('*,cancel,10,confirm,2',margin_bottom='2px',_class='slotbar_dialog_footer')
        bar.cancel.slotButton('Cancel',action="dlg.hide()",dlg=dlg.js_widget)
        bar.confirm.slotButton('Confirm',action="""griddata.setItem('#'+rowIndex+'._more_attributes',data.deepCopy());
                                                    dlg.hide()""",
                                        dlg=dlg.js_widget,
                                        griddata='=#FORM.current_columns',
                                        rowIndex='=.rowIndex',
                                        data='=.data')

    def packageGrids(self,bc):
        self.relationEditorDialog(bc)
        self.moreAttributesDialog(bc)
        tablesframe = bc.contentPane(region='top',height='200px',splitter=True).bagGrid(frameCode='tables',title='Tables',
                                                storepath='#FORM.record.tables',
                                                datapath='#FORM.tablesFrame',
                                                struct=self.tables_struct,
                                                grid_multiSelect=False,
                                                grid_subscribe_update_import_status="""
                                                    var b = this.widget.storebag();
                                                    var r = b.getItem($1.table);
                                                    if(!r){
                                                        return;
                                                    }
                                                    r.setItem('status',$1.status);
                                                    """,
                                                pbl_classes=True,margin='2px',
                                                addrow=True,delrow=True)
        tablesgrid = tablesframe.grid
        tablesgrid.dragAndDrop('source_columns')
        tablesgrid.dataController("""
            var tblpars,tableNode,tblVal,columnNode,colVal,colpars,columns,pkeycol,status,col_legacy_name;
            data.forEach(function(col){
                    tblpars = objectExtract(col,'table_*');
                    var tblname = tblpars['name'].toLowerCase();
                    tableNode = tables.getNode(tblname);

                    if(!tableNode){
                        pkeycol = tblpars.pkey.toLowerCase()
                        status = ''; //dataTemplate(tpl,{tblname:tblname});
                        tblVal = new gnr.GnrBag({name:tblname,legacy_name:tblpars['fullname'],
                                                pkey:pkeycol,
                                                _columns:new gnr.GnrBag(),
                                                status:status});
                        tableNode = tables.setItem(tblname,tblVal);
                    }
                    columns = tableNode.getValue().getItem('_columns');
                    var colname = col.name.toLowerCase()
                    columnNode =  columns.getNode(colname);
                    if(!columnNode){
                        var relate_to = col.relate_to?col.relate_to.toLowerCase():null
                        col_legacy_name = col.name;
                        if(col_legacy_name=='_multikey'){
                            col_legacy_name = null;
                        }
                        columnNode = columns.setItem(colname,new gnr.GnrBag({name:colname,legacy_name:col_legacy_name,
                                                                name_long:stringCapitalize(col.name),dtype:col.dtype,size:col.size,
                                                                indexed:col.indexed,unique:col.unique}));
                        if(relate_to){
                            columnNode._value.setItem('_relation',new gnr.GnrBag({relation:relate_to,relation_name:null,
                                                                                  onDelete:'raise',one_name:null,
                                                                                  many_name:null,deferred:false}));
                        }
                    }
                })
            """,data='^.dropped_source_columns',dropInfo='=.droppedInfo_source_columns',
                tables='=#FORM.record.tables',
                tpl="""<a style="cursor:pointer; text-align:center;" href="javascript:genro.publish('import_table',{table:'$tblname'})">import</a>""")

        tablesform = tablesgrid.linkedForm(frameCode='tableform',
                                 datapath='.tableform',loadEvent='onSelected',
                                 childname='form',
                                 formRoot=bc.contentPane(region='center',overflow='hidden'),
                                 store='memory',
                                 form_locked=True,
                                 form_parentLock=False,
                                 store_pkeyField='name')
        self.tablesForm(tablesform)

    def tablesForm(self,form):
        bar = form.top.slotToolbar('2,navigation,5,formtitle,*,form_locker,semaphore,2')
        bar.formtitle.div('^.record.name',color='#444',font_weight='bold')
        form.store.attributes.update(autoSave=True)
        form.dataController("this.form.setLocked(true)",_onStart=True)
        form.dataController("genro.dlg.alert('Wrong info','Table has wrong data');",save_failed='^#FORM.controller.save_failed')
        bc = form.center.borderContainer()
        top = bc.contentPane(datapath='.record',region='top')
        fb = top.formbuilder(cols=3)
        fb.dataFormula('#FORM.columnsValues',"""columns.values().map(function(v){return v.getItem('name')}).join(',')""",
                        columns='^._columns',_if='columns && columns.len()',_else='null')
        fb.textbox(value='^.name',lbl='Name',validate_notnull=True,validate_case='l')
        fb.textbox(value='^.name_long',lbl='Name Long')
        fb.textbox(value='^.name_plural',lbl='Name Plural')
        fb.comboBox(value='^.pkey',lbl='Pkey',validate_notnull=True,values='^#FORM.columnsValues')
        fb.comboBox(value='^.caption_field',lbl='Caption field',values='^#FORM.columnsValues')       
        fb.checkbox(value='^.lookup',lbl='Lookup')

        fb.button('Handle Sysfields') 
        columnsframe = bc.contentPane(region='center').bagGrid(frameCode='columns',title='Columns',
                                                        datapath='#FORM.columnsGrid',
                                                    storepath='#FORM.record._columns',
                                                    struct=self.columns_struct,
                                                    pbl_classes=True,margin='2px',
                                                    grid_selfDragRows=True,
                                                    addrow=True,delrow=True)


    def getSourceDb(self,connection_params=None):
        config = self.site.gnrapp.config
        dbname=connection_params['dbname'] or connection_params['filename']
        if connection_params['implementation']!='sqlite':
            connection_params['host'] = connection_params['host'] or config['db?host'] or 'localhost'
            connection_params['user'] = connection_params['user'] or config['db?user']
            connection_params['password'] = connection_params['password'] or config['db?password']
            connection_params['port'] = connection_params['port'] or config['db?port']

        externaldb = GnrSqlDb(implementation=connection_params['implementation'],
                            dbname=dbname,
                            host=connection_params['host'],user=connection_params['user'],
                            password = connection_params['password'])
        externaldb.importModelFromDb()

        return externaldb

    @public_method
    def getDbStructure(self,connection_params=None):
        externaldb = self.getSourceDb(connection_params)
        src = externaldb.model.src
        result = Bag()
        for pkg in src['packages'].keys():
            pkgval = Bag()
            result.setItem(pkg, pkgval,name=pkg,checked=False)
            tables = src['packages'][pkg]['tables']
            if not tables:
                continue
            for table,tblattr,tblval in tables.digest('#k,#a,#v'):
                tblattr = dict(tblattr)
                tblattr['checked'] = False
                tblattr['name'] = table
                tableval = Bag()
                pkgval.setItem(table,tableval,**tblattr)
                for column,colattr,colval in tblval['columns'].digest('#k,#a,#v'):
                    cv = dict(colattr)
                    for t,v in tblattr.items():
                        cv['table_%s' %t] = v
                    cv['checked'] = False
                    cv['name'] = column
                    if colval:
                        relnode = colval.getNode('relation')
                        cv['relate_to'] = relnode.attr['related_column']
                    tableval.setItem(column,None,**cv)
                if tblval['indexes']:
                    for column,unique in tblval['indexes'].digest('#a.columns,#a.unique'):
                        n = tableval.getNode(column)
                        if n:
                            n.attr['is_pkey'] = column == tblattr['pkey']
                            n.attr['indexed'] = True
                            n.attr['unique'] = boolean(unique)
        return result

    @public_method
    def importTable(self,table=None,instance=None,package=None,connection_params=None):
        sourcedb = self.getSourceDb(connection_params)
        sourcedb.model.build()
        destdb = GnrApp(instance).db
        self._importTableOne(sourcedb,destdb,package,table,thermo=True)
        destdb.commit()
        sourcedb.closeConnection()
        destdb.closeConnection()

    def _importTableOne(self,sourcedb,destdb,package,table):
        desttable = destdb.table('%s.%s' %(package,table))
        if desttable.query().count():
            return
        sourcetable = sourcedb.table(desttable.attributes['legacy_name'])
        columns = []
        for k,c in desttable.columns.items():
            legacy_name = c.attributes.get('legacy_name')
            if legacy_name:
                columns.append(" $%s AS %s " %(legacy_name,k))
        columns = ', '.join(columns)
        f = sourcetable.query(columns=columns,addPkeyColumn=False).fetch()
        progressDetail = dict(status='Importing records',total=len(f),current=0)
        t0 = time()
        for i,r in enumerate(f):
            desttable.insert(r)
            if time()-t0>1:
                t0 = time()
                progressDetail['current'] = i
                status = r""" %(status)s <progress style='width:12em' max='%(total)s' value='%(current)s'></progress>""" %progressDetail
                self.clientPublish('update_import_status',status=status,table=table)
        self.clientPublish('update_import_status',status='<b>Imported</b>',table=table)

    @public_method
    def getPreviewData(self,table=None,connection_params=None,**kwargs):
        sourcedb = self.getSourceDb(connection_params)
        sourcedb.model.build()
        result = Bag()
        tbl = sourcedb.table(table)
        cols = ','.join(['$%s' %c.name for c in sourcedb.table(table).columns.values() if c.name!='_multikey'])
        f = tbl.query(columns=cols,addPkeyColumn=False,limit=200).fetch()
        sourcedb.closeConnection()
        for i,r in enumerate(f):
            result['r_%s' %i] = Bag(r)
        return result

    def getFakeApplication(self,project,package):
        custom_config = Bag()
        pkgcode='%s:%s' %(project,package)
        custom_config.setItem('packages.%s' %pkgcode,None,pkgcode=pkgcode)
        return GnrApp(custom_config=custom_config)


    def getPackagePath(self,project,package):
        path_resolver = PathResolver()
        project_path = path_resolver.project_name_to_path(project)
        return os.path.join(project_path,'packages',package)


    @public_method
    def loadPackageTables(self,package=None,project=None):
        result = Bag()
        models_path = os.path.join(self.getPackagePath(project,package),'model')
        for m in os.listdir(models_path):
            tablename,ext = os.path.splitext(m)
            if ext!='.py':
                continue
            red = self.get_redbaron(os.path.join(models_path,m))
            config_db = red.find('def','config_db')
            targs,tkwargs = self.parsBaronNodeCall(config_db.find('name','table').parent[2])
            tablevalue = Bag(tkwargs)
            tablevalue['name'] = tablename
            result[tablename] = tablevalue
            tablevalue['_sysFields'] =self.handleSysFields(red)
            columnsvalue = Bag()
            tablevalue['_columns'] = columnsvalue
            for colNode in red.find_all('name','column'):
                cbag = self._loadColumnBag(colNode)
                cbag['tag'] = 'column'
                columnsvalue[cbag['name']] = cbag
            for colNode in red.find_all('name','aliasColumn'):
                cbag = self._getColBag(colNode,'relation_path')
                cbag['tag'] = 'aliasColumn'
                columnsvalue[cbag['name']] = cbag
            for colNode in red.find_all('name','formulaColumn'):
                cbag = self._getColBag(colNode,'sql_formula')
                cbag['tag'] = 'formulaColumn'
                columnsvalue[cbag['name']] = cbag
            for colNode in red.find_all('name','pyColumn'):
                cbag = self._getColBag(colNode,'py_method')
                cbag['tag'] = 'pyColumn'
                columnsvalue[cbag['name']] = cbag
        return result

    def handleSysFields(self,red):
        sysFieldBaronNode = red.find('name','sysFields')
        if not sysFieldBaronNode:
            return Bag()
        result = Bag(SYSFIELDS_DEFAULT) #counter_kwargs=None
        result['_enabled'] = True
        args,kwargs = self.parsBaronNodeCall(sysFieldBaronNode.parent[2])
        for k,v in kwargs.items():
            result[k] = v
        return result

    def _getColBag(self,node,firstArg=None,firstArgDefault=None):
        cbag = Bag()
        p = node.parent
        cargs,ckwargs = self.parsBaronNodeCall(p[2])
        colname = cargs[0]
        cbag = Bag()
        cbag['name'] = colname
        if len(cargs)>1:
            fval = cargs[1]
        else:
            fval = ckwargs.pop(firstArg,firstArgDefault)
        cbag[firstArg] = fval
        for k,v in ckwargs.items():
            cbag[k] = v
        return cbag

    def parsBaronNodeCall(self,node):
        args = []
        kwargs = OrderedDict()
        for argNode in node.find_all('call_argument'):
            key = argNode.target.value if argNode.target else None
            value = argNode.value.value
            argtype = argNode.value.type
            if argtype=='string':
                value = value.strip("'") if "'" in value else value.strip('"')
            elif value in ('True','False'):
                value = boolean(value)
            elif hasattr(value,'value'):
                value = Bag(self.parsBaronNodeCall(value)[1])
            if not key:
                args.append(value)
            else:
                kwargs[key] = value
        return args,kwargs

    def _loadColumnBag(self,colNode,aliasColumn=False):
        cbag = self._getColBag(colNode,'dtype','T')
        p = colNode.parent
        if p.find('name','relation'):
            _relation = Bag()
            rargs,rkwargs = self.parsBaronNodeCall(p[4])
            mode = rkwargs.pop('mode',None)
            _relation['relation'] = rargs[0]
            _relation['foreignkey'] = mode=='foreignkey'
            for k,v in rkwargs.items():
                _relation[k] = v
            cbag['_relation'] = _relation
        return cbag


    @public_method
    def loadPackageTables_old(self,package=None,project=None):
        app = self.getFakeApplication(project,package)
        result = Bag()
        package_path = self.getPackagePath(project,package)
        for tablename,tblobj in app.db.packages[package].tables.items():
            red = self.get_redbaron(os.path.join(package_path,'model','%s.py' %tablename))
            targs,tkwargs = self.parsBaronNodeCall(red.find('name','table'))
            tablevalue = Bag(tkwargs)
            tablevalue['name'] = tablename
            result[tablename] = tablevalue
            columnsvalue = Bag()
            tablevalue['_columns'] = columnsvalue
            tablevalue['_sysFields'] =self.handleSysFields(red)
            for colname,colobj in tblobj.columns.items():
                cbag = self._columnVal(colname,colobj)
                if not cbag:
                    continue
                columnsvalue[colname] = cbag
                joiner = colobj.relatedColumnJoiner()
                if joiner and joiner.get('mode')=='O':
                    _relation = Bag()
                    _relation['foreignkey'] = joiner.get('foreignkey')
                    _relation['relation_name'] = joiner.get('relation_name')
                    _relation['relation'] = joiner.get('one_relation')
                    _relation['onDelete'] = joiner.get('onDelete')
                    _relation['onDelete_sql'] = joiner.get('onDelete_sql')
                    _relation['onUpdate'] = joiner.get('onUpdate')
                    _relation['onUpdate_sql'] = joiner.get('onUpdate_sql')
                    cbag['_relation'] = _relation
            for colname,colobj in tblobj.virtual_columns.items():
                cbag = self._columnVal(colname,colobj)
                if not cbag:
                    continue
                columnsvalue[colname] = cbag
                #print x
        return result

    def _columnVal(self,colname,colobj):
        cbag = Bag()
        cattr = dict(colobj.attributes)
        _sysfield = cattr.pop('_sysfield',None)
        if _sysfield:
            return
        cbag['name'] = colname
        for attrname,attrvalue in cattr.items():
            if attrname in ('name','dtype','size','group','name_long','name_short','indexed','unique'):
                cbag[attrname] = cattr.pop(attrname)
        more_attributes = Bag()
        for attrname,attrvalue in cattr.items():
            more_attributes[attrname] = Bag(dict(attribute_key=attrname,attribute_value=attrvalue,dtype=self.catalog.names[type(attrvalue)]))
        cbag['_more_attributes'] = more_attributes
        return cbag

