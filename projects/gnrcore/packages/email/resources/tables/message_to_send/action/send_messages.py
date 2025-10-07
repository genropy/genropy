# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction

caption = '!!Send emails'
tags = 'admin'
description='!!Send emails'


class Main(BaseResourceAction):
    batch_prefix = 'SM'
    batch_title = '!!Send emails'
    batch_immediate = True
    
    def do(self):
        self.tblobj.sendMessages()

    def table_script_parameters_pane(self, pane, **kwargs):
        pass
