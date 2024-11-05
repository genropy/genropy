# -*- coding: utf-8 -*-

# tpleditor.py
# Created by Francesco Porcari on 2011-06-22.
# Copyright (c) 2011 Softwell. All rights reserved.

import struct
import json
from gnr.core.gnrdecorator import public_method
from gnr.sql.gnrsqlmigration import SqlMigrator
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerBase,public:Public"
    
    def test_0_migration(self,pane):
        bc = pane.borderContainer(height='800px')
        bc.roundedGroupFrame(region='left',width='50%',title='SQL').tree(storepath='.result.sqlstructure')
        fl = bc.contentPane(region='top').formlet(cols=2)
        fl.textbox(value='^.instance_name',lbl='Instance')
        fl.button('Run',lbl='&nbsp;').dataRpc('.result',self.getMigrationBag,instance_name='=.instance_name',migrate='^.migrate')
        tc = bc.tabContainer(region='bottom',height='200px')
        tc.contentPane(title='DiffTree').tree(storepath='.result.diff')
        tg = tc.contentPane(title='Migration Commands').treeGrid(storepath='.result.commands_tree',headers=True,
                    _class='fieldsTree')
        tg.column('caption',header='Entity')
        tg.column('evt',size=80,header='Evt')
        tg.column('entity',size=100,header='Entity type')
        tg.column('sql',size=300,header='Sql')
        bc.roundedGroupFrame(region='center',title='ORM').tree(storepath='.result.ormstructure')


    @public_method
    def getMigrationBag(self,instance_name=None,migrate=None):
        mig = SqlMigrator(instance_name)
        result = Bag()
        
        mig.toSql()
        result['diff'] = Bag(json.loads(mig.diff.to_json()))
        if migrate:
            mig.applyChanges()
            mig = SqlMigrator(instance_name)
            mig.toSql()
        result['sqlstructure'] = Bag(mig.sqlStructure)
        result['ormstructure'] = Bag(mig.ormStructure)
        result['diff'] = Bag(json.loads(mig.diff.to_json()))
        result['commands_tree'] = self.prepareCommandsTree(mig.commands)
        return result
    
    def prepareCommandsTree(self,commans_dict):
        result = Bag()
        for t,vl in commans_dict.items():
            if not result.getItem(t[0]):
                result.setItem(t[0],Bag(),caption=t[0])
            if not result.getItem(f'{t[0]}.{t[1]}'):
                result.setItem(f'{t[0]}.{t[1]}',Bag(),caption=t[1])
            fullpath = '.'.join(t)
            b = result.getItem(fullpath) or Bag()
            for i,v in enumerate(vl):
                b.addItem(f'r_{i:02}',None,**v)
            result.setItem(fullpath,b,_attributes={'table':t[2] if len(t)>2 else None,'schema':t[1] if len(t)>1 else None,'caption':fullpath})
        return result
            
