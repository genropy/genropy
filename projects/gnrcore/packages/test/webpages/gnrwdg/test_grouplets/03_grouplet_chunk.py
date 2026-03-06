# -*- coding: utf-8 -*-

"""Test page for groupletChunk struct_method: inline summary template with
click-to-edit dialog, using handlers and resource grouplets.
Each test shows the chunk embedded in a comune form to demonstrate
how editing in the dialog updates the surrounding form."""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletHandler"""

    def _comune_form(self, pane, frameCode, datapath):
        """Shared form setup: frameForm + formStore + dbselect selector"""
        form = pane.frameForm(frameCode=frameCode,
                             height='500px', width='700px',
                             datapath=datapath,
                             border='1px solid silver',
                             pkeyPath='.comune_pkey',
                             _anchor=True)
        form.formStore(table='glbl.comune', storeType='Item',
                      handler='recordCluster', startKey='*norecord*')
        bar = form.top.slotToolbar('5,selector,*,semaphore,locker,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.comune_pkey', table='glbl.comune',
                   parentForm=False,
                   validate_onAccept="""if(userChange){
                       this.getParentNode().form.publish('load',{destPkey:value})
                   }""",
                   lbl='Comune')
        return form

    def test_1_chunk_with_handler(self, pane):
        """Editable fields + groupletChunk with handler for extra data"""
        form = self._comune_form(pane, 'chunk_handler', '.handler_form')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='glbl.comune')
        fb.field('denominazione', colspan=2, width='100%')
        fb.field('sigla_provincia')
        fb.field('codice_comune')
        fb.field('capoluogo')
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Territorio',
                           height='60px')
        chunk_pane.groupletChunk(
            value='^#FORM.record',
            template="""
            <div style="color:#555;">
                ${<span>Zona altimetrica: $zona_altimetrica</span>}
                ${<span style="margin-left:8px;">Alt. $altitudine m</span>}
            </div>
            ${<div style="color:#555;">Comune montano: $comune_montano</div>}
            """,
            name='edit_territorio',
            handler=self.grp_territorio,
            title='Edit Territorio')

    def test_2_chunk_with_resource(self, pane):
        """Editable fields + groupletChunk with resource grouplet"""
        form = self._comune_form(pane, 'chunk_resource', '.resource_form')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='glbl.comune')
        fb.field('zona_altimetrica')
        fb.field('altitudine')
        fb.field('comune_montano')
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Anagrafica',
                           height='50px')
        chunk_pane.groupletChunk(
            value='^#FORM.record',
            template="""
            <div style="font-weight:bold;">$denominazione</div>
            <div style="color:#555;">$sigla_provincia - $codice_comune</div>
            """,
            name='edit_anagrafica_res',
            resource='anagrafica',
            table='glbl.comune',
            title='Edit Anagrafica')

    def test_3_chunk_with_box_kwargs(self, pane):
        """Editable fields + groupletChunk with box_ kwargs and virtual_columns"""
        form = self._comune_form(pane, 'chunk_box', '.box_form')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='glbl.comune')
        fb.field('denominazione', colspan=2, width='100%')
        fb.field('capoluogo')
        fb.field('comune_montano')
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Dettagli',
                           height='70px')
        chunk_pane.groupletChunk(
            value='^#FORM.record',
            template="""
            <div>$sigla_provincia - $codice_comune</div>
            <div style="color:#555;">
                ${<span>Altitudine: $altitudine m</span>}
                ${<span style="margin-left:8px;">Zona: $zona_altimetrica</span>}
            </div>
            """,
            name='edit_dettagli',
            handler=self.grp_dettagli,
            title='Edit Dettagli',
            virtual_columns='zona_altimetrica,altitudine',
            box_padding='5px',
            box_background='#f9f9f9',
            box_border_radius='4px')

    def test_4_chunk_with_resource_template(self, pane):
        """groupletChunk auto-discovers template and virtual_columns from resource"""
        form = self._comune_form(pane, 'chunk_res_tpl', '.res_tpl_form')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='glbl.comune')
        fb.field('denominazione', colspan=2, width='100%')
        fb.field('capoluogo')
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Codici',
                           height='50px')
        chunk_pane.groupletChunk(
            value='^#FORM.record',
            name='edit_codici_auto',
            resource='codici',
            table='glbl.comune',
            title='Edit Codici')

    def _prospect_form(self, pane, frameCode, datapath):
        """Shared form setup for myprospect table"""
        form = pane.frameForm(frameCode=frameCode,
                             height='500px', width='700px',
                             datapath=datapath,
                             border='1px solid silver',
                             pkeyPath='.prospect_pkey',
                             _anchor=True)
        form.formStore(table='test.myprospect', storeType='Item',
                      handler='recordCluster', startKey='*norecord*')
        bar = form.top.slotToolbar('5,selector,*,semaphore,locker,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.prospect_pkey', dbtable='test.myprospect',
                   parentForm=False,
                   validate_onAccept="""if(userChange){
                       this.getParentNode().form.publish('load',{destPkey:value})
                   }""",
                   lbl='Prospect')
        return form

    def test_5_chunk_prospect_topics(self, pane):
        """Prospect form with three topic chunks: company, needs, budget.
        Each chunk uses the template from its topic __info__.py and
        fills on record selection."""
        form = self._prospect_form(pane, 'chunk_prospect', '.prospect_form')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='test.myprospect')
        fb.field('company_name', colspan=2, width='100%')
        fb.field('contact_name')
        fb.field('contact_email')
        fb.groupletChunk(
            value='^#FORM.record.extra_data.company',
            name='edit_company_topic',
            resource='company',
            table='test.myprospect',
            title='Company Profile',
            remote_grid_columns=2,
            colspan=2, lbl='Company Profile')
        fb.groupletChunk(
            value='^#FORM.record.extra_data.needs',
            name='edit_needs_topic',
            resource='needs',
            table='test.myprospect',
            title='Needs Assessment',
            grid_columns=2,
            colspan=2, lbl='Needs Assessment')
        fb.groupletChunk(
            value='^#FORM.record.extra_data.budget',
            name='edit_budget_topic',
            resource='budget',
            table='test.myprospect',
            title='Budget & Timeline',
            grid_columns=2,
            colspan=2, lbl='Budget & Timeline')

    @public_method
    def grp_territorio(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px',
                             table='glbl.comune')
        fb.field('zona_altimetrica')
        fb.field('altitudine')
        fb.field('comune_montano')

    @public_method
    def grp_dettagli(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px',
                             table='glbl.comune')
        fb.field('sigla_provincia')
        fb.field('codice_comune')
        fb.field('zona_altimetrica')
        fb.field('altitudine')
