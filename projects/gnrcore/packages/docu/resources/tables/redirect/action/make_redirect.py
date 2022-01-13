# -*- coding: utf-8 -*-

from gnr.web.batch.btcbase import BaseResourceBatch

caption = 'Make redirect'
description = caption

class Main(BaseResourceBatch):
    batch_prefix = 'RED'
    batch_title =  caption
    batch_cancellable = False
    batch_delay = 0.5

    def do(self):
        redirect_pkeys = self.get_selection_pkeys() or self.batch_parameters.get('redirect_pkeys')
        redirect_recs = self.db.table('docu.redirect').query(columns='*,$old_handbook_path,$old_handbook_url').fetchAsDict('id')

        for redirect_pkey in self.btc.thermo_wrapper(redirect_pkeys, message='Redirects', maximum=len(redirect_pkeys)):
            redirect_rec = redirect_recs[redirect_pkey]
            if redirect_rec['is_active']:
                self.db.table('docu.redirect').makeRedirect(redirect_rec)