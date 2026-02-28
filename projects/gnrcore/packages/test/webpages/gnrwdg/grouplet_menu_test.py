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
            value='^.record',
            showOnFormLoaded=False)

    def test_2_myticket(self, pane):
        """Ticket system: form_add menu creates typed tickets with dynamic grouplet"""
        pane.borderContainer(height='500px').contentPane(region='center').dialogTableHandler(table='test.myticket',
                               datapath='.tickets',
                               viewResource='View',
                               formResource='Form')
