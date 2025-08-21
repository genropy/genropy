# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction
from gnr.app import pkglogger as logger

caption = '!!Send emails'
tags = 'admin'
description='!!Send emails'

class Main(BaseResourceAction):
    batch_prefix = 'SENDACC'
    batch_title = '!!Send emails'
    batch_immediate = True
    
    def do(self):
        """
        Iterates over accounts that have save_output_message enabled,
        opens one SMTP session per account, and sends all pending emails
        for that account by delegating to sendEmailsForAccount().
        """
        self.message_tbl = self.db.table('email.message')
        mail_handler = self.db.application.site.getService('mail')
        accounts = self.tblobj.query(where='$save_output_message IS TRUE').fetch()
        for account in accounts:
            with mail_handler.smtp_session(account=account) as smtp_connection:
                self.sendEmailsForAccount(account, smtp_connection=smtp_connection)
    
    def sendEmailsForAccount(self,account, smtp_connection=None):
        email_to_send = self.message_tbl.query(where="""$message_to_send IS TRUE 
                                                        AND $account_id=:acid""",
                                        order_by='$__ins_ts',
                                        limit=account['send_limit'],
                                        acid=account['id'],
                                        bagFields=True).fetch()
        for message in email_to_send:
            message_id = message['id']
            try:
                self.message_tbl.sendMessage(pkey=message_id, smtp_connection=smtp_connection)
            except Exception as e:
                log_msg = f'Error sending mail message {message_id}: {e}'
                logger.error(log_msg)
                self.batch_log_write(log_msg)

    def table_script_parameters_pane(self, pane, **kwargs):
        pass
