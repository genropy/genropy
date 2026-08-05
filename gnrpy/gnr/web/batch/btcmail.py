#!/usr/bin/env python
# encoding: utf-8
#
#btcmail.py
#
#Created by Francesco Porcari on 2010-10-16.
#Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.batch.btcbase import BaseResourceBatch
from gnr.core.gnrbag import Bag
from datetime import datetime

class BaseResourceMail(BaseResourceBatch):
    def __init__(self, *args, **kwargs):
        super(BaseResourceMail, self).__init__(**kwargs)
        self._mail_handler = None

    @property
    def mail_handler(self):
        if not self._mail_handler:
            self._mail_handler = self.page.getService('mail')
        return self._mail_handler

    def send_one_template(self,record=None,to_address=None,cc_address=None,subject=None,body=None,attachments=None,**kwargs):
        self.mail_handler.sendmail_template(record,body=body,to_address=to_address,attachments=attachments,
                                            cc_address=cc_address,subject=subject,**kwargs)

    def send_one_email(self,**kwargs):
        if self.db.package('email'):
            self.mail_handler.sendmail(account_id=self.batch_parameters.get('account_id'),**kwargs)
        else:
            self._send_one_email_legacy(**kwargs)

    
            
    def _send_one_email_legacy(self,to_address=None,from_address=None,
                                cc_address=None,subject=None,body=None,
                                attachments=None,_record_id=None,html=None,**kwargs):
        mp = Bag(self.mail_handler.getDefaultMailAccount())
        mail_code = self.batch_parameters.get('mail_code')
        tbl = self.tblobj.fullname
        now = datetime.now()
        try:
            self.mail_handler.sendmail(to_address=to_address,
                                    body=body, subject=subject,
                                    cc_address=cc_address, bcc_address=mp['bcc_address'],
                                    from_address=from_address or mp['from_address'],
                                    attachments=attachments or mp['attachments'], 
                                    account=mp['account'],
                                    smtp_host=mp['smtp_host'], port=mp['port'], user=mp['user'], password=mp['password'],
                                    ssl=mp['ssl'], tls=mp['tls'], html=mp['html'], async_=False)
            
            with self.db.tempEnv(connectionName='system',storename=self.db.rootstore):
                self.db.table('adm.sent_email').insert(dict(code=mail_code,tbl=tbl,mail_address=to_address,sent_ts=now,record_id=_record_id))
                self.db.commit()

        except Exception:
            with self.db.tempEnv(connectionName='system',storename=self.db.rootstore):
                self.db.table('adm.sent_email').insert(dict(code=mail_code,tbl=tbl,mail_address=to_address,sent_ts=None,_record_id=_record_id))
                self.db.commit()
        
    def get_template(self,template_address):
        if not ':' in template_address:
            template_address = 'adm.userobject.data:%s' %template_address
        return self.page.loadTemplate(template_address,asSource=True)[0]

    def get_selection(self,**kwargs):
        selection = super(BaseResourceMail, self).get_selection(**kwargs)
        mail_code = self.batch_parameters.get('mail_code')
        if not mail_code:
            return selection
        tbl = self.tblobj.fullname
        sending_pkeys = selection.output('pkeylist')
        sent = self.db.table('adm.sent_email').query(where='$tbl=:tbl AND $code=:c AND $sent_ts IS NOT NULL AND $record_id IN :spk',
                                        tbl=tbl,c=mail_code,spk=sending_pkeys,
                                        columns='$record_id').fetch()
        if not sent:
            return selection
        sent = set([r['record_id'] for r in sent])
        sending_pkeys = set(sending_pkeys)
        sending_pkeys = sending_pkeys.difference(sent)
        return self.tblobj.query(where='$%s IN :pk' %self.tblobj.pkey,pk=sending_pkeys,excludeDraft=False,**kwargs).selection()