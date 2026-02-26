# -*- coding: utf-8 -*-

"""Test page for GroupletForm widget: inline form with store capabilities wrapping a grouplet"""

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet:GroupletHandler"""

    def test_1_groupletform_memory_handler(self, pane):
        """Inline GroupletForm with memory store and handler"""
        pane.data('.address_data', Bag(dict(
            street='Via Roma 1', city='Milano',
            zip='20100', country='Italia'
        )))
        frame = pane.framePane(frameCode='mem_gf',
                               height='400px', border='1px solid silver',
                               datapath='.mem_groupletform')
        bar = frame.top.slotToolbar('5,lbl,*')
        bar.lbl.div('In-memory address editor', font_weight='bold')
        frame.center.contentPane(padding='10px').groupletform(
            loadOnBuilt=True,
            handler=self.grp_address,value='^.#parent.address_data',
            formId='mem_gf_form')
   

    def test_2_groupletform_record_handler(self, pane):
        """Inline GroupletForm with record store and handler"""
        frame = pane.framePane(frameCode='rec_gf',
                               height='400px', border='1px solid silver',
                               datapath='.rec_groupletform')
        bar = frame.top.slotToolbar('5,selector,*')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.comune_pkey', dbtable='glbl.comune',
                   lbl='Comune')
        frame.center.contentPane(padding='10px').groupletform(
            handler=self.grp_comune_fields,value='^.current',
            table='glbl.comune',
            formId='rec_gf_form',
            store_handler='record',
            storeType='Item')
        bar.dataController(
            "if(pkey){genro.formById('rec_gf_form').load({destPkey:pkey});}",
            pkey='^.comune_pkey')

    def test_3_groupletform_record_resource(self, pane):
        """Inline GroupletForm with record store and table resource"""
        frame = pane.framePane(frameCode='res_gf',
                               height='400px', border='1px solid silver',
                               datapath='.res_groupletform')
        bar = frame.top.slotToolbar('5,selector,*')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.comune_pkey', dbtable='glbl.comune',
                   lbl='Comune')
        frame.center.contentPane(padding='10px').groupletform(
            resource='anagrafica',
            table='glbl.comune',
            formId='res_gf_form',
            store_handler='record',
            storeType='Item')
        bar.dataController(
            "if(pkey){genro.formById('res_gf_form').load({destPkey:pkey});}",
            pkey='^.comune_pkey')

    def test_4_groupletform_record_nested_resource(self, pane):
        """Inline GroupletForm with nested table resource (territorio/altimetria)"""
        frame = pane.framePane(frameCode='nested_gf',
                               height='400px', border='1px solid silver',
                               datapath='.nested_groupletform')
        bar = frame.top.slotToolbar('5,selector,*')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.comune_pkey', dbtable='glbl.comune',
                   lbl='Comune')
        frame.center.contentPane(padding='10px').groupletform(
            resource='territorio/altimetria',
            table='glbl.comune',
            formId='nested_gf_form',
            store_handler='record',
            storeType='Item')
        bar.dataController(
            "if(pkey){genro.formById('nested_gf_form').load({destPkey:pkey});}",
            pkey='^.comune_pkey')

    @public_method
    def grp_address(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='6px')
        fb.textbox(value='^.street', lbl='Street', colspan=2, width='100%')
        fb.textbox(value='^.city', lbl='City')
        fb.textbox(value='^.zip', lbl='ZIP', width='6em')
        fb.textbox(value='^.country', lbl='Country')

    @public_method
    def grp_comune_fields(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='6px',
                             table='glbl.comune')
        fb.field('denominazione', colspan=2, width='100%')
        fb.field('sigla_provincia')
        fb.field('codice_comune')
        fb.field('capoluogo')
        fb.field('comune_montano')
