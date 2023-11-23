# -*- coding: utf-8 -*-

# test_special_action.py
# Created by Francesco Porcari on 2010-07-02.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.batch.btcaction import BaseResourceAction

caption = '!!Delete selection rows'
tags = 'superadmin'
permissions = 'del'
description = '!!Delete selection rows'

class Main(BaseResourceAction):
    batch_prefix = 'delete'
    batch_title = 'Delete selection rows'
    batch_cancellable = False
    batch_delay = 0.5
    batch_immediate = True


    def do(self):
        columns = '*'
        if self.tblobj.column('__is_protected_row') is not None:
            columns='*,$__is_protected_row'
        selection = self.get_selection(columns=columns)
        for r in self.btc.thermo_wrapper(selection, 'record'):
            if r.get('__is_protected_row'):
                continue
            self.tblobj.delete(r)
        self.db.commit()
            


    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div('You are going to delete the elements of the current selection')