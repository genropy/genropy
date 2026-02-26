# -*- coding: utf-8 -*-

"""Test page for topic-as-resource in grouplet: passing a topic folder
instead of a single grouplet file to the grouplet widget renders a CSS grid
with all child grouplets, each with a caption header."""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet:GroupletHandler,
                     th/th:TableHandler"""

    def _ticket_form(self, pane, frameCode, datapath):
        """Shared form setup for myticket table"""
        form = pane.frameForm(frameCode=frameCode,
                             height='500px',
                             datapath=datapath,
                             border='1px solid silver',
                             pkeyPath='.ticket_pkey',
                             _anchor=True)
        form.formStore(table='test.myticket', storeType='Item',
                      handler='recordCluster', startKey='*norecord*')
        bar = form.top.slotToolbar('5,selector,*,semaphore,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.ticket_pkey', dbtable='test.myticket',
                   parentForm=False,
                   validate_onAccept="if(userChange){"
                   "this.getParentNode().form.publish('load',{destPkey:value})}",
                   lbl='Ticket')
        return form

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

    def test_1_topic_grid_columns(self, pane):
        """Topic as resource with grid_columns=2: technical grouplets in two-column grid"""
        form = self._ticket_form(pane, 'topic_grid_2col', '.grid_2col')
        form.center.contentPane(overflow='auto').grouplet(
            resource='technical',
            table='test.myticket',
            value='^.record.extra_data',
            remote_grid_columns=2)

    def test_2_topic_grid_collapsible(self, pane):
        """Topic as resource with collapsible cells: click caption to toggle"""
        form = self._ticket_form(pane, 'topic_grid_collapse', '.grid_collapse')
        form.center.contentPane(overflow='auto').grouplet(
            resource='technical',
            table='test.myticket',
            value='^.record.extra_data',
            remote_grid_collapsible=True)

    def test_3_topic_grid_custom_template(self, pane):
        """Topic as resource with custom grid_template_columns and gap"""
        form = self._ticket_form(pane, 'topic_grid_custom', '.grid_custom')
        form.center.contentPane(overflow='auto').grouplet(
            resource='commercial',
            table='test.myticket',
            value='^.record.extra_data',
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
        form = self._comune_form(pane, 'topic_grid_terr', '.grid_terr')
        form.center.contentPane(overflow='auto').grouplet(
            resource='territorio',
            table='glbl.comune',
            value='^.record',
            remote_grid_columns=2,
            remote_grid_collapsible=True)

    def test_6_chunk_topic_technical(self, pane):
        """groupletChunk dialog with topic: click opens dialog with technical grouplets grid"""
        form = self._ticket_form(pane, 'dlg_topic_tech', '.dlg_tech')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='test.myticket')
        fb.field('subject', colspan=2, width='100%')
        fb.field('ticket_type', tag='filteringSelect',
                 values='technical:Technical,commercial:Commercial,'
                        'administrative:Administrative')
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Technical Details',
                           height='60px')
        chunk_pane.groupletChunk(
            value='^#FORM.record.extra_data',
            template='<div style="color:#555;">'
                     '${<span>OS: $operating_system</span>}'
                     '${<span> | Error: $error_code</span>}'
                     '</div>',
            name='edit_technical_topic',
            resource='technical',
            table='test.myticket',
            title='Technical Details',
            remote_grid_columns=2)

    def test_7_chunk_topic_commercial(self, pane):
        """groupletChunk dialog with topic: commercial grouplets in single-column dialog"""
        form = self._ticket_form(pane, 'dlg_topic_comm', '.dlg_comm')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='test.myticket')
        fb.field('subject', colspan=2, width='100%')
        fb.field('ticket_type', tag='filteringSelect',
                 values='technical:Technical,commercial:Commercial,'
                        'administrative:Administrative')
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Commercial Info',
                           height='50px')
        chunk_pane.groupletChunk(
            value='^#FORM.record.extra_data',
            template='<div style="color:#555;">'
                     '${<b>$company_name</b>}'
                     '${<span> - $estimated_budget</span>}'
                     '</div>',
            name='edit_commercial_topic',
            resource='commercial',
            table='test.myticket',
            title='Commercial Info')

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

    def test_9_chunk_topic_auto_template(self, pane):
        """groupletChunk with topic: template auto-discovered from __info__.py"""
        form = self._ticket_form(pane, 'chunk_auto_tpl', '.chunk_auto')
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, border_spacing='3px',
                               table='test.myticket')
        fb.field('subject', colspan=2, width='100%')
        fb.field('ticket_type', tag='filteringSelect',
                 values='technical:Technical,commercial:Commercial,'
                        'administrative:Administrative')
        chunk_pane = fb.div(colspan=2, width='100%',
                            lbl='Commercial (auto template)', height='50px')
        chunk_pane.groupletChunk(
            value='^#FORM.record.extra_data',
            name='edit_comm_auto',
            resource='commercial',
            table='test.myticket',
            title='Commercial Details',
            grid_columns=2)
