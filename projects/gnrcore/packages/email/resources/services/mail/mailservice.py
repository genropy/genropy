#!/usr/bin/env pythonw
# -*- coding: UTF-8 -*-

from gnr.core.gnrbag import Bag
from gnrpkg.adm.services.mail import AdmMailService
from gnr.web.gnrbaseclasses import BaseComponent

class Service(AdmMailService):

    def get_account_params(self, account_id=None, **kwargs):
        result = dict(self.smtp_account)
        email_account_id = account_id or self.parent.getPreference('mail.email_account_id',pkg='adm')
        if email_account_id:
            account_params =  self.parent.db.table('email.account').getSmtpAccountPref(email_account_id)
            result.update(account_params)
            result['account_id'] = email_account_id
        result.update(kwargs)
        return result

    def set_smtp_account(self, email_account_id=None,**kwargs):
        self.smtp_account = dict(email_account_id=email_account_id)
    
    def sendmail(self,scheduler=None,account_id=None,moveAttachment=None,**kwargs):
        db = self.parent.db
        if scheduler is None:
            account_id = account_id or self.getDefaultMailAccount()['account_id']
            scheduler = db.table('email.account').readColumns(pkey=account_id,columns='$save_output_message')  
        if scheduler:
            if moveAttachment is None:
                moveAttachment = True
            db.table('email.message').newMessage(account_id=account_id,
                                                        moveAttachment=moveAttachment,**kwargs)
        else:
            super(Service, self).sendmail(account_id=account_id,**kwargs)

class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.dbSelect(value='^.email_account_id',lbl='Default smtp account',dbtable='email.account')
