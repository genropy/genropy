# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction
from gnr.app import pkglogger as logger

caption = '!!Send messages'
tags = 'admin'
description='!!Send send messages'


class Main(BaseResourceAction):
    batch_prefix = 'SENDMSG'
    batch_title = '!!Send Messages'
    batch_immediate = True
    
    def do(self):
        """
        Groups pending messages by account_id, opens one SMTP session per account,
        enforces each account's send_limit by stopping the inner loop when reached,
        and reuses the same smtp_connection for all messages of that account.
        """
        self.mail_handler = self.db.application.site.getService('mail')
        if self.get_selection_pkeys():
            where = '$id IN :messages_to_send'
        else:
            where = "$message_to_send IS TRUE"
        messages_to_send = self.query(where=where, columns='$id,$account_id,@account_id.send_limit AS send_limit'
                                      ).fetchGrouped('account_id')
        for account_id, messages in messages_to_send.items():
            send_limit = messages[0]['send_limit'] if messages and isinstance(messages[0], dict) else None
            with self.mail_handler.smtp_session(account=account_id) as smtp_connection:
                count = 0
                for message in messages:
                    if send_limit and count >= send_limit:
                        log_msg = f'Stopped sending for account {account_id}: reached send limit {send_limit}'
                        logger.warning(log_msg)
                        self.batch_log_write(log_msg)
                        break
                    message_id = message['id'] if isinstance(message, dict) else message
                    try:
                        self.tblobj.sendMessage(pkey=message_id, smtp_connection=smtp_connection)
                    except Exception as e:
                        log_msg = f'Error sending mail message {message_id}: {e}'
                        logger.error(log_msg)
                        self.batch_log_write(log_msg)
                    count += 1

    def table_script_parameters_pane(self, pane, **kwargs):
        pass
