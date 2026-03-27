# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction

caption = '!!Retry send'
tags = 'admin'
description = '!!Clear errors and re-enqueue selected messages for sending'


class Main(BaseResourceAction):
    batch_prefix = 'RS'
    batch_title = '!!Retry send'
    batch_immediate = True

    def do(self):
        message_tbl = self.tblobj
        for message_id in self.get_selection_pkeys():
            message_tbl.retrySendMessage(message_id=message_id)
        self.db.commit()

    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div('!!This action clears all errors and re-enqueues the selected messages for sending.',
                 font_style='italic', color='#666', padding='10px')
