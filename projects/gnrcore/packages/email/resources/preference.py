# -*- coding: utf-8 -*-

class AppPref(object):
    def permission_email(self, **kwargs):
        return 'admin'

    def prefpane_email(self, parent, **kwargs):
        fb = parent.contentPane(region='center').formbuilder(cols=1)
        fb.dbSelect('^.dflt_email_account_id', table='email.account', lbl='!![en]Default e-mail account')
        fb.textbox('^.dflt_noreply', lbl='!![en]Default no-reply address')