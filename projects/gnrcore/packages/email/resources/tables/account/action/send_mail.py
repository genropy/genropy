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
        if self.db.package('email').getMailProxy():
            return
        self.message_tbl = self.db.table('email.message')
        accounts = self.tblobj.query(where='$save_output_message IS TRUE').fetch()
        for account in accounts:
            self.sendEmailsForAccount(account)
    
    def sendEmailsForAccount(self, account):
        mts_tbl = self.db.table('email.message_to_send')
        messages_to_send = mts_tbl.query(
            columns='$message_id',
            where='@message_id.account_id=:acid',
            acid=account['id'],
            order_by='$__ins_ts',
            limit=account['send_limit']
        ).fetch()

        for row in messages_to_send:
            try:
                self.message_tbl.sendMessage(pkey=row['message_id'])
            except Exception as e:
                raise

    def table_script_parameters_pane(self, pane, **kwargs):
        pass
