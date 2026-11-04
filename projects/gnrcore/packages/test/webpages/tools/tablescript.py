# -*- coding: utf-8 -*-

"""A table template rendered on the server, as HTML or as a PDF

Both cases render the `custom` template of `adm.tblinfo`, read from
`test/resources/tables/_packages/adm/tblinfo/tpl/`, against the table picked in
the select. They differ in the output only: `renderTemplate` returns the HTML,
which the case shows; `TableTemplateToHtml` called with a string `pdf` writes
the PDF to that storage path, and the page hands its url to the client through
`gnr.downloadurl`, which starts the download.
"""

from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import TableTemplateToHtml


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_rendertemplate(self, pane):
        """HTML on screen: renderTemplate returns the template filled with the picked table"""
        pane.dbSelect(value='^.tblid', dbtable='adm.tblinfo', lbl='Table')
        pane.button('Render', action='FIRE .render')
        pane.dataRpc('.html', self.renderTemplate, _fired='^.render',
                     table='adm.tblinfo', record_id='=.tblid', tplname='custom',
                     _if='record_id', _else='return "Pick a table first"')
        pane.div('^.html')

    def test_1_button(self, pane):
        """PDF download: the same template written to page:tblinfo.pdf, then downloaded"""
        pane.dbSelect(value='^.tblid', dbtable='adm.tblinfo', lbl='Table')
        pane.button('Download PDF', action='FIRE .download')
        pane.dataRpc(self.downloadTemplatePrint, _fired='^.download',
                     table='adm.tblinfo', record_id='=.tblid', tplname='custom',
                     _if='record_id')

    @public_method
    def downloadTemplatePrint(self, table=None, tplname=None, record_id=None, **kwargs):
        htmlbuilder = TableTemplateToHtml(page=self, table=self.db.table(table))
        htmlbuilder(record=record_id, template=self.tableTemplate(table=table, tplname=tplname),
                    pdf='page:tblinfo.pdf')
        self.setInClientData('gnr.downloadurl', self.site.storageNode('page:tblinfo.pdf').url(),
                             fired=True)
