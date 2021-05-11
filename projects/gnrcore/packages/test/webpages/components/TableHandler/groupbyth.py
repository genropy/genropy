# -*- coding: utf-8 -*-

"""genrodlg"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    
    def struttura_group(self,struct):
        r=struct.view().rows()
        r.fieldcell('@sigla_provincia.nome',width='20em')
        r.fieldcell('popolazione_residente',group_aggr='sum',width='10em')
        r.fieldcell('popolazione_residente',group_aggr='avg',width='10em')

    def test_0_groupByTableHandler(self,pane):
        "Group data by customized criteria with groupByTableHandler. In this case, insert region name to show data"
        bc = pane.borderContainer(height='400px',width='650px')
        bc.contentPane(region='top').dbSelect(value='^regione',dbtable='glbl.regione', lbl='Regione')
        center = bc.contentPane(region='center')
        center.groupByTableHandler(table='glbl.comune', struct=self.struttura_group,
                                condition='@sigla_provincia.regione LIKE :rg', condition_rg='^regione?=#v?#v:"%"',
                                border='1px solid silver')

    def test_1_groupedView(self, pane):
        "Same result with plainTableHandler, with Grouped View (open on the left"
        pt = pane.plainTableHandler(table='fatt.fattura_riga', height='500px',
                                        view_store_onStart=True, groupable=True)