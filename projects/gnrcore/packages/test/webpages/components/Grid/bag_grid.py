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

    def test_4_columnset_scroll(self,pane):
        "bagGrid with a fixed first column and ten columnsets, to check horizontal scrolling"
        pane.data('.dati',self.getScrollRows())
        pane.dataController('SET .gridstore = dati.deepCopy();',dati='=.dati',_fired='^.loadBag')
        pane.dataFormula('.gridstore',"new gnr.GnrBag();",_onStart=True)
        frame = pane.bagGrid(frameCode='test',title='Test',
                                struct=self.scrollstruct,
                                height='300px',
                                storepath='.gridstore')
        frame.bottom.button('Load',fire='.loadBag')

    def scrollstruct(self,struct):
        "Struct of test_4_columnset_scroll: one fixed column plus ten columnsets of three cells"
        view_0 = struct.view(fixedColumn=1)
        rows = view_0.rows()
        rows.cell('nome',width='10em',name='Nome')
        for i in range(10):
            cs = rows.columnset('cs_{}'.format(i),name='Cs {}'.format(i))
            for j in range(3):
                cs.cell('val_{i:02}{j:02}'.format(i=i,j=j),name='Col {}'.format(i))

    def getScrollRows(self):
        "Rows of test_4_columnset_scroll, one Bag row per record"
        result = Bag()
        for i in range(5):
            row = Bag()
            result.addItem('r_{i:02}'.format(i=i),row)
            row['nome'] = 'row {i:02}'.format(i=i)
            for j in range(10):
                for z in range(3):
                    row['val_{i:02}{j:02}'.format(i=j,j=z)] = i*100+j
        return result

    def test_5_dynamic_storepath(self, pane):
        """bagGrid whose storepath is a formula: the selected label picks the branch of one Bag the grid shows

        Colour, Size and Shoe size repoint the same grid to `.data.CO`, `.data.TG`
        and `.data.MS` of the case; with no label selected it shows an empty store."""
        bc = pane.borderContainer(height='300px', _anchor=True)
        fb = bc.contentPane(region='top').formbuilder(cols=1, border_spacing='3px')
        fb.filteringSelect(value='^.selectedLabel', lbl='Label',
                           values='CO:Colour,TG:Size,MS:Shoe size')
        fb.data('.data', self.getLabelRows())
        bc.contentPane(region='center').bagGrid(frameCode='dynamicstore', datapath='.mygrid',
                            storepath='==_selectedLabel?"#ANCHOR.data."+_selectedLabel:".emptystore"',
                            grid__selectedLabel='^#ANCHOR.selectedLabel',
                            struct=self.labelstruct)

    def labelstruct(self, struct):
        "Struct of test_5_dynamic_storepath"
        r = struct.view().rows()
        r.cell('codice', name='Code', width='10em', edit=True)
        r.cell('descrizione', name='Description', width='30em', edit=True)

    def getLabelRows(self):
        "Rows of test_5_dynamic_storepath, one branch per label"
        return Bag("""<?xml version="1.0" encoding="utf-8"?>
<GenRoBag>
<CO descrizione="Colour">
<n_1007 _pkey="n_1007"><codice>RO</codice><descrizione>Red</descrizione></n_1007>
<n_1023 _pkey="n_1023"><codice>AR</codice><descrizione>Orange</descrizione></n_1023>
<n_1015 _pkey="n_1015"><codice>VE</codice><descrizione>Green</descrizione></n_1015>
</CO>
<TG descrizione="Size">
<n_1025 _pkey="n_1025"><codice>M</codice><descrizione>Medium</descrizione></n_1025>
<n_1033 _pkey="n_1033"><codice>S</codice><descrizione>Small</descrizione></n_1033>
<n_1041 _pkey="n_1041"><codice>X</codice><descrizione>Large</descrizione></n_1041>
<n_1049 _pkey="n_1049"><codice>XL</codice><descrizione>Extra large</descrizione></n_1049>
</TG>
<MS descrizione="Shoe size">
<n_1012 _pkey="n_1012"><codice>01</codice><descrizione>36</descrizione></n_1012>
<n_1020 _pkey="n_1020"><codice>02</codice><descrizione>37</descrizione></n_1020>
<n_1028 _pkey="n_1028"><codice>03</codice><descrizione>38</descrizione></n_1028>
<n_1036 _pkey="n_1036"><codice>04</codice><descrizione>39</descrizione></n_1036>
<n_1044 _pkey="n_1044"><codice>05</codice><descrizione>40</descrizione></n_1044>
<n_1052 _pkey="n_1052"><codice>06</codice><descrizione>41</descrizione></n_1052>
<n_1060 _pkey="n_1060"><codice>07</codice><descrizione>42</descrizione></n_1060>
</MS>
</GenRoBag>""")

    def test_6_hidden_column(self, pane):
        """bagGrid whose Description column is hidden through a data path

        The filteringSelect writes `main.tiponascondi` and the column disappears
        when it holds `AA`. The path is absolute on both its writer and its
        reader, so it lives at the root of the page data, not under the case."""
        bc = pane.borderContainer(height='500px', datapath='.altragrid')
        bc.bagGrid(struct=self.hiddencolumn_struct, region='center')
        bc.contentPane(region='top').filteringSelect(value='^main.tiponascondi', label='Description column',
                                                     values='AA:Hide,BB:Show')

    def hiddencolumn_struct(self, struct):
        "Struct of test_6_hidden_column: one column hidden by a data path"
        r = struct.view().rows()
        r.cell('codice', width='20em', name='Code')
        r.cell('descrizione', width='3em', name='Description', hidden='^main.tiponascondi?=#v=="AA"')

    def test_7_pastegrid(self, pane):
        "bagGrid, paste a block of text and turn every line into a row"
        bc = pane.borderContainer(height='400px')
        bc.contentPane(region='left', width='300px').simpleTextArea(value='^.sentences',
                                                                    height='200px', width='90%')
        bc.bagGrid(struct=self.sentence_struct, region='center',
                   grid_onpaste=r"""
                let txt = event.clipboardData.getData('text');
                let rows = txt.split('\n').map(function(chunk){return {'sentence':chunk}});
                this.gridEditor.addNewRows(rows)
                """)

    def sentence_struct(self, struct):
        "Struct of test_7_pastegrid: a single editable column"
        r = struct.view().rows()
        r.cell('sentence', width='20em', name='Sentence', edit=True)
