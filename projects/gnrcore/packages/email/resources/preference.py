# -*- coding: utf-8 -*-

class AppPref(object):
    def permission_email(self, **kwargs):
        return 'admin'

    def prefpane_email(self, parent, **kwargs):
        fb = parent.contentPane(**kwargs).formbuilder(cols=1)
        fb.dbSelect('^.email_account_id', table='email.account',
                    lbl='!![en]Default e-mail account', hasDownArrow=True)
        fb.textbox('^.dflt_reply_to', lbl='!![en]Default reply-to address',
                   tip="!!This will be applied to all e-mails sent without a specific reply-to address")
        fb.checkbox('^.collect_addresses', lbl='!![en]Collect addresses',
                    tip="!![en]If enabled, stores all message addresses in a separate table for searching")
        fb.checkbox('^.exclude_from_address', lbl='!![en]Exclude FROM address',
                    tip="!![en]If enabled, excludes sender addresses from collection",
                    hidden='^.collect_addresses?=!#v')
