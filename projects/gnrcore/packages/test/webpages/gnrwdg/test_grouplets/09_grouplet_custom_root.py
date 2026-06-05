# -*- coding: utf-8 -*-

"""Test page for grouplets_root parameter: load grouplets from a custom
root folder (myconfigurations/) instead of the default grouplets/ folder.
The myconfigurations resources are in packages/test/resources/myconfigurations/."""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletHandler"""

    def test_1_custom_root_resource(self, pane):
        """Single grouplet from custom root: loads contact_info from
        myconfigurations/ instead of grouplets/."""
        pane.borderContainer(height='400px', border='1px solid silver',
                             datapath='.custom_single').contentPane(
            region='center', overflow='auto').grouplet(
            resource='contact_info',
            grouplets_root='myconfigurations',
            value='^.data')

    def test_2_custom_root_topic_grid(self, pane):
        """Topic from custom root: loads preferences/ topic from
        myconfigurations/ as a collapsible grid."""
        pane.borderContainer(height='400px', border='1px solid silver',
                             datapath='.custom_topic').contentPane(
            region='center', overflow='auto').grouplet(
            resource='preferences',
            grouplets_root='myconfigurations',
            value='^.data',
            remote_grid_collapsible=True)

    def test_3_custom_root_panel(self, pane):
        """Panel with custom root: tree shows all myconfigurations content
        (contact_info leaf + preferences topic with notifications and theme)."""
        pane.borderContainer(height='500px', border='1px solid silver',
                             datapath='.custom_panel').groupletPanel(
            grouplets_root='myconfigurations',
            value='^.data',
            frameCode='custom_panel',
            region='center')

    def test_4_custom_root_menu_rpc(self, pane):
        """Verify custom root menu via dataRpc: the returned Bag should
        contain contact_info and preferences topic from myconfigurations/."""
        bc = pane.borderContainer(height='500px', border='1px solid silver',
                                  datapath='.custom_menu')
        bc.contentPane(region='top', height='40px').button(
            'Load Menu',
            action="FIRE .load_menu;")
        bc.dataRpc('.menu_result', self.getCustomRootMenu,
                   _fired='^.load_menu')
        bc.contentPane(region='center', overflow='auto').tree(
            storepath='.menu_result',
            hideValues=True,
            labelAttribute='caption',
            _class='branchtree noIcon')

    @public_method
    def getCustomRootMenu(self, **kwargs):
        return self.gr_getGroupletMenu(grouplets_root='myconfigurations')
