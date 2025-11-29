# -*- coding: utf-8 -*-

# tpleditor.py
# Created by Francesco Porcari on 2011-06-22.
# Copyright (c) 2011 Softwell. All rights reserved.

import json
from gnr.core.gnrdecorator import public_method
from gnr.sql.gnrsqlmigration import SqlMigrator
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
import gnr.sql
from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.pgutils import PgDbUtils

class GnrCustomWebPage(object):
    py_requires="public:Public"

    def main(self,root, **kwargs):
        bc = root.borderContainer(datapath='main')
        self.dbSelectorPane(bc,region='top',datapath='.selector',margin='2px')
        self.dbViewersTabs(bc,region='center',margin='2px')
    
    def dbSelectorPane(self,parent,**kwargs):
        pane = parent.contentPane(**kwargs)
        fb = pane.formlet(cols=7)
        useable_implementations = ','.join(gnr.sql.ADAPTERS_BY_CAPABILITY['MIGRATIONS']) + ',gnrinstance'
        fb.filteringSelect(value='^.implementation',values=useable_implementations,
                            lbl='Implementation',width='7em')
        fb.dataController("""
                          let hidden_uploader = true;
                          let hidden_dbpars = true;
                          let hidden_instance_name = true;
                          if (implementation=='gnrinstance'){
                             hidden_instance_name = false;
                          }else if(implementation=='sqlite'){
                             hidden_uploader = false;
                          }else if(implementation){
                             hidden_dbpars = false;
                          }
                          SET .hidden_instance_name = hidden_instance_name;
                          SET .hidden_dbpars = hidden_dbpars;
                          SET .hidden_uploader = hidden_uploader;
                          """,implementation='^.implementation',_onStart=True)
        fb.textbox(value='^.pars.instance_name',lbl='Instance name',hidden='^.hidden_instance_name')
        fb.textbox(value='^.pars.conn.dbname',lbl='Dbname',width='8em',hidden='^.hidden_dbpars')
        fb.textbox(value='^.pars.conn.host',lbl='Host',width='8em',hidden='^.hidden_dbpars')
        fb.textbox(value='^.pars.conn.port',lbl='Port',width='5em',hidden='^.hidden_dbpars')
        fb.textbox(value='^.pars.conn.user',lbl='User',width='7em',hidden='^.hidden_dbpars')
        fb.textbox(value='^.pars.conn.password',lbl='Password',width='5em',hidden='^.hidden_dbpars')
        fb.data('.pars.sqlitepath','page:sqliteSource')
        fb.div(hidden='^.hidden_uploader',lbl='Sqlite file').dropUploader(nodeId='exdbSqliteUploader',
            uploadPath='page:sqliteSource',
            height = '16px', width='30em',
            line_height='15px',font_size='14px',
            label= '!![en]Drop sqlite file here or do double click to browse your disk',
            )
        fb.button('Connect').dataRpc('main.structures',self.getMigrationBag,
                                     instance_name='=.pars.instance_name',
                                     connection_pars ='=.pars.conn',
                                     implementation='=.pars.implementation',
                                     applyChanges='^main.applyChanges',
                                     _lockScreen=True)
        fb.dataRpc(self.runDbUtils,subscribe_dbUtilsRun=True,
                   instance_name='=.pars.instance_name',
                                     connection_pars ='=.pars.conn',
                                     implementation='=.pars.implementation',
                                     _lockScreen=True,
                    _onResult="""
                        genro.setData('main.dbutils.'+kwargs.methodname+'.result',result)
                    """)

        
    def dbViewersTabs(self,parent,**kwargs):
        tc = parent.tabContainer(**kwargs)

        bc = tc.borderContainer(title='Structure',datapath='.structures')
        bc.roundedGroupFrame(region='bottom',height='50%',title='Orm',splitter=True).bagEditor(storepath='.orm_clean')
        bc.roundedGroupFrame(region='center',title='SQL').bagEditor(storepath='.sql_clean')

        self.unusedElementsPane(tc,title='Unused',datapath='.unused',
                                hidden='^main.structures.unused_elements?=!#v || #v.len()==0')
        self.dbUtilsPane(tc,title='Utils',datapath='.dbutils')

        bc = tc.borderContainer(title='JSON Structures',datapath='.structures')
        bc.roundedGroupFrame(region='center',width='50%',title='SQL').tree(storepath='.sql')
        bc.roundedGroupFrame(region='right',width='50%',title='Orm').tree(storepath='.orm')
        frame = tc.framePane(title='Sql Commands')
        frame.codemirror(value='^.structures.sql_commands',
                                                        config_lineNumbers=True,config_mode='sql',
                                config_indentUnit=4,config_keyMap='softTab',
                                config_addon='search',
                                height='100%',
                                config_gutters=["CodeMirror-linenumbers"])
        bar = frame.top.slotToolbar('*,applyChanges,5')
        bar.applyChanges.slotButton('Apply',fire='main.applyChanges')

    def unusedElementsPane(self,parent,**kwargs):
        frame = parent.frameGrid(frameCode='unusedGrid',
                                 storepath='main.structures.unused_elements',
                                 struct=self.unusedGridStruct,
                                 pkey='_pkey',
                                 checkboxColumn=True,
                                 **kwargs)
        bar = frame.top.slotToolbar('5,generateDrop,*,searchOn,5')
        bar.generateDrop.slotButton('Generate DROP Commands').dataRpc(
            'main.unused.drop_commands',self.generateDropCommands,
            selected_elements='=.checked',
            _lockScreen=True
        )
        bottom = frame.bottom.contentPane(height='40%',splitter=True,padding='5px')
        bottom.div('DROP Commands:',font_weight='bold',margin_bottom='5px')
        bottom.codemirror(value='^main.unused.drop_commands',
                         config_lineNumbers=True,config_mode='sql',
                         config_indentUnit=4,
                         height='100%',readOnly=True)

    def unusedGridStruct(self,struct):
        r = struct.view().rows()
        r.cell('entity_type',name='Type',width='8em')
        r.cell('schema_name',name='Schema',width='8em')
        r.cell('table_name',name='Table',width='12em')
        r.cell('entity_name',name='Name',width='15em')
        r.cell('sql_name',name='SQL Name',width='15em')
        r.cell('details',name='Details',width='20em')
        return struct

    def dbUtilsPane(self,parent,**kwargs):
        tc = parent.tabContainer(**kwargs)
        pane = tc.contentPane(title='PgUtils',overflow='auto')
        for methodname,desc in PgDbUtils.list_pgutils('pgutils').items():
            g = pane.gridbox(cols=3,datapath=f'.{methodname}',margin='4px',
                             border='2px solid silver',justify_content='center',rounded=8)
            g.div(methodname,padding_left='10px',font_weight='bold')
            g.div(desc,font_style='italic')
            g.button('Run').dataController("genro.publish('dbUtilsRun',{methodname:methodname});",methodname=methodname)
            g.div(colspan=3,border_top='1px solid silver',
                  min_height='100px',padding='5px').quickGrid(value='^.result')

        pane = tc.contentPane(title='PgStats',overflow='auto')
        for methodname,desc in PgDbUtils.list_pgutils('pgstats').items():
            g = pane.gridbox(cols=3,datapath=f'.{methodname}',margin='4px',
                             border='2px solid silver',justify_content='center',rounded=8)
            g.div(methodname,padding_left='10px',font_weight='bold')
            g.div(desc,font_style='italic')
            g.button('Run').dataController("genro.publish('dbUtilsRun',{methodname:methodname});",methodname=methodname)
            g.div(colspan=3,border_top='1px solid silver',
                  min_height='100px',padding='5px').quickGrid(value='^.result')

    @public_method
    def getMigrationBag(self,instance_name=None,implementation=None,connection_pars=None,applyChanges=False):
        db = self.getDbFromPars(instance_name=instance_name,implementation=implementation,connection_pars=connection_pars)
        extensions = None
        if instance_name:
            extensions = db.application.config['db?extensions']
        mig = SqlMigrator(db,ignore_constraint_name=True,extensions=extensions)
        result = Bag()
        mig.prepareMigrationCommands()
        changes = mig.getChanges()
        if changes and applyChanges:
            mig.applyChanges()
            return self.getMigrationBag(instance_name=instance_name,implementation=implementation,connection_pars=connection_pars)
        cleanModel = mig.jsonModelWithoutMeta()
        result['sql'] = Bag(mig.sqlStructure)
        result['orm'] = Bag(mig.ormStructure)
        result['orm_clean'] = Bag(cleanModel['orm'])
        result['sql_clean'] = Bag(cleanModel['sql'])
        result['diff'] = mig.getDiffBag()
        result['commands_tree'] = Bag(mig.commands)
        result['sql_commands'] = changes
        result['unused_elements'] = self.extractUnusedElements(mig)
        return result

    def extractUnusedElements(self,mig):
        """Estrae elementi nel DB che non sono definiti nell'ORM"""
        result = Bag()
        row_idx = 0
        for reason,kw in mig.dictDifferChanges():
            if reason != 'removed':
                continue
            item = kw['item']
            entity_type = item.get('entity')
            if entity_type not in ('index','relation','constraint'):
                continue
            schema_name = item.get('schema_name','')
            table_name = item.get('table_name','')
            entity_name = item.get('entity_name','')
            attributes = item.get('attributes',{})
            sql_name = attributes.get('index_name') or attributes.get('constraint_name') or entity_name
            if entity_type == 'index':
                columns = attributes.get('columns',{})
                if isinstance(columns,dict):
                    details = f"columns: {', '.join(columns.keys())}"
                else:
                    details = f"columns: {columns}"
            elif entity_type == 'relation':
                details = f"-> {attributes.get('related_schema','')}.{attributes.get('related_table','')}"
            else:
                details = attributes.get('constraint_type','')
            result.setItem(f'r_{row_idx}',None,
                          entity_type=entity_type,
                          schema_name=schema_name,
                          table_name=table_name,
                          entity_name=entity_name,
                          sql_name=sql_name,
                          details=details,
                          _pkey=f'{schema_name}.{table_name}.{entity_type}.{sql_name}')
            row_idx += 1
        return result
    
    
    def getDbFromPars(self,instance_name=None,implementation=None,connection_pars=None):
        if instance_name:
            db = GnrApp(instance_name).db
        else:
            db = GnrSqlDb(
                implementation=implementation,
                host=connection_pars['host'],
                port=connection_pars['port'],
                dbname=connection_pars['dbname'],
                user=connection_pars['user'],
                password=connection_pars['password']
            )
        return db

    @public_method
    def generateDropCommands(self,selected_elements=None):
        """Genera comandi DROP per gli elementi selezionati"""
        if not selected_elements:
            return ''
        commands = []
        for pkey in selected_elements:
            parts = pkey.split('.')
            if len(parts) < 4:
                continue
            schema_name = parts[0]
            table_name = parts[1]
            entity_type = parts[2]
            entity_name = '.'.join(parts[3:])
            if entity_type == 'index':
                commands.append(f'DROP INDEX IF EXISTS "{schema_name}"."{entity_name}";')
            elif entity_type in ('relation','constraint'):
                commands.append(f'ALTER TABLE "{schema_name}"."{table_name}" DROP CONSTRAINT IF EXISTS "{entity_name}";')
        return '\n'.join(commands)

    @public_method
    def runDbUtils(self,instance_name=None,implementation=None,connection_pars=None,methodname=None):
        db = self.getDbFromPars(instance_name=instance_name,implementation=implementation,connection_pars=connection_pars)
        if not db:
            return
        if db.implementation not in ['postgres', 'postgres3']:
            return
        utils = PgDbUtils(db)
        l = json.loads(getattr(utils,methodname)())
        result = Bag()
        for i,row in enumerate(l):
            result.addItem(f'r_{i:02}',None,**row)
        return result
