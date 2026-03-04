# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.lib.services.mail import MailService

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
        fb.textBox(value='^.mail.cc', lbl='CC:')
        fb.textBox(value='^.mail.bcc', lbl='BCC:')
        fb.textBox(value='^.mail.subject', lbl='Subject:')
        fb.dbSelect(value='^.tpl.template_id', lbl='Template', 
                        table='adm.userobject', hasDownArrow=True, condition='$objtype=:tpl', condition_tpl='template',
                        rowcaption='$code,$description', auxColumns='$description,$userid', selected_tbl='^.tpl.tbl')
        fb.dbSelect(value='^.mail.account_id', lbl='Mail account', table='email.account', hasDownArrow=True)

        send = fb.button('Send')
        send.dataRpc(self.sendMessageFromTemplate, to_address='=.mail.to', cc_address='=.mail.cc', 
                        bcc_address='=.mail.bcc', subject='=.mail.subject', 
                        template_id='=.tpl.template_id', account_id='=.mail.account_id', tbl='=.tpl.tbl')
    
    @public_method
    def sendMessageFromTemplate(self, account_id=None, to_address=None, cc_address=None, 
                                        bcc_address=None, subject=None, template_id=None, tbl=None):
        msg_tbl = self.db.table('email.message')
        rnd_rec_id = self.db.table(tbl).query(columns='$id', limit=1).selection().output('pkeylist')
        new_msg = msg_tbl.newMessageFromUserTemplate(account_id=account_id, to_address=to_address, 
                                                        cc_address=cc_address, bcc_address=bcc_address,
                                                        subject=subject, template_id=template_id, 
                                                        record_id=rnd_rec_id[0], doCommit=True)

    def test_3_set_params(self, pane):
        "Send e-mail indicating all required parameters, no service configuration required"
        fb = pane.div(margin='5px').formbuilder(cols=1, border_spacing='6px', width='100%', fld_width='100%', tdl_width='10em')
        fb.div(lbl='Mail Settings', colspan=2, lbl_font_style='italic', lbl_margin_top='1em', margin_top='1em',
               lbl_color='#7e5849')
        fb.textbox(value='^.smtp_host', lbl='SMTP Host', dtype='T', colspan=1)
        fb.textbox(value='^.from_address', lbl='From address', dtype='T', colspan=1)
        fb.textbox(value='^.to_address', lbl='To address', dtype='T', colspan=1)
        fb.textbox(value='^.user', lbl='Username', dtype='T', colspan=1)
        fb.passwordTextBox(value='^.password', lbl='Password', dtype='T', colspan=1)
        fb.textbox(value='^.port', lbl='Port', dtype='T', colspan=1)
        fb.checkbox(value='^.tls', lbl='TLS', dtype='B', colspan=1)
        fb.checkbox(value='^.ssl', lbl='SSL', dtype='B', colspan=1)

        fb.simpleTextarea(value='^.message',lbl='Text')
        fb.button('Run').dataRpc(self.send_email, smtp_host='=.smtp_host', 
                            port='=.port', message='=.message', 
                            tls='=.tls', ssl='=.ssl',
                            from_address='=.from_address', to_address='=.to_address', 
                            user='=.user', password='=.password')

    @public_method
    def send_email(self, smtp_host=None, port=None, ssl=None, tls=None, user=None, password=None,
                            message=None,from_address=None,to_address=None):
        msg = "From: {from_address}\r\nTo: {to_address}\r\n{message}".format(from_address=from_address, 
                            to_address=to_address, message=message)
        account_params = dict(smtp_host=smtp_host, port=port, user=user, password=password, ssl=ssl, tls=tls)
        mh = MailService()
        with mh.get_smtp_connection(**account_params) as smtp_connection:
            smtp_connection.sendmail(from_address, to_address, msg)
            print("Successfully sent email")
