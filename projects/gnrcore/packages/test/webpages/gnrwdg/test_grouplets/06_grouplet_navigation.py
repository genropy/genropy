# -*- coding: utf-8 -*-

"""Test page for grouplet navigation: groupletPanel (tree/multiButton),
groupletWizard, collapsible grid, and tree-based menu selection."""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletHandler,
                     th/th:TableHandler"""

    # --- GroupletPanel ---

    def test_1_panel_tree(self, pane):
        """groupletPanel in tree mode: dialogTableHandler on myprospect with full grouplet tree"""
        pane.borderContainer(height='500px').contentPane(
            region='center').dialogTableHandler(
            table='test.myprospect',
            datapath='.prospect_tree',
            viewResource='View',
            formResource='Form',
            view_store__onStart=True)

    def test_2_panel_multibutton_table(self, pane):
        """groupletPanel with topic and table: multiButton selector for technical grouplets"""
        pane.borderContainer(height='500px', border='1px solid silver',
                         datapath='.panel_mb').groupletPanel(
            table='test.myticket',
            topic='technical',
            value='^.data',
            frameCode='mb_table_panel', region='center')

    def test_3_panel_multibutton_no_table(self, pane):
        """groupletPanel with topic, no table: multiButton selector for app grouplets, and no form"""
        pane.borderContainer(height='500px', border='1px solid silver',
                         datapath='.panel_app').groupletPanel(
            topic='app',
            useForm=False,
            value='^.record',
            frameCode='mb_app_panel', region='center')

    # --- GroupletWizard ---

    def test_4_wizard_booking(self, pane):
        """Booking wizard: dialogTableHandler with wizard form"""
        pane.borderContainer(height='500px').contentPane(
            region='center').dialogTableHandler(
            table='test.booking',
            datapath='.booking',
            viewResource='View',
            formResource='Form',
            view_store__onStart=True)


    def test_6_collapsible_grid(self, pane):
        """myprospect with collapsible topic-grid form (FormGrid resource)"""
        pane.borderContainer(height='500px').contentPane(
            region='center').dialogTableHandler(
            table='test.myprospect',
            datapath='.prospect_collapsible',
            viewResource='View',
            formResource='FormGrid',
            view_store__onStart=True)

    # --- Menu navigation ---

    def test_7_menu_tree(self, pane):
        """Navigate grouplets via tree menu: click a grouplet caption in the tree
        to render it in the center panel."""
        bc = pane.borderContainer(height='500px', border='1px solid silver',
                                  datapath='.comune_menu')

        left = bc.contentPane(region='left', width='220px',
                              splitter=True, border_right='1px solid silver',
                              padding='10px')
        left.dataRpc('.grouplets_menu', self.gr_getGroupletMenu,
                       table='glbl.comune', _onStart=True)
        left.tree(storepath='.grouplets_menu',
                  hideValues=True,
                  labelAttribute='caption',
                  selectedLabelClass='selectedTreeNode',
                  openOnClick=True,
                  getLabelClass="""
                      if(!node.attr.grouplet_caption){ return 'setting_group'; }
                  """,
                  connect_onClick="""
                      if($2.item.attr.resource && $2.item.attr.grouplet_caption){
                          SET .selected_resource = $2.item.attr.resource;
                          SET .selected_caption = $2.item.attr.grouplet_caption;
                      }
                  """)

        right = bc.borderContainer(region='center')
        top = right.contentPane(region='top', height='30px',
                                padding='5px', border_bottom='1px solid silver')
        top.div('^.selected_caption',
                font_weight='bold', font_size='1.2em')
        right.contentPane(region='center', overflow='auto').grouplet(
            resource='^.selected_resource',
            table='glbl.comune',
            value='^.data')

    def test_8_menu_topic_filter(self, pane):
        """Grouplet menu filtered by topic: tree shows only grouplets within 'technical'"""
        bc = pane.borderContainer(height='500px', border='1px solid silver',
                                  datapath='.ticket_topic_menu')

        left = bc.contentPane(region='left', width='220px',
                              splitter=True, border_right='1px solid silver',
                              padding='10px')
        left.dataRpc('.topic_menu', self.gr_getGroupletMenu,
                       table='test.myticket', topic='technical', _onStart=True)
        left.tree(storepath='.topic_menu',
                  hideValues=True,
                  labelAttribute='caption',
                  selectedLabelClass='selectedTreeNode',
                  openOnClick=True,
                  connect_onClick="""
                      if($2.item.attr.resource && $2.item.attr.grouplet_caption){
                          SET .selected_resource = $2.item.attr.resource;
                          SET .selected_caption = $2.item.attr.grouplet_caption;
                      }
                  """)

        right = bc.borderContainer(region='center')
        top = right.contentPane(region='top', height='30px',
                                padding='5px', border_bottom='1px solid silver')
        top.div('^.selected_caption',
                font_weight='bold', font_size='1.2em')
        right.contentPane(region='center', overflow='auto').grouplet(
            resource='^.selected_resource',
            table='test.myticket',
            value='^.data')

    def test_9_menu_multibutton(self, pane):
        """Non-table grouplet menu with topic: multiButton selection from grouplets/app"""
        frame = pane.framePane(frameCode='app_grouplet_frame',
                               height='500px', border='1px solid silver',
                               datapath='.app_grouplet')
        bar = frame.top.slotBar('*,mb,*', _class='mobile_bar')
        bar.dataRpc('.app_menu', self.gr_getGroupletMenu,
                    topic='app', _onStart=True)
        bar.mb.multibutton(value='^.selected_code', storepath='.app_menu')
        bar.dataController("""
            if(code){
                var node = menu.getNode(code);
                if(node){ SET .selected_resource = node.attr.resource; }
            }
        """, code='^.selected_code', menu='=.app_menu')
        frame.center.contentPane(overflow='auto').grouplet(
            resource='^.selected_resource',
            value='^.record')

    def test_10_menu_dialog_table(self, pane):
        """Ticket system: form_add menu creates typed tickets with dynamic grouplet"""
        pane.borderContainer(height='500px').contentPane(
            region='center').dialogTableHandler(
            table='test.myticket',
            datapath='.tickets',
            viewResource='View',
            formResource='Form',
            view_store__onStart=True)
