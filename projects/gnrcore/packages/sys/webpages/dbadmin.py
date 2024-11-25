# -*- coding: utf-8 -*-

# tpleditor.py
# Created by Francesco Porcari on 2011-06-22.
# Copyright (c) 2011 Softwell. All rights reserved.

from flask import json
from gnr.core.gnrdecorator import public_method
from gnr.sql.gnrsqlmigration import SqlMigrator
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
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
        fb.filteringSelect(value='^.implementation',values='postgres,sqlite,mysql,mssql,fourd,gnrinstance',
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

        self.dbUtilsPane(tc,title='Utils',datapath='.dbutils')

        bc = tc.borderContainer(title='JSON Structures',datapath='.structures')
        bc.roundedGroupFrame(region='center',width='50%',title='SQL').tree(storepath='.sql')
        bc.roundedGroupFrame(region='right',width='50%',title='Orm').tree(storepath='.orm')

    def dbUtilsPane(self,parent,**kwargs):
        bc = parent.borderContainer(**kwargs)
        pane = bc.contentPane(region='center',overflow='auto')
        for methodname,desc in PgDbUtils.list_pgutils().items():
            g = pane.gridbox(cols=3,datapath=f'.{methodname}',margin='4px',
                             border='2px solid silver',justify_content='center',rounded=8)
            g.div(methodname,padding_left='10px',font_weight='bold')
            g.div(desc,font_style='italic')
            g.button('Run').dataController("genro.publish('dbUtilsRun',{methodname:methodname});",methodname=methodname)
            g.div(colspan=3,border_top='1px solid silver',
                  min_height='100px',padding='5px').quickGrid(value='^.result')


    @public_method
    def getMigrationBag(self,instance_name=None,implementation=None,connection_pars=None):
        db = self.getDbFromPars(instance_name=instance_name,implementation=implementation,connection_pars=connection_pars)
        mig = SqlMigrator(db,ignore_constraint_name=True)
        result = Bag()
        mig.prepareMigrationCommands()
        cleanModel = mig.jsonModelWithoutMeta()
        result['sql'] = Bag(mig.sqlStructure)
        result['orm'] = Bag(mig.ormStructure)
        result['orm_clean'] = Bag(cleanModel['orm'])
        result['sql_clean'] = Bag(cleanModel['sql'])
        result['diff'] = mig.getDiffBag()
        result['commands_tree'] = Bag(mig.commands)
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
    def runDbUtils(self,instance_name=None,implementation=None,connection_pars=None,methodname=None):
        db = self.getDbFromPars(instance_name=instance_name,implementation=implementation,connection_pars=connection_pars)
        if not db:
            return
        if db.implementation!='postgres':
            return
        utils = PgDbUtils(db)
        l = json.loads(getattr(utils,f'pgutils_{methodname}')())
        result = Bag()
        for i,row in enumerate(l):
            result.addItem(f'r_{i:02}',None,**row)
        return result