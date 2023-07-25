# -*- coding: utf-8 -*-

# contextname.py
# Created by Francesco Porcari on 2011-03-05.
# Copyright (c) 2011 Softwell. All rights reserved.

from builtins import object
class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def test_0_notification(self,pane):
        """Notification"""
        fb = pane.formbuilder(cols=3,border_spacing='3px')
        fb.button('Subscribe',action='genro.webpushSubscribe()',)
        fb.button('Notify').dataRpc(
            self.webpushNotify,
            _ask=dict(title='Notify',fields=[
                dict(name='user',lbl='User'),
                dict(name='title',lbl='Title'),
                dict(name='message',lbl='Message'),
                dict(name='url',lbl='Url'),
                dict(name='logged',label='Logged',tag='checkbox')

            ])
        )


