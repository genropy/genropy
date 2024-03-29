#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import extract_kwargs
from gnrpkg.adm.services.mail import AdmMailService
from gnr.web.gnrbaseclasses import BaseComponent

class Service(AdmMailService):

    def get_account_params(self, account_id=None, **kwargs):
        account_parameters = dict(self.smtp_account)
        email_account_id = account_id or self.parent.getPreference('mail.email_account_id',pkg='adm') or self.parent.getPreference('email_account_id',pkg='email') 
        if email_account_id:
            account_parameters =  self.parent.db.table('email.account').getSmtpAccountPref(email_account_id)
            account_parameters['account_id'] = email_account_id
        result = dict(kwargs)    
        for k,v in account_parameters.items():
            if result.get(k) is None:
                result[k] = v                                         
        return result

    def set_smtp_account(self, email_account_id=None,**kwargs):
        self.smtp_account = dict(email_account_id=email_account_id)
            
    @extract_kwargs(headers=True)
    def sendmail(self, scheduler=None, account_id=None, attachments=None,
                        headers_kwargs=None, doCommit=None, noreply=None, nosend=None, **kwargs):   
        message_kwargs = self.get_account_params(account_id, **kwargs)    #DP message parameters and connection settings in kwargs
        default_scheduler = message_kwargs.pop('scheduler',None)
        dflt_noreply = message_kwargs.pop('dflt_noreply',None)
        if noreply:
            message_kwargs['reply_to'] = dflt_noreply

        scheduler = default_scheduler if scheduler is None else scheduler
        if scheduler:
            new_message = self.parent.db.table('email.message').newMessage(attachments=attachments,
                                                    headers_kwargs=headers_kwargs,doCommit=doCommit,**message_kwargs)
            return new_message
        else:
            kwargs['headers_kwargs'] = headers_kwargs
            return super(Service, self).sendmail(attachments=attachments,**message_kwargs)
    

class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.dbSelect(value='^.email_account_id',lbl='Default smtp account',dbtable='email.account')
