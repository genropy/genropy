# -*- coding: utf-8 -*-

"""Test page for topic-as-resource in grouplet: passing a topic folder
instead of a single grouplet file to the grouplet widget renders a CSS grid
with all child grouplets, each with a caption header."""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet:GroupletHandler,
                     th/th:TableHandler"""

    def _comune_form(self, pane, frameCode, datapath):
        """Shared form setup for glbl.comune table"""
        form = pane.frameForm(frameCode=frameCode,
                             height='500px',
                             datapath=datapath,
                             border='1px solid silver',
                             pkeyPath='.comune_pkey',
                             _anchor=True)
        form.formStore(table='glbl.comune', storeType='Item',
                      handler='recordCluster', startKey='*norecord*')
        bar = form.top.slotToolbar('5,selector,*,semaphore,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.comune_pkey', dbtable='glbl.comune',
                   parentForm=False,
                   validate_onAccept="if(userChange){"
                   "this.getParentNode().form.publish('load',{destPkey:value})}",
                   lbl='Comune')
        return form

    def _prospect_form(self, pane, frameCode, datapath):
        """Shared form setup for myprospect table"""
        form = pane.frameForm(frameCode=frameCode,
                             height='500px',
                             datapath=datapath,
                             border='1px solid silver',
                             pkeyPath='.prospect_pkey',
                             _anchor=True)
        form.formStore(table='test.myprospect', storeType='Item',
                      handler='recordCluster', startKey='*norecord*')
        bar = form.top.slotToolbar('5,selector,*,semaphore,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.prospect_pkey', dbtable='test.myprospect',
                   parentForm=False,
                   validate_onAccept="if(userChange){"
                   "this.getParentNode().form.publish('load',{destPkey:value})}",
                   lbl='Prospect')
        return form

    def test_1_topic_grid_columns(self, pane):
        """Topic as resource with grid_columns=2: technical grouplets in two-column grid"""
        pane.grouplet(
            resource='technical',
            table='test.myticket',
            value='^.data',
            remote_grid_columns=2)

    def test_2_topic_grid_collapsible(self, pane):
        """Topic as resource with collapsible cells: click caption to toggle"""
        pane.grouplet(
            resource='technical',
            table='test.myticket',
            value='^.data',
            remote_grid_collapsible=True)

    def test_3_topic_grid_custom_template(self, pane):
        """Topic as resource with custom grid_template_columns and gap"""
        pane.grouplet(
            resource='commercial',
            table='test.myticket',
            value='^.data',
            remote_grid_template_columns='1fr 2fr',
            remote_grid_gap='16px')

    def test_4_topic_grid_no_table(self, pane):
        """Topic as resource without table: app-level grouplets in grid"""
        pane.borderContainer(height='500px', border='1px solid silver',
                         datapath='.app_grid').contentPane(
            region='center', overflow='auto').grouplet(
            resource='app',
            value='^.record',
            remote_grid_columns=3)

    def test_5_topic_grid_territorio(self, pane):
        """Nested topic as resource: territorio sub-topic of glbl.comune grouplets"""
        pane.grouplet(
            resource='territorio',
            table='glbl.comune',
            value='^.data',
            remote_grid_columns=2,
            remote_grid_collapsible=True)

    def test_6_chunk_topic_comune(self, pane):
        """groupletChunk in comune form: territorio topic chunk showing
        summary template that updates on dialog edit"""
        form = self._comune_form(pane, 'dlg_chunk_comune', '.dlg_comune')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='glbl.comune')
        fb.field('denominazione', colspan=2, width='100%')
        fb.field('sigla_provincia')
        fb.field('codice_comune')
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Territorio',
                           height='60px')
        chunk_pane.groupletChunk(
            value='^#FORM.record',
            template="""<div style="color:#555;">
                ${<span>Zona: $zona_altimetrica</span>}
                ${<span> | Alt. $altitudine m</span>}
            </div>
            ${<div style="color:#555;">Montano: $comune_montano</div>}""",
            name='edit_territorio_topic',
            resource='territorio',
            table='glbl.comune',
            title='Territorio',
            remote_grid_columns=2,
            remote_grid_collapsible=True)

    def test_7_chunk_topics_prospect(self, pane):
        """groupletChunk in prospect form: three topic chunks (company, needs, budget)
        each showing a summary template that updates on dialog edit"""
        form = self._prospect_form(pane, 'dlg_chunks', '.dlg_chunks')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='test.myprospect')
        fb.field('company_name', colspan=2, width='100%')
        fb.field('contact_name')
        fb.field('contact_email')
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Company Profile',
                           height='60px')
        chunk_pane.groupletChunk(
            value='^#FORM.record.extra_data',
            template='<div style="color:#555;">'
                     '${<b>$industry</b>}'
                     '${<span> ($company_size)</span>}'
                     '</div>',
            name='edit_company_topic',
            resource='company',
            table='test.myprospect',
            title='Company Profile',
            remote_grid_columns=2)
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Needs Assessment',
                           height='50px')
        chunk_pane.groupletChunk(
            value='^#FORM.record.extra_data',
            template='<div style="color:#555;">'
                     '${<span>Urgency: <b>$urgency</b></span>}'
                     '${<span> | $impact_area</span>}'
                     '</div>',
            name='edit_needs_topic',
            resource='needs',
            table='test.myprospect',
            title='Needs Assessment')
        chunk_pane = fb.div(colspan=2, width='100%',
                            lbl='Budget & Timeline', height='50px')
        chunk_pane.groupletChunk(
            value='^#FORM.record.extra_data',
            name='edit_budget_auto',
            resource='budget',
            table='test.myprospect',
            title='Budget & Timeline',
            grid_columns=2)

    def test_8_chunk_topic_no_table(self, pane):
        """groupletChunk dialog with topic, no table: app grouplets in dialog grid"""
        pane.borderContainer(height='500px', border='1px solid silver',
                         datapath='.dlg_app').contentPane(
            region='center', padding='10px').groupletChunk(
            value='^.record',
            template='<div style="color:#555;">'
                     '${<span>App: $app_name</span>}'
                     '</div>',
            name='edit_app_topic',
            resource='app',
            title='App Configuration',
            remote_grid_columns=3)
