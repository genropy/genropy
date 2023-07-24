# -*- coding: utf-8 -*-

# contextname.py
# Created by Francesco Porcari on 2011-03-05.
# Copyright (c) 2011 Softwell. All rights reserved.

from builtins import object
class GnrCustomWebPage(object):
    js_requires='webpush'
    py_requires="gnrcomponents/testhandler:TestHandlerFull"


    def test_0_notification(self,pane):
        """Notification"""
        fb = pane.formbuilder(cols=3,border_spacing='3px')
        fb.textBox(value='^.message',lbl='Message')
        fb.button('Start',action='WEBPUSH.subscribeUser();',)
        fb.button('Notify',action='WEBPUSH.notifyAll(message)', message='=.message')


