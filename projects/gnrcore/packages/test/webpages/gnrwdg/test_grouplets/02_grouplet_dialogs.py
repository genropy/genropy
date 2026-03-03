# -*- coding: utf-8 -*-

"""Test page for Grouplet dialog editors (memoryDataEditor, documentDataEditor, recordDataEditor)"""

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler"""

    def test_1_memoryDataEditor(self, pane):
        """memoryDataEditor: edit form data in a dialog, write back on confirm"""
        pane.data('.mydata', Bag(dict(
            name='Mario', surname='Rossi',
            street='Via Roma 1', city='Milano',
            zip='20100', country='Italia'
        )))
        form = pane.frameForm(frameCode='mem_form',
                             height='400px', width='600px',
                             datapath='.memform',
                             border='1px solid silver')
        form.formStore(storeType='Item', handler='memory', locationpath='.#parent.mydata',)
        bar = form.top.slotToolbar('edit_btn,*,semaphore,formcommands')
        bar.edit_btn.button('Edit Address').dataController(
            """genro.dlg.memoryDataEditor('address', {value:'^#FORM.record',handler:grp_handler,title:'Edit Address'},this)""",
            grp_handler=self.grp_address)
        fb = form.record.formlet(cols=1)
        fb.textbox(value='^.name', lbl='Name')
        fb.textbox(value='^.surname', lbl='Surname')
        fb.textbox(value='^.street', lbl='Street', readOnly=True)
        fb.textbox(value='^.city', lbl='City', readOnly=True)
        fb.dataController("this.form.load()",_onStart=True)

    def test_2_documentDataEditor(self, pane):
        """documentDataEditor: edit a document by path"""
        fb = pane.formlet(cols=1)
        fb.textbox(value='^.doc_path', lbl='Document path',
                  default_value='pkg:test15/testdata/docstore/doc1.xml')
        fb.button('Edit Document').dataController(
            "genro.dlg.documentDataEditor('doc_edit', {path:doc_path, handler:grp_handler,title:'Edit Document'}, this)",
            doc_path='=.doc_path',
            grp_handler=self.grp_document)

    def test_3_recordDataEditor(self, pane):
        """recordDataEditor: edit a database record with inline handler"""
        fb = pane.formlet(cols=1)
        fb.dbselect(value='^.selected_comune', table='glbl.comune',
                   lbl='Select Comune')
        fb.button('Edit Comune').dataController(
            "genro.dlg.recordDataEditor('comune_edit', {table:'glbl.comune', pkey:comune_pkey, handler:grp_handler,title:'Edit Comune'},this)",
            comune_pkey='=.selected_comune',
            grp_handler=self.grp_comune)

    def test_4_recordDataEditor_resource(self, pane):
        """recordDataEditor: edit using a table resource grouplet"""
        fb = pane.formlet(cols=1)
        fb.dbselect(value='^.selected_comune_2', table='glbl.comune',
                   lbl='Select Comune')
        fb.button('Edit Comune (resource)').dataController(
            "genro.dlg.recordDataEditor('comune_res', {table:'glbl.comune', pkey:comune_pkey, resource:'anagrafica', title:'Edit Comune - Anagrafica'}, this)",
            comune_pkey='=.selected_comune_2')

    def test_5_recordDataEditor_territorio(self, pane):
        """recordDataEditor: edit comune territorio using nested resource grouplet"""
        fb = pane.formlet(cols=1)
        fb.dbselect(value='^.selected_comune_3', table='glbl.comune',
                   lbl='Select Comune')
        fb.button('Edit Comune (territorio)').dataController(
            "genro.dlg.recordDataEditor('comune_terr', {table:'glbl.comune', pkey:comune_pkey, resource:'territorio/altimetria', title:'Edit Comune - Altimetria'}, this)",
            comune_pkey='=.selected_comune_3')

    @public_method
    def grp_address(self, pane, **kwargs):
        fb = pane.formlet(cols=3)
        fb.textbox(value='^.street', lbl='Street')
        fb.textbox(value='^.city', lbl='City')
        fb.textbox(value='^.zip', lbl='ZIP')
        fb.textbox(value='^.country', lbl='Country')

    @public_method
    def grp_document(self, pane, **kwargs):
        fb = pane.formlet(cols=3)
        fb.textbox(value='^.name', lbl='Name')
        fb.textbox(value='^.description', lbl='Description')
        fb.dateTextBox(value='^.date', lbl='Date')

    @public_method
    def grp_comune(self, pane, **kwargs):
        fb = pane.formlet(cols=2, table='glbl.comune')
        fb.field('denominazione', colspan=2, width='100%')
        fb.field('sigla_provincia')
        fb.field('codice_comune')
        fb.field('capoluogo')
