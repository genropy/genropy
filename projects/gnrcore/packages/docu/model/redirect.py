# encoding: utf-8
import os

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('redirect', pkey='id', name_long='Redirect', name_plural='Redirects',caption_field='page_name',
                                    checkpref='docu.manage_redirects')
        self.sysFields(tbl)
        
        tbl.column('page_id',size='22',name_long='!![en]Moved Page').relation('documentation.id',
                                relation_name='redirects', mode='foreignkey', onDelete='raise')
        tbl.column('old_url', name_long='!![en]Old url')
        tbl.column('new_url', name_long='!![en]New url')
        tbl.column('old_handbook_id',size='22', group='_', name_long='!![en]Old Handbook'
                    ).relation('docu.handbook.id', relation_name='old_redirects', mode='foreignkey', onDelete='raise')
        tbl.column('new_handbook_id',size='22', group='_', name_long='!![en]New Handbook'
                    ).relation('docu.handbook.id', relation_name='new_redirects', mode='foreignkey', onDelete='raise')
        tbl.column('is_active', dtype='B', name_long='Is active', name_short='Act.')

        tbl.aliasColumn('page_name', '@page_id.name', name_long='!![en]Page name')
        tbl.aliasColumn('old_handbook_path', '@old_handbook_id.sphinx_path', name_long='!![en]Handbook path')
        tbl.aliasColumn('old_handbook_url', '@old_handbook_id.handbook_url', name_long='!![en]Handbook url')

    def defaultValues(self):
        return dict(is_active=True)
        
    def makeRedirect(self, redirect_rec):
        old_url = redirect_rec['old_url']
        old_page_to_red = old_url.replace(redirect_rec['old_handbook_url'],'')
        sn = self.db.application.site.storageNode(redirect_rec['old_handbook_path'],old_page_to_red, autocreate=True)
        new_url = redirect_rec['new_url']
        html_text = self.defaultHtmlRedirect(new_url)

        with sn.open(mode='wb') as html_file:
            html_file.write(html_text.encode())

    def defaultHtmlRedirect(self, new_url):
        return """<html>
                    <head>
                        <meta http-equiv="refresh" content="1; url={new_url}" />
                        <script>
                          window.location.href = "{new_url}"
                        </script>
                    </head>
                </html>""".format(new_url=new_url)