#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.lib.services.mail import MailService

class Service(MailService):
    pass

class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.from_address',lbl='From address')
        fb.textbox(value='^.smtp_host',lbl='Smtp host')
        fb.textbox(value='^.user',lbl='User')
        fb.passwordTextBox(value='^.password',lbl='Password')
        fb.numberTextBox(value='^.port',lbl='Port',width='5em',places=0)
        fb.checkbox(value='^.ssl',label='SSL')
        fb.checkbox(value='^.tls',label='TLS')
