#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import extract_kwargs
from gnrpkg.adm.services.mail import AdmMailService
from gnr.web.gnrbaseclasses import BaseComponent

class Service(AdmMailService):

    def get_account_params(self, account_id=None, **kwargs):
        account_parameters = dict(self.smtp_account)
        email_account_id = account_id or self.parent.getPreference('mail.email_account_id',pkg='adm')   #DP Preferenza in email 
        if email_account_id:
            account_parameters =  self.parent.db.table('email.account').getSmtpAccountPref(email_account_id)
            account_parameters['account_id'] = email_account_id
        for k,v in kwargs.items():
            if not kwargs.get(k,None):
                account_parameters[k]=v                                                                     
        return account_parameters

    def set_smtp_account(self, email_account_id=None,**kwargs):
        self.smtp_account = dict(email_account_id=email_account_id)
            
    @extract_kwargs(headers=True)
    def sendmail(self,scheduler=None,account_id=None,attachments=None,headers_kwargs=None,doCommit=None,**kwargs):
        #db = self.parent.db
        #account_id = account_id or self.getDefaultMailAccount()['account_id']
        #if scheduler is None:
        #    scheduler = db.table('email.account').readColumns(pkey=account_id,columns='$save_output_message')  
        account_parameters = self.get_account_params(account_id, **kwargs)
            #for k,v in account_parameters.items():
            #    if not kwargs.get(k,None):
            #        kwargs[k]=v
        default_scheduler = account_parameters.pop('scheduler',None)
        scheduler = default_scheduler if scheduler is None else scheduler
        if scheduler:
            new_message = self.parent.db.table('email.message').newMessage(attachments=attachments,
                                                    headers_kwargs=headers_kwargs,doCommit=doCommit,**account_parameters)   #kwargs?
            return new_message
        else:
            kwargs['headers_kwargs'] = headers_kwargs
            return super(Service, self).sendmail(attachments=attachments,**account_parameters)  #kwargs?
        
        #info@softwell.it
        #Amministrazione <info@softwell.it>
        #Ufficio Tecnico <info@softwell.it>

class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.dbSelect(value='^.email_account_id',lbl='Default smtp account',dbtable='email.account')
