# -*- coding: utf-8 -*-

# gettemplate.py
# Created by Francesco Porcari on 2011-05-11.
# Copyright (c) 2011 Softwell. All rights reserved.

"Test page description"

class GnrCustomWebPage(object):
    py_requires="""gnrcomponents/testhandler:TestHandlerFull,
                   gnrcomponents/tpleditor:ChunkEditor,
                   gnrcomponents/framegrid:TemplateGrid"""

    def test_1_template_a(self,pane):
        """First test description"""
        pane.dbSelect(dbtable='glbl.provincia',value='^.pkey',_class='gnrfield')
        pane.dataRecord('.record','glbl.provincia',pkey='^.pkey',_onStart=True)
        pane.data('.pippo',55)
        pane.div(template="""<div><span>$sigla $regione</span>
                             </div><div>$nome</div> $pippo""",datasource='^.record',pippo='^.pippo')

    def test_2_template(self,pane):
        """First test description"""
        pane.dbSelect(dbtable='glbl.provincia',value='^.pkey',_class='gnrfield')
        pane.dataRecord('.record','glbl.provincia',pkey='^.pkey',_onStart=True)
        pane.data('.pippo',55)
        pane.div(template="""<div><span>$sigla $regione</span>
                             </div><div>$nome</div> $pippo""",datasource='^.record',pippo='^.pippo')
                             
    def test_3_template(self,pane):
        """First test description"""
        #pane.div('aaa')
        pane.textbox(value='^.template_name',default_value='demotpl1.html')
        pane.dbSelect(dbtable='glbl.provincia',value='^.pkey',_class='gnrfield')
        pane.dataRecord('.record','glbl.provincia',pkey='^.pkey',_onStart=True)
        pane.data('.pippo',55)
        pane.dataResource('.remote_tpl',resource='^.template_name')
        pane.div(template='^.remote_tpl',datasource='^.record',pippo='^.pippo')
    
    def test_4_tableTemplate(self,pane):
        pane.dbSelect(dbtable='glbl.provincia',value='^.pkey',_class='gnrfield')
        pane.dataRecord('.record','glbl.provincia',pkey='^.pkey',_onStart=True)
        pane.div(template=self.tableTemplate('glbl.provincia','short'),datasource='^.record')
    
    def test_5_templateChunk(self,pane):
        pane.dbSelect(dbtable='glbl.regione',value='^.pkey',_class='gnrfield')
        pane.textbox(value='^ggg')

        rpc = pane.dataRecord('.record','glbl.regione',pkey='^.pkey')
        pane.templateChunk(innerHTML='^.piero',template='custom',table='glbl.regione',datasource='^.record',
                        tpl_test='^ggg',tpl_root='^*D',
                    height='100px',dataProvider=rpc,editable=True)


    def test_36_templateChunk(self,pane):
        pane.dbSelect(dbtable='glbl.regione',value='^.pkey',_class='gnrfield',lbl='Regione')
        rpc = pane.dataRecord('.record','glbl.regione',pkey='^.pkey')
        pane.templateChunk(innerHTML='^.testplain',template='testplain',table='glbl.regione',datasource='^.record',
                    height='100px',
                    dataProvider=rpc,
                    editable=True,plainText=True)



    def test_6_templateChunk_provincia(self,pane):
        pane.dbSelect(dbtable='glbl.provincia',value='^.pkey',_class='gnrfield')
        rpc = pane.dataRecord('.record','glbl.provincia',pkey='^.pkey')
        pane.templateChunk(template='custom',table='glbl.provincia',datasource='^.record',
                            height='100px',record_id='^.record.sigla')



    def test_7_templateChunk_provincia(self,pane):
        pane.dbSelect(dbtable='glbl.provincia',value='^.pkey',_class='gnrfield')
        rpc = pane.dataRecord('.record','glbl.provincia',pkey='^.pkey')
        pane.templateChunk(template='custom',table='glbl.provincia',datasource='^.record',
                            height='100px',dataProvider=rpc)


    def test_9_templateChunk(self,pane):
        pane.dbSelect(dbtable='glbl.regione',value='^.pkey',_class='gnrfield')
        pane.textbox(value='^ggg')
        pane.div(nodeId='zzz')

        #rpc = pane.dataRecord('.record','glbl.regione',pkey='^.pkey')
        pane.templateChunk(innerHTML='^.piero',template='custom',table='glbl.regione',#datasource='^.record',
                        tpl_test='^ggg',tpl_root='^*D',record_id='^.pkey',
                    height='100px',#dataProvider=rpc,
                    editable=True)



    def test_6_templateChunkNoResource(self,pane):
        pane.dataRecord('.tipo_protocollo','studio.pt_tipo',pkey='PiWA-zDGMhSbDKS5AYRR5g',_onStart=True)
        
        pane.dbSelect(dbtable='studio.pt_protocollo',value='^.protocollo_esempio.pkey')
        rpc = pane.dataRecord('.protocollo_esempio.record','studio.pt_protocollo',pkey='^.protocollo_esempio.pkey')
        
        pane.templateChunk(template='^.tipo_protocollo.template_associato',
                            table='studio.pt_protocollo',editable=True,dataProvider=rpc,
                            datasource='^#FORM.protocollo_esempio.record', height='100px')



    def test_10_notable(self,pane):
        pane.dataRecord('.dati','glbl.provincia',pkey='MI',_onStart=True)
        
        
        pane.templateChunk(template='tplnotable',
                            datasource='^.dati',
                            editable=True, 
                            height='100px')


    def test_33_notable(self,pane):
        fb = pane.formbuilder()
        fb.dbSelect(value='^.prodotto_id',dbtable='fatt.prodotto',
                        condition='$caratteristiche IS NOT NULL')
        fb.dataRecord('.prodotto','fatt.prodotto',pkey='^.prodotto_id',_if='pkey')
        
        
        pane.templateChunk(template='.prodotto.prodotto_tipo_id',
                            datasource='^.prodotto.caratteristiche',
                            editable=True, 
                            height='100px')

    def test_34_notable(self,pane):
        fb = pane.formbuilder()
        fb.dbSelect(value='^.prodotto_id',dbtable='fatt.prodotto',
                        condition='$caratteristiche IS NOT NULL')
        fb.dataRecord('.prodotto','fatt.prodotto',pkey='^.prodotto_id',_if='pkey')
        
        
        pane.templateChunk(template='^.prodotto.prodotto_tipo_id',
                            datasource='.prodotto',
                            table='fatt.prodotto',
                            editable=True, 
                            height='100px')

    def test_11_griddynamic(self,pane):
        frame = pane.templateGrid(storepath='.data',
            fields=[dict(value='^.sigla',lbl='Sigla'),dict(value='^.nome',lbl='Nome')],
            template_resource='tplnotable',
            height='500px',pbl_classes='*',title='Pippo')
        bar = frame.top.bar.replaceSlots('addrow','addrow,testpicker')
        bar.testpicker.palettePicker(grid=frame.grid,
                                    table='glbl.provincia',#paletteCode='mypicker',
                                    viewResource='View',
                                    checkbox=True,defaults='sigla,nome',
                                    relation_field='sigla')


                    
    def test_z_formulasyntax(self,pane):
        fb = pane.formbuilder(cols=1)
        fb.numberTextbox(value='^.width')
        fb.textbox(value='^.pippo',width='==_width+_uu+"px";',_width='^.width',_uu=66,
                     onCreated='console.log("bazinga");')
        fb.checkbox(value='^.prova',lbl='disabled')
        fb.textbox(disabled='^.prova')
        fb.textbox(value='^.dis')
        fb.textbox(value='^.xxx',disabled='==_prova=="disabled";',_prova='^.dis',onCreated='console.log("bazinga");')
        
    
        

