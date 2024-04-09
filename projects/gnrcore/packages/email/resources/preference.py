# -*- coding: utf-8 -*-

class AppPref(object):
    def permission_email(self, **kwargs):
        return 'admin'

    def prefpane_email(self, parent, **kwargs):
        fb = parent.contentPane(**kwargs).formbuilder(cols=1)
        fb.dbSelect('^.email_account_id', table='email.account', 
                        lbl='!![en]Default e-mail account', hasDownArrow=True)
        fb.textbox('^.dflt_noreply', lbl='!![en]Default no-reply address')