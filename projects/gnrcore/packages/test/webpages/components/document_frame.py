# -*- coding: utf-8 -*-

"""documentFrame

A documentFrame shows a print resource of a table as HTML or PDF inside the page.
The first three cases print a single record of the `fatt` package; the last one prints
the current selection of a TableHandler grid, with its columns, through the
`print_gridres` resource every table inherits from `_default`.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     th/th:TableHandler"""

    def test_0_docHTML(self, pane):
        "Use documentFrame to show HTML print files"
        self.printDisplay(pane.framePane(title='Stampa HTML', height='400px', datapath='.embed_document'), 
                            resource='fatt.fattura:html_res/mia_fattura',html=True)

    def test_1_docPDF(self, pane):
        "Use documentFrame to show PDF print files"
        self.printDisplay(pane.framePane(title='Stampa HTML', height='400px', datapath='.embed_document'), 
                            resource='fatt.fattura:html_res/mia_fattura',html=False)

    def test_2_docTPL(self, pane):
        """Use documentFrame to show template-generated print files. 
        Please create a 'fattura_template' html resource first, which specifies a record_template file"""
        self.printDisplay(pane.framePane(title='Stampa HTML', height='400px', datapath='.embed_document'), 
                            resource='fatt.fattura:html_res/fattura_template',html=True)

    def printDisplay(self, frame, resource=None, html=None):
        bar = frame.top.slotBar('10,lett_select,*', height='20px', border_bottom='1px solid silver')
        fb = bar.lett_select.formbuilder(cols=2)
        fb.dbselect('^.curr_letterhead_id', table='adm.htmltemplate',   
                            lbl='!![it]Carta intestata', hasDownArrow=True)
        fb.dbselect('^.pkey', table='fatt.fattura', lbl='!![it]Fattura', hasDownArrow=True)
        frame.documentFrame(resource=resource,
                          pkey='^.pkey',
                          html=html,
                          letterhead_id='^.curr_letterhead_id',
                          missingContent='NO FATTURA',
                          _if='pkey', _delay=100)

    def test_3_grid_print_preview(self, pane):
        """Print preview of a grid: run a query in the adm.tblinfo grid (the Limit field of the
        extended query caps the rows) and the documentFrame below prints the same rows with the
        grid's current columns, through adm.tblinfo:html_res/print_gridres."""
        bc = pane.borderContainer(height='700px')
        top = bc.contentPane(region='top', height='50%', border_bottom='1px solid silver')
        th = top.plainTableHandler(table='adm.tblinfo', extendedQuery=True, datapath='.myth')
        th.dataFormula('.queryBag',
                       """new gnr.GnrBag({where:_queryWhere.deepCopy(),queryLimit:_queryLimit,
                                          customOrderBy:_customOrderBy});""",
                       _if='_queryWhere',
                       _queryWhere='^.view.query.where',
                       _queryLimit='^.view.query.limit',
                       _customOrderBy='^.view.query.customOrderBy')
        gridId = th.view.grid.attributes['nodeId']
        bc.contentPane(region='center').documentFrame(resource='adm.tblinfo:html_res/print_gridres',
                                                      pkey='*', html=True, httpMethod='POST',
                                                      currentGridStruct='==genro.wdgById("%s").getExportStruct();' % gridId,
                                                      currentQuery='=.myth.queryBag',
                                                      _if='currentGridStruct',
                                                      _fired='^.myth.view.runQueryDo', _delay=100)
