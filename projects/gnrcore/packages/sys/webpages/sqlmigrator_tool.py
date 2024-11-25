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
        fl.button('Check',lbl='&nbsp;').dataRpc('.result',self.getMigrationBag,
                                                migrate='^.migrate',_onStart=True)
        tc = bc.tabContainer(region='bottom',height='40%')
        tg = tc.contentPane(title='DiffTree').bagEditor(storepath='.result.diff',headers=True)
        tc.contentPane(title='Migration Commands').tree(storepath='.result.commands_tree')
        bc.roundedGroupFrame(region='center',title='ORM').tree(storepath='.result.ormstructure')


    @public_method
    def getMigrationBag(self,migrate=None):
        mig = SqlMigrator(self.db,ignore_constraint_name=True)
        result = Bag()
        mig.prepareMigrationCommands()
        if migrate:
            mig.applyChanges()
            mig = SqlMigrator(self.db)
            mig.prepareMigrationCommands()
        result['sqlstructure'] = Bag(mig.sqlStructure)
        result['ormstructure'] = Bag(mig.ormStructure)
        result['diff'] = mig.getDiffBag()
        result['commands_tree'] = Bag(mig.commands)
        return result
    
    
