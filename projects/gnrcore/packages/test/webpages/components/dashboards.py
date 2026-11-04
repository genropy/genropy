# -*- coding: utf-8 -*-

"""dashboardItem: one dashboard tile outside a dashboard gallery"""


class GnrCustomWebPage(object):

    py_requires = "gnrcomponents/testhandler:TestHandlerFull,dashboard_component/dashboard_component:DashboardItem"

    def windowTitle(self):
        return 'Dashboard item test'

    def test_0_table_counter(self,pane):
        "dash_example_tablecounter, the item counting the rows of the table it is given"
        bc = pane.borderContainer(height='300px',width='500px',margin='10px')
        bc.contentPane(region='center').dashboardItem(table='adm.user',
                            itemName='dash_example_tablecounter')

    def test_1_same_item_other_table(self,pane):
        "The same itemName on adm.htag: the caller binds an item to a table, the item does not"
        bc = pane.borderContainer(height='300px',width='500px',margin='10px')
        bc.contentPane(region='center').dashboardItem(table='adm.htag',
                            itemName='dash_example_tablecounter')

    def test_2_server_processes(self,pane):
        "dash_example_htop, an item reading live server data instead of a table"
        bc = pane.borderContainer(height='400px',width='700px',margin='10px')
        bc.contentPane(region='center').dashboardItem(itemName='dash_example_htop')
