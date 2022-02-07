# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import TableTemplateToHtml

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/pagededitor/pagededitor:PagedEditor"

    def test_0_pagedEditor(self, pane):
        "Use pagedEditor to customize a template directly in the preview, managing pagination"
        bc = pane.borderContainer(height='600px')
        bar = bc.contentPane(region='top').slotBar('10,fbpars,*', height='20px', border_bottom='1px solid silver')
        fb = bar.fbpars.formbuilder(datapath='.htmlbag')
        fb.dbselect('^.pkey', table='fatt.fattura', lbl='!![it]Fattura', hasDownArrow=True)
        fb.dbselect(value='^.record_template', lbl='Template code', table='adm.userobject',
                        condition='$tbl=:tbl AND $objtype=:objtype',
                        condition_tbl='fatt.fattura', alternatePkey='code',
                        condition_objtype='template', hasDownArrow=True)
        fb.dbselect('^.letterhead_id', table='adm.htmltemplate',   
                            lbl='!![it]Carta intestata', hasDownArrow=True)
        fb.button('Get HTML DOC').dataRpc('.source',self.getHTMLDoc,
                                            fattura_id='=.pkey',
                                            record_template='=.record_template',
                                            letterhead_id='=.letterhead_id')
        bc.contentPane(region='center').pagedEditor(
                        value='^.htmlbag.source',
                        pagedText='^.htmlbag.output',
                        border='1px solid silver',
                        letterhead_id='^.htmlbag.letterhead_id',
                        extra_bottom=10,
                        editor_constrain_width='210mm',
                        editor_constrain_min_height='297mm',
                        editor_constrain_border='1px solid silver',
                        editor_constrain_margin='4px')

    @public_method
    def getHTMLDoc(self, fattura_id=None,record_template=None,**kwargs):
        tbl=self.db.table('fatt.fattura')
        text = TableTemplateToHtml(table=tbl,record_template=record_template).contentFromTemplate(record=fattura_id)
        return text