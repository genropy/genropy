# -*- coding: utf-8 -*-

from gnr.web.batch.btcbase import BaseResourceBatch
import os
import errno

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
            old_url = redirect_rec['old_url']
            old_page_to_red = old_url.replace(redirect_rec['old_handbook_url'],'')
            old_page_path = '/sphinx/build' + old_page_to_red
            sn = self.page.site.storageNode(redirect_rec['old_handbook_path']+old_page_path)
            new_url = redirect_rec['new_url']
            html_text = self.defaultHtmlRedirect(new_url)

            #Check if folder exists, otherwise creates it
            if not os.path.exists(os.path.dirname(sn.internal_path)):
                try:
                    os.makedirs(os.path.dirname(sn.internal_path))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            with open(sn.internal_path,"w") as html_file:
                html_file.write(html_text)

    def defaultHtmlRedirect(self, new_url):
        return """<html>
                    <head>
                        <meta http-equiv="refresh" content="1; url={new_url}" />
                        <script>
                          window.location.href = "{new_url}"
                        </script>
                    </head>
                </html>""".format(new_url=new_url)
