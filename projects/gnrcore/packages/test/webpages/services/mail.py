# -*- coding: utf-8 -*-
from re import sub
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/testhandler:TestHandlerFull'
    js_requires='ckeditor/ckeditor'
    
    def test_0_sendmail(self,pane):
        "Send e-mail. You must configure a service or package email before testing"
        fb=pane.formbuilder(cols=3)
        fb.textBox(value='^.mail.from', lbl='From:')
        fb.textBox(value='^.mail.to', lbl='To:')
        fb.textBox(value='^.mail.subject', lbl='Subject:')
        fb.simpleTextArea(value='^.mail.content', lbl='Content:', width='95%', height='30px')
        fb.dbSelect(value='^.service.service_identifier', lbl='Mail service', 
                        table='sys.service', condition='$service_type=:type', condition_type='mail',
                        selected_service_name='^.service.service_name', hasDownArrow=True)

        send = fb.button('Send')
        send.dataRpc(self.sendMail, to_address='=.mail.to',from_address='=.mail.from', 
                    subject='=.mail.subject', body='=.mail.content', service_name='=.service.service_name')
    
    @public_method
    def sendMail(self,service_name=None,to_address=None,from_address=None,subject=None,body=None):
        mail_service = self.site.getService(service_name)
        assert mail_service,'set in services a mail service'
        result = mail_service.sendmail(to_address=to_address, from_address=from_address, subject=subject, body=body)
        return result

    def test_1_newMessageFromTemplate(self,pane):
        "Send e-mail with template. You must configure a template and package email before testing"
        fb=pane.formbuilder(cols=3)
        fb.textBox(value='^.mail.to', lbl='To:')
        fb.textBox(value='^.mail.subject', lbl='Subject:')
        fb.dbSelect(value='^.tpl.template_id', lbl='Template', 
                        table='adm.userobject', hasDownArrow=True, condition='$objtype=:tpl', condition_tpl='template',
                        rowcaption='$code,$description', auxColumns='$description,$userid', selected_tbl='^.tpl.tbl')
        fb.dbSelect(value='^.mail.account_id', lbl='Mail account', table='email.account', hasDownArrow=True)

        send = fb.button('Send')
        send.dataRpc(self.sendMessageFromTemplate, to_address='=.mail.to', subject='=.mail.subject', 
                        template_id='=.tpl.template_id', account_id='=.mail.account_id', tbl='=.tpl.tbl')
    
    @public_method
    def sendMessageFromTemplate(self, account_id=None, to_address=None, subject=None, template_id=None, tbl=None):
        msg_tbl = self.db.table('email.message')
        rnd_rec_id = self.db.table(tbl).query(columns='$id', limit=1).selection().output('pkeylist')
        new_msg = msg_tbl.newMessageFromUserTemplate(account_id=account_id, to_address=to_address, 
                                                        subject=subject, template_id=template_id, 
                                                        record_id=rnd_rec_id[0], doCommit=True)