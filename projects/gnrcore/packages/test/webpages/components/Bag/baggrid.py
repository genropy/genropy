# -*- coding: utf-8 -*-

"""bagGrid"""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:frameGrid"
    
    def struct_spesa(self, struct):
        r = struct.view().rows()
        r.cell('articolo', width='20em', name='Articolo', edit=True)
        r.cell('quantita', width='10em', dtype='L', name='Quantità', edit=True)

    def test_0_baggrid(self, pane):
        "BagGrid with possibility to add and remove records. Check inspector to watch generated Bag"
        frame = pane.bagGrid(struct=self.struct_spesa, datapath='.vista_spesa', storepath='.lista_spesa', 
                                    height='400px', width='400px', export=True, searchOn=True)

    def test_1_load(self,pane):
        """Load Bag grid with default values or add single default value. Check inspector to watch generated Bag"""
        pane.data('.dati',self.getDati())
        pane.dataController('SET .gridstore = dati.deepCopy();',dati='=.dati',_fired='^.loadBag')
        pane.dataFormula('.gridstore',"new gnr.GnrBag();",_onStart=True)
        frame = pane.bagGrid(frameCode='load',title='Test',struct=self.gridstruct,height='300px',
                            table='glbl.localita',storepath='.gridstore',
                            default_provincia='MI',
                            default_qty=4)
        frame.bottom.button('Load',fire='.loadBag')
        
    def gridstruct(self, struct):
        r = struct.view().rows()
        r.fieldcell('provincia',edit=dict(selected_codice_istat='.cist'),
                    table='glbl.provincia',caption_field='sigla')
        r.cell('qty',dtype='N',name='Quantitativo',width='5em',edit=True)  
        r.cell('cist',name='Codice istat')

    def getDati(self):
        result = Bag()
        result.setItem('r_0',Bag(dict(provincia = 'MI', qty=13, sigla='MI', cist='044')))
        result.setItem('r_1',Bag(dict(provincia = 'CO', qty=22, sigla='CO', cist='039')))
        return result

    def test_2_remotestruct(self,pane):
        "Load Bag grid struct, then same as before. Check inspector to watch generated Bag"
        pane.data('.dati',self.getDati())
        pane.dataController('SET .xxx = dati.deepCopy();',dati='=.dati',_fired='^.zzz')
        frame = pane.bagGrid(frameCode='remotestruct',title='Bag Grid',structpath='yyy',height='300px',
                            table='glbl.localita',storepath='.xxx',default_provincia='MI',default_qty=4)
        frame.bottom.button('Load Struct',fire='kkk')
        frame.bottom.button('Load',fire='.zzz')
        pane.dataRpc('yyy',self.r_gridstruct,_fired='^kkk')

    @public_method
    def r_gridstruct(self):
        struct = self.newGridStruct()
        r = struct.view().rows()
        r.fieldcell('provincia',edit=dict(selected_codice_istat='.cist'),table='glbl.provincia',caption_field='sigla')
        r.cell('qty',dtype='L',name='Quantitativo',width='5em',edit=True)  
        r.cell('cist',name='Codice istat')
        return struct

    def test_3_bagridformula(self,pane):
        "Bag grid formula: dynamic struct and real time calculation inside grid."
        def struct(struct):
            r = struct.view().rows()
            r.cell('description',name='^first_header_name',width='15em',edit=True,hidden='^hidden_0')

            r.cell('number',name='Number',width='7em',dtype='L',hidden='^hidden_1',
                    edit=True,columnset='ent')
            r.cell('price',name='Price',width='7em',dtype='N',hidden='^hidden_2',
                    edit=True,columnset='ent')
            r.cell('total',name='Total',width='7em',dtype='N',formula='number*price',hidden='^hidden_3',
                    totalize='.sum_total',format='###,###,###.00')
            r.cell('discount',name='Disc.%',width='7em',dtype='N',edit=True,columnset='disc',hidden='^hidden_4')
            r.cell('discount_val',name='Discount',width='7em',dtype='N',formula='total*discount/100',
                    totalize='.sum_discount',hidden='^hidden_5',
                    columnset='disc')
            r.cell('net_price',name='F.Price',width='7em',dtype='N',
                        formula='total-discount_val',totalize='.sum_net_price',
                        columnset='tot',hidden='^hidden_6')
            r.cell('vat',name='Vat',width='7em',dtype='N',
                    formula='net_price+net_price*vat_p/100',formula_vat_p='^vat_perc',
                    totalize='.sum_vat',format='###,###,###.00',columnset='tot',hidden='^hidden_7')
            r.cell('gross',name='Gross',width='7em',dtype='N',formula='net_price+vat',
                    totalize='.sum_gross',format='###,###,###.00',columnset='tot',hidden='^hidden_8')

        bc = pane.borderContainer(height='400px',width='800px')
        top = bc.contentPane(region='top',height='80px')
        fb = top.formbuilder(cols=10,border_spacing='3px')
        bc.contentPane(region='right',splitter=True,width='5px')
        bc.contentPane(region='bottom',splitter=True,height='50px')
        fb.numberTextBox(value='^vat_perc',lbl='Vat perc.',default_value=10,colspan='10')
        fb.data('first_header_name','Variable head')
        fb.textbox(value='^first_header_name',lbl='First header')
        fb.textbox(value='^colsetname',lbl='Colset',default_value='Enterable')
        fb.textbox(value='^colsetentbg',lbl='Colset bg',default_value='green')

        fb.br()
        for i in range(9):
            fb.checkbox(value='^hidden_%s' %i,label='last %s' %i)

        fb.button('clear',fire='.clear')
        bc.dataFormula('.surfaces.store',"new gnr.GnrBag({r1:new gnr.GnrBag({description:'Test variable'})})",_onStart=True,_fired='^.clear')
        frame = bc.contentPane(region='center').bagGrid(frameCode='formule',datapath='.surfaces',
                                                    struct=struct,height='300px',fillDown=True,
                                                    grid_footer='Totals',
                                                    pbl_classes=True,margin='5px',
                                                    columnset_ent='^colsetname',
                                                    columnset_disc='Discount',
                                                    columnset_tot='Totals',
                                                    columnset_ent_background='^colsetentbg',
                                                    columnset_tot_background='red'
                                                    )

    def test_video(self, pane):
        "This bagGrid test was explained in this LearnGenropy video"
        pane.iframe(src='https://www.youtube.com/embed/MnqfBy6Q2Ns', width='240px', height='180px',
                        allow="autoplay; fullscreen")