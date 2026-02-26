# -*- coding: utf-8 -*-

"""Test page for Grouplet menu: tree-based grouplet selection with record form"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet:GroupletHandler,
                     th/th:TableHandler"""

    def test_1_grouplet_menu(self, pane):
        """Select a comune, load record, navigate grouplets via tree"""
        form = pane.frameForm(frameCode='comune_grp_menu',
                             border='1px solid silver',
                             datapath='.comune_form',
                             height='500px',
                             _anchor=True,
                             pkeyPath='.comune_pkey')
        form.formStore(table='glbl.comune', storeType='Item',
                      handler='recordCluster', startKey='*norecord*')
        bar = form.top.slotToolbar('5,selector,*,semaphore,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value='^.comune_pkey', dbtable='glbl.comune',
                   parentForm=False,
                   validate_onAccept="if(userChange){this.getParentNode().form.publish('load',{destPkey:value})}",
                   lbl='Comune')

        bc = form.center.borderContainer()

        left = bc.contentPane(region='left', width='220px',
                              splitter=True, border_right='1px solid silver',
                              padding='10px')
        left.dataRpc('.grouplets_menu', self.gr_getGroupletMenu,
                       table='glbl.comune', _onStart=True)
        left.tree(storepath='#FORM.grouplets_menu',
                  hideValues=True,
                  labelAttribute='caption',
                  selectedLabelClass='selectedTreeNode',
                  openOnClick=True,
                  getLabelClass="""
                      if(!node.attr.grouplet_caption){ return 'setting_group'; }
                  """,
                  connect_onClick="""
                      if($2.item.attr.resource){
                          SET #FORM.selected.resource = $2.item.attr.resource;
                          SET #FORM.selected.caption = $2.item.attr.grouplet_caption;
                      }
                  """)

        right = bc.borderContainer(region='center')
        top = right.contentPane(region='top', height='30px',
                                padding='5px', border_bottom='1px solid silver')
        top.div('^#FORM.selected.caption',
                font_weight='bold', font_size='1.2em')
        right.contentPane(region='center', overflow='auto').grouplet(
            resource='^#FORM.selected.resource',
            table='glbl.comune',
            value='^.record')

    def test_2_grouplet_menu_with_topic(self, pane):
        """Grouplet menu filtered by topic: loads only grouplets within 'technical'"""
        form = pane.frameForm(frameCode='ticket_topic_menu',
                             border='1px solid silver',
                             datapath='.ticket_topic_form',
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

        bc = form.center.borderContainer()

        left = bc.contentPane(region='left', width='220px',
                              splitter=True, border_right='1px solid silver',
                              padding='10px')
        left.dataRpc('.topic_menu', self.gr_getGroupletMenu,
                       table='test.myticket', topic='technical', _onStart=True)
        left.tree(storepath='#FORM.topic_menu',
                  hideValues=True,
                  labelAttribute='caption',
                  selectedLabelClass='selectedTreeNode',
                  openOnClick=True,
                  connect_onClick="""
                      if($2.item.attr.resource){
                          SET #FORM.selected.resource = $2.item.attr.resource;
                          SET #FORM.selected.caption = $2.item.attr.grouplet_caption;
                      }
                  """)

        right = bc.borderContainer(region='center')
        top = right.contentPane(region='top', height='30px',
                                padding='5px', border_bottom='1px solid silver')
        top.div('^#FORM.selected.caption',
                font_weight='bold', font_size='1.2em')
        right.contentPane(region='center', overflow='auto').grouplet(
            resource='^#FORM.selected.resource',
            table='test.myticket',
            value='^.record')

    def test_3_grouplet_menu_no_table_with_topic(self, pane):
        """Non-table grouplet menu with topic: multiButton selection from grouplets/app"""
        frame = pane.framePane(frameCode='app_grouplet_frame',
                               height='500px', border='1px solid silver',
                               datapath='.app_grouplet')
        bar = frame.top.slotBar('*,mb,*',_class='mobile_bar')
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

    def test_4_myticket(self, pane):
        """Ticket system: form_add menu creates typed tickets with dynamic grouplet"""
        pane.borderContainer(height='500px').contentPane(region='center').dialogTableHandler(table='test.myticket',
                               datapath='.tickets',
                               viewResource='View',
                               formResource='Form')
