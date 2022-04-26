# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

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