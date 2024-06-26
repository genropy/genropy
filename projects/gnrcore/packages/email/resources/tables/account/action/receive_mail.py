# -*- coding: utf-8 -*-

from __future__ import print_function
from gnr.web.batch.btcaction import BaseResourceAction


caption = '!!Receive email'
tags = 'admin'
description='!!Receive email'


class Main(BaseResourceAction):
    batch_prefix = 'RM'
    batch_title = '!!Receive email'
    batch_immediate = True
    
    def do(self):
        selection = self.get_selection() or self.db.table('email.account').query(where='$schedulable IS TRUE').selection()
        tblmessage = self.db.table('email.message')
        for r in selection.output('pkeylist'):
            try:
                tblmessage.receive_imap(account=r)  
            except Exception as e:
                raise
                print('ERROR IN RECEIVING IMAP receive_email batch', str(e))

    def table_script_parameters_pane(self, pane, **kwargs):
        pass
