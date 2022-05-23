# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires="""gnrcomponents/testhandler:TestHandlerBase,
                    gnrcomponents/tpleditor:ChunkEditor"""

    def test_0_chooseRecord(self,pane):
        """templateChunk can embed a template block in a page. Use shift+click to manager your template
        (only for _dev_ users)"""
        cp = pane.contentPane(region='center', height='600px')
        cp.dbSelect(value='^.prov_sigla', table='glbl.provincia', lbl='!!Choose province')
        cp.templateChunk(table='glbl.provincia', record_id='^.prov_sigla', height='200px', template='provincetpl')

    def test_1_autoSelect(self,pane):
        """Use dataFormula with _onStart=True to automatically retrieve data on loading"""
        cp = pane.contentPane(region='center', height='600px')
        provincia_rec = self.db.table('glbl.provincia').recordAs('MI')
        cp.dataFormula('.prov_sigla', 'prov', prov=provincia_rec['sigla'], _onStart=True)
        cp.templateChunk(table='glbl.provincia', record_id='^.prov_sigla', height='200px', template='provincetpl')