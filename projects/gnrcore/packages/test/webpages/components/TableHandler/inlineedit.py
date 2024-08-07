# -*- coding: utf-8 -*-

"""Inline edit cases"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
        
    def test_0_testCheckbox(self, pane):
        "stackTableHandler, double click to open record and check fields"
        bc = pane.borderContainer(height='400px')
        bc.contentPane(region='center').stackTableHandler(table='glbl.regione',viewResource='TestDyinCheckbox',
                                                            formResource='TestDyinCheckboxForm',
                                                            pbl_classes=True,condition_onStart=True)


    def test_1_testCheckbox_b(self, pane):
        "inlineTableHandler, edit directly from column"
        bc = pane.borderContainer(height='400px')
        bc.contentPane(region='center').inlineTableHandler(table='glbl.regione',viewResource='TestEditInlineCheckbox',
                                                            pbl_classes=True,condition_onStart=True,saveButton=True)


    def test_2_testCheckbox_c(self, pane):
        "stackTableHandler, double click to open record and check fields hierarchically"
        bc = pane.borderContainer(height='400px')
        bc.contentPane(region='center').stackTableHandler(table='glbl.regione',viewResource='TestDyinCheckboxNuts',
                                                            condition_onStart=True,
                                                            formResource='TestDyinCheckboxTree')


    def test_3_testCheckbox_c(self, pane):
        "inlineTableHandler, edit directly from column hierarchically"
        bc = pane.borderContainer(height='400px')
        bc.contentPane(region='center').inlineTableHandler(table='glbl.regione',viewResource='TestDyinCheckboxNutsEdit',
                                                            pbl_classes=True,condition_onStart=True,saveButton=True)


        
    def test_4_testCheckbox_variablestruct(self, pane):
        "plainTableHandler, hide Columns with checkbox or dropdown"
        bc = pane.borderContainer(height='800px')
        bc.contentPane(region='top').checkbox(value='^nascondi',label='hidden')
        bc.contentPane(region='center').plainTableHandler(table='glbl.regione',viewResource='TestHiddenStruct',
                                                        pbl_classes=True,condition_onStart=True,saveButton=True)
        bottom_bc = bc.borderContainer(region='bottom',height='500px',datapath='.altragrid')
        bottom_bc.bagGrid(struct=self.pippostruct,region='center')

        bottom_bc.contentPane(region='top').filteringSelect(value='^main.tiponascondi',label='Tiponascondi',values='AA:Nascondi,BB:Non nascondi')

    def pippostruct(self,struct):
        r = struct.view().rows()
        r.cell('codice', width='20em',name='Codice')
        r.cell('descrizione',width='3em',name='Descrizione',hidden='^main.tiponascondi?=#v=="AA"')

