#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import extract_kwargs
from gnrpkg.adm.services.mail import AdmMailService
from gnr.web.gnrbaseclasses import BaseComponent

class Service(AdmMailService):

    def get_account_params(self, account_id=None, **kwargs):
        """
        Build the SMTP connection parameters. Please note that this method
        redefines base method in base class MailService (/lib/services/mail.py)
        in case the package mail is present.

        If an account_id is provided, the method loads
        the saved configuration from the email.account table and merges it.
        If no account_id is provided (no package mail), then only the parameters
        passed in kwargs are used (smtp_host, port, user, etc).
        In both cases, kwargs always override any defaults or stored values.
        """
        result = dict(self.smtp_account)
        email_account_id = account_id or self.parent.getPreference('mail.email_account_id',pkg='adm')
        if email_account_id:
            account_parameters =  self.parent.db.table('email.account').getSmtpAccountPref(email_account_id)
            account_parameters['account_id'] = email_account_id
        result = dict(kwargs)    
        for k,v in account_parameters.items():
            if result.get(k) is None:
                result[k] = v      
        return result

    def set_smtp_account(self, email_account_id=None,**kwargs):
        """
        Set the default smtp_account reference (used as a base for building parameters).
        """
        self.smtp_account = dict(email_account_id=email_account_id)
            
    @extract_kwargs(headers=True)
    def sendmail(self, scheduler=None, account_id=None, attachments=None, headers_kwargs=None, doCommit=None,
                 smtp_connection=None, **kwargs):
        """
        Send an email. Please note that this method
        redefines base method in base class MailService (/lib/services/mail.py)
        in case the package mail is present.

        If scheduler is True, a new message record is created in email.message.
        Otherwise the message is sent immediately using either the provided account_id
        or explicit SMTP parameters. An optional smtp_connection can be passed to reuse
        an open connection.
        """
        db = self.parent.db
        account_id = account_id or self.getDefaultMailAccount()['account_id']
        if scheduler is None:
            scheduler = db.table('email.account').readColumns(pkey=account_id,columns='$save_output_message')  
        if account_id:
            account_parameters = self.get_account_params(account_id)
            for k,v in account_parameters.items():
                if not kwargs.get(k,None):
                    kwargs[k]=v
        if scheduler:
            message_tbl = self.parent.db.table('email.message')
            new_message = message_tbl.newMessage(attachments=attachments,
                                                    headers_kwargs=headers_kwargs,doCommit=doCommit,**message_kwargs)
            if new_message['priority'] == '-1':
                new_message = message_tbl.sendMessage(new_message['id'])
            return new_message
        else:
            kwargs['headers_kwargs'] = headers_kwargs
            return super(Service, self).sendmail(attachments=attachments, smtp_connection=smtp_connection, **kwargs)

class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.dbSelect(value='^.email_account_id',lbl='!![en]Default smtp account',dbtable='email.account')
