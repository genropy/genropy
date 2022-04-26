# -*- coding: utf-8 -*-

"Mobyt service test"

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_smstest(self, pane):
        "Please configure Mobyt SMS service with your credentials and then test it here"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.textbox(value='^.sender', lbl='From')
        fb.textbox(value='^.recipient', lbl='To')
        fb.filteringSelect(value='^.message_type', lbl='Message Type', values='LL,L,N')
        fb.simpleTextarea(value='^.message',lbl='Text')
        fb.button('Run').dataRpc(self.sendsms, message_type='=.message_type', 
                            message='=.message', sender='=.sender', recipient='=.recipient')

    @public_method
    def sendsms(self, sender=None, recipient=None, message=None, message_type=None):
        smsservice = self.site.getService('sms')
        assert smsservice,'set in siteconfig the service smsmobyt'
        result = smsservice.sendsms(recipient=[recipient], sender=sender, message=message, message_type=message_type)
        print(result)