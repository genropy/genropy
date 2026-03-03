# -*- coding: utf-8 -*-

"""Test page for recursive nested topics: a topic can contain sub-topics
at arbitrary depth. The submethodtesting topic has an inner/ sub-topic
with gamma and delta grouplets."""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet:GroupletHandler"""

    def test_1_nested_topic_grid(self, pane):
        """Topic grid with nested sub-topic: submethodtesting contains alfa, beta
        and inner/ sub-topic (gamma, delta). Inner renders as nested grid."""
        pane.borderContainer(height='500px', border='1px solid silver',
                             datapath='.nested_grid').contentPane(
            region='center', overflow='auto').grouplet(
            resource='submethodtesting',
            value='^.data',
            remote_grid_collapsible=True)

    def test_2_nested_topic_panel(self, pane):
        """Panel tree with nested topics: tree shows submethodtesting with
        expandable inner branch containing gamma and delta leaves."""
        pane.borderContainer(height='500px', border='1px solid silver',
                             datapath='.nested_panel').groupletPanel(
            value='^.data',
            frameCode='nested_panel',
            region='center')

    def test_3_nested_topic_wizard(self, pane):
        """Wizard with nested topic: top-level items become wizard steps.
        alfa and beta are individual steps; inner is a single step that
        renders gamma and delta as a CSS grid via gr_loadGrouplet."""
        pane.borderContainer(height='500px', border='1px solid silver',
                             datapath='.nested_wizard').groupletWizard(
            topic='submethodtesting',
            value='^.data',
            frameCode='nested_wizard',
            region='center')

    def test_4_nested_menu_rpc(self, pane):
        """Verify nested menu structure via dataRpc: the returned Bag should
        contain a submethodtesting topic with an inner sub-topic."""
        bc = pane.borderContainer(height='500px', border='1px solid silver',
                                  datapath='.nested_menu')
        bc.contentPane(region='top', height='40px').button(
            'Load Menu',
            action="FIRE .load_menu;")
        bc.dataRpc('.menu_result', self.getNestedMenu,
                   _fired='^.load_menu')
        bc.contentPane(region='center', overflow='auto').tree(
            storepath='.menu_result',
            hideValues=True,
            labelAttribute='caption',
            _class='branchtree noIcon')

    @public_method
    def getNestedMenu(self, **kwargs):
        return self.gr_getGroupletMenu()
