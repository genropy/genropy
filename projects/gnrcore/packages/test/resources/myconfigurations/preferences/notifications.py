# -*- coding: utf-8 -*-

info = dict(caption='Notifications', code='notifications', priority=1)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.checkbox(value='^.email_notifications', label='Email notifications')
        fb.checkbox(value='^.sms_notifications', label='SMS notifications')
        fb.checkbox(value='^.push_notifications', label='Push notifications')
