# -*- coding: utf-8 -*-

"""Test page for groupletPanel and groupletWizard components"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet:GroupletHandler,
                     th/th:TableHandler"""

    def test_1_panel_tree_mode(self, pane):
        """groupletPanel in tree mode: dialogTableHandler on myprospect with full grouplet tree"""
        pane.borderContainer(height='500px').contentPane(
            region='center').dialogTableHandler(
            table='test.myprospect',
            datapath='.prospect_tree',
            viewResource='View',
            formResource='Form')

    def test_2_panel_multibutton_with_table(self, pane):
        """groupletPanel with topic and table: multiButton selector for technical grouplets"""
        form = pane.frameForm(frameCode='panel_mb_form',
                             border='1px solid silver',
                             datapath='.panel_mb',
                             height='500px',
                             _anchor=True,
                             pkeyPath='.ticket_pkey')
        form.formStore(table='test.myticket', storeType='Item',
                      handler='recordCluster', startKey='*norecord*')
        bar = form.top.slotToolbar('5,selector,*,semaphore,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.ticket_pkey', dbtable='test.myticket',
                   parentForm=False,
                   validate_onAccept="if(userChange){this.getParentNode().form.publish('load',{destPkey:value})}",
                   lbl='Ticket')
        form.center.contentPane().groupletPanel(
            table='test.myticket',
            topic='technical',
            value='^.record.extra_data',
            frameCode='mb_table_panel')

    def test_3_panel_multibutton_no_table(self, pane):
        """groupletPanel with topic, no table: multiButton selector for app grouplets"""
        pane.borderContainer(height='500px', border='1px solid silver',
                         datapath='.panel_app').groupletPanel(
            topic='app',
            value='^.record',
            frameCode='mb_app_panel', region='center')

    def test_4_wizard_booking(self, pane):
        """Booking wizard: dialogTableHandler with wizard form"""
        pane.borderContainer(height='500px').contentPane(
            region='center').dialogTableHandler(
            table='test.booking',
            datapath='.booking',
            viewResource='View',
            formResource='Form')

    def test_5_wizard_standalone(self, pane):
        """Standalone wizard with app topic, no external form"""
        pane.borderContainer(height='500px', border='1px solid silver',
                         datapath='.wizard_app').groupletWizard(
            topic='app',
            value='^.record',
            frameCode='app_wizard', region='center')

    def test_6_prospect_collapsible_grid(self, pane):
        """myprospect with collapsible topic-grid form (FormGrid resource)"""
        pane.borderContainer(height='500px').contentPane(
            region='center').dialogTableHandler(
            table='test.myprospect',
            datapath='.prospect_collapsible',
            viewResource='View',
            formResource='FormGrid')

    def test_7_dialog_topic_grid(self, pane):
        """groupletChunk dialog: click opens dialog with commercial topic in 2-column grid"""
        form = pane.frameForm(frameCode='dlg_grid_form',
                             border='1px solid silver',
                             datapath='.dlg_grid',
                             height='500px',
                             _anchor=True,
                             pkeyPath='.ticket_pkey')
        form.formStore(table='test.myticket', storeType='Item',
                      handler='recordCluster', startKey='*norecord*')
        bar = form.top.slotToolbar('5,selector,*,semaphore,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.ticket_pkey', dbtable='test.myticket',
                   parentForm=False,
                   validate_onAccept="if(userChange){"
                   "this.getParentNode().form.publish('load',{destPkey:value})}",
                   lbl='Ticket')
        center = form.center.contentPane(padding='10px', datapath='.record')
        ffb = center.formlet(cols=2, border_spacing='3px',
                                table='test.myticket')
        ffb.field('subject', colspan=2, width='100%')
        ffb.field('ticket_type', tag='filteringSelect',
                 values='technical:Technical,commercial:Commercial,'
                        'administrative:Administrative')
        chunk_pane = ffb.div(colspan=2, width='100%',
                            lbl='Commercial Details', height='50px')
        chunk_pane.groupletChunk(
            value='^#FORM.record.extra_data',
            template='<div style="color:#555;">'
                     '${<b>$company_name</b>}'
                     '${<span> - $estimated_budget</span>}'
                     '</div>',
            name='edit_comm_grid',
            resource='commercial',
            table='test.myticket',
            title='Commercial Details',
            remote_grid_columns=2)
