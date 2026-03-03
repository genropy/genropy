# -*- coding: utf-8 -*-


class Grouplet(object):
    def __info__(self):
        return dict(caption='Notifications', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.checkbox(value='^.email_notifications', label='Email notifications')
        fb.checkbox(value='^.sms_notifications', label='SMS notifications')
        fb.checkbox(value='^.push_notifications', label='Push notifications')
