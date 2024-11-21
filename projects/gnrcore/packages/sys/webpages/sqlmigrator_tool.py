# -*- coding: utf-8 -*-

# tpleditor.py
# Created by Francesco Porcari on 2011-06-22.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.core.gnrdecorator import public_method
from gnr.sql.gnrsqlmigration import SqlMigrator
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp

class GnrCustomWebPage(object):
    py_requires="public:Public"
    
    def main(self,root, **kwargs):
        bc = root.borderContainer(datapath='main')
        bc.roundedGroupFrame(region='left',width='50%',title='SQL').tree(storepath='.result.sqlstructure')
        fl = bc.contentPane(region='top').formlet(cols=2)
        fl.textbox(value='^.instance_name',lbl='Instance')
        fl.button('Run',lbl='&nbsp;').dataRpc('.result',self.getMigrationBag,instance_name='=.instance_name',migrate='^.migrate')
        tc = bc.tabContainer(region='bottom',height='40%')
        tg = tc.contentPane(title='DiffTree').bagEditor(storepath='.result.diff',headers=True)
        #tg.column('caption',header='Entity')
        #tg.column('old',size=110,header='Old')
        #tg.column('new',size=110,header='New')
        #tg.column('reason',size=150,header='Reason')
        #tg.column('changed_attribute',size=110,header='Attribute')

        tc.contentPane(title='Migration Commands').tree(storepath='.result.commands_tree')
        bc.roundedGroupFrame(region='center',title='ORM').tree(storepath='.result.ormstructure')


    @public_method
    def getMigrationBag(self,instance_name=None,migrate=None):
        app = GnrApp(instance_name)
        mig = SqlMigrator(app.db)
        result = Bag()
        mig.toSql()
        if migrate:
            mig.applyChanges()
            mig = SqlMigrator(instance_name)
            mig.toSql()
        result['sqlstructure'] = Bag(mig.sqlStructure)
        result['ormstructure'] = Bag(mig.ormStructure)
        result['diff'] = mig.getDiffBag()
        result['commands_tree'] = Bag(mig.commands)
        return result
    
    
