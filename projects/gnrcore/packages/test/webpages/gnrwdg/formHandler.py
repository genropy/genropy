# -*- coding: utf-8 -*-

"""frameForm and its recordCluster store, in every container that can hold a form

`frameForm` is the form widget of the framework: a framePane whose store is a
record loaded from a table, with the toolbar commands (navigation, save, delete,
locker, semaphore) wired to it. The store here is always `recordCluster` on
`glbl.provincia`, so the cases differ only in where the form lives -- side by
side in a borderContainer, in a tabContainer built lazily, in a docked palette,
in a tooltipPane, in a dialog, or built remotely -- and in how the record to
load is chosen. `onLoading_glbl_provincia` shows the server-side hook that can
mark a record readonly while it is being loaded.
"""

from gnr.web.gnrwebstruct import struct_method


class GnrCustomWebPage(object):
    dojo_source=True
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/formhandler:FormHandler,foundation/includedview:IncludedView"
    user_polling=0
    auto_polling=0

    @struct_method
    def formTester(self,pane,frameCode=None,startKey=None,**kwargs):
        """The form the cases reuse: a frameForm on glbl.provincia with a recordCluster store"""
        form = pane.frameForm(frameCode=frameCode,table='glbl.provincia',
                              store='recordCluster',store_startKey=startKey or '*norecord*',**kwargs)
        form.testToolbar(startKey=startKey)
        pane = form.center.contentPane(datapath='.record')
        fb = pane.formbuilder(cols=2, border_spacing='4px',fld_width="100%")
        fb.formContent()
        return form

    @struct_method
    def testToolbar(self,form,startKey=None):
        """The form toolbar; without a startKey it also carries the dbselect that loads a record"""
        left = 'selector,|,' if not startKey else ''
        tb = form.top.slotToolbar('%s *,|,semaphore,|,formcommands,|,locker' %left,border_bottom='1px solid silver')
        if not startKey:
            fb = tb.selector.formbuilder(cols=1, border_spacing='1px')
            fb.dbselect(value="^.prov",dbtable="glbl.provincia",parentForm=False,
                                        validate_onAccept="if(userChange){this.form.publish('load',{destPkey:value})};",
                                        lbl='Provincia')
        return tb

    @struct_method
    def formContent(self,fb):
        """The record fields, with the validate_len rules of sigla and codice_istat"""
        fb.field('sigla',validate_len='2:2',validate_len_error="""Wrong lenght! (the field accept
                                                                  only a string of 2 characters)""")
        fb.field('regione')
        fb.field('nome',keepable=True)
        fb.field('codice_istat',keepable=True,validate_len='6:10')
        fb.field('ordine')
        fb.field('ordine_tot')
        fb.field('cap_valido')
        fb.checkbox(value='^.piero',keepable=True,label='Piero')
        return fb

    def onLoading_glbl_provincia(self,record,newrecord,loadingParameters,recInfo):
        """Server-side loading hook: the record of Aosta is served readonly"""
        if record['sigla'] == 'AO':
            recInfo['_readonly'] = True

    def test_0_frameform(self,pane):
        """A frameForm whose formStore is declared explicitly, with a callback on the load handler"""
        form = pane.frameForm(frameCode='provincia_1',border='1px solid silver',datapath='.form',
                              rounded_bottom=10,height='180px',width='600px',pkeyPath='.prov')
        form.testToolbar()
        store = form.formStore(table='glbl.provincia',storeType='Item',handler='recordCluster',startKey='*norecord*',onSaved='reload')
        rpc = store.handler('load',default_ordine_tot='100')
        rpc.addCallback('console.log(result)')
        pane = form.center.contentPane(datapath='.record')
        fb = pane.formbuilder(cols=2).formContent()

    def test_10_frameform_iv(self,pane):
        """The same form in a tabContainer, the second tab holding the localita of the loaded provincia"""
        form = pane.frameForm(frameCode='regione_b',border='1px solid silver',datapath='.form',
                            rounded_bottom=10,height='180px',width='600px',pkeyPath='.prov')
        form.testToolbar()
        store = form.formStore(table='glbl.provincia',storeType='Item',handler='recordCluster',startKey='*norecord*',onSaved='reload')
        store.handler('load',_onCalling='console.log("xxxx")',default_ordine_tot='100')
        tc = form.center.tabContainer(datapath='.record')
        tc.contentPane(title='Provincia').formbuilder(cols=2, border_spacing='3px').formContent()
        bc =tc.borderContainer(title='Comuni')
        self.includedViewBox(bc,label='Comuni',datapath='comuni',
                             nodeId='comuni',table='glbl.localita',
                             struct='min',
                             reloader='^#regione_b_form.record.id',
                             selectionPars=dict(where='$provincia=:provincia_id',
                             provincia_id='^#regione_b_form.record.sigla'))

    def test_2_formPane_dbl_cp(self,pane):
        """Two independent forms side by side: each frameCode has its own store and toolbar"""
        bc = pane.borderContainer(height='180px')
        bc.formTester(frameCode='form_a',region='left',datapath='.pane1',width='50%',border='1px solid gray',margin_right='5px')
        bc.formTester(frameCode='form_b',region='center',datapath='.pane2',border='1px solid gray')

    def test_22_formPane_tc(self,pane):
        """A form as a tab of a tabContainer, built only when the tab is first selected (_lazyBuild)"""
        bc = pane.borderContainer(height='300px')
        topbc = bc.borderContainer(height='250px',region='top',splitter=True)
        bc.contentPane(region='center')
        tc = topbc.tabContainer(region='left',splitter=True,width='600px',nodeId='mytc')
        topbc.contentPane(region='center').div('pippo')
        tc.contentPane(title='Dummy',background_color='red')
        tc.formTester('form_tc',region='center',title='My Form',_lazyBuild=True)
        tc.contentPane(title='Third one')

    def test_3_formPane_palette(self,pane):
        """A form inside a docked palette, built lazily when the palette is first opened"""
        pane = pane.div(height='30px')
        pane.dock(id='test_3_dock')
        pane.palette(paletteCode='province_lazy',title='Province',dockTo='test_3_dock',
                    _lazyBuild=True,_onLazyBuilt='console.log("aaa")').formTester('form_palette',height='300px',width='400px')

    def test_8_formPane_tooltipForm(self,pane):
        """A form in a tooltipPane: shift-hovering the box loads the provincia named by its attribute"""
        box = pane.div(height='30px',width='100px',background='red',provincia='MI')
        box.span('Milano')
        dlg = box.tooltipPane(title='Milano',modifiers='shift',xconnect_onOpening='console.log(arguments);genro.formById("form_ttdialog").load({destPkey:e.target.sourceNode.attr.provincia});')
        dlg.formTester('form_ttdialog',height='300px',width='500px',background='white',rounded=6)

    def test_5_formPane_palette_remote(self,pane):
        """A palette created client side whose content is built by remote_testPalette on the server"""
        fb = pane.formbuilder(cols=4, border_spacing='2px')
        fb.dbselect(value="^.provincia",dbtable="glbl.provincia")
        fb.button('open',action="""var paletteCode='prov_'+pkey;

                                   var palette = genro.src.create('palette',{paletteCode:paletteCode,title:'Palette:'+pkey,
                                                                               remote:'testPalette',remote_pkey:pkey,
                                                                               dockTo:false},
                                                                    paletteCode);
                                    """,
                    pkey='=.provincia')

    def remote_testPalette(self,pane,pkey=None,**kwargs):
        """The remote builder of test_5: one form per pkey, opened on the record it names"""
        pane.formTester('formRemote_%s' %pkey,startKey=pkey,width='500px',height='300px')

    def test_4_formPane_dialog(self,pane):
        """A form in a dialog, its contentPane built the first time the dialog is shown"""
        pane.button('Show dialog',action='genro.wdgById("province_dlg").show()')
        dialog = pane.dialog(title='Province',nodeId='province_dlg',closable=True).contentPane(_lazyBuild=True)
        dialog.formTester('form_dialog',height='300px',width='500px')

    @struct_method('mytoolbar_selectrecord')
    def mytoolbar_selectrecord(self,pane,**kwargs):
        """A toolbar slot offering the record selector as a struct_method of its own"""
        fb=pane.formbuilder(cols=1, border_spacing='1px')
        fb.dbselect(value="^.prov",dbtable="glbl.provincia",parentForm=False,
                    validate_onAccept="this.form.publish('load',{destPkey:value});",lbl='Provincia')

    def rpc_salvaDati(self, dati, **kwargs):
        """Server-side receiver printing whatever a case sends it"""
        print("Dati salvati:")
        print(dati)

    def test_111_frame_formdatapath(self,pane):
        """A form loaded on a fixed startKey (MI), its fields spread over two tabs"""
        form = pane.frameForm(frameCode='regione_a',border='1px solid silver',datapath='.form',
                            rounded_bottom=10,height='180px',width='600px',
                            pkeyPath='.prov')
        form.formStore(table='glbl.provincia',storeType='Item',
                      handler='recordCluster',startKey='MI',onSaved='reload')
        form.testToolbar()
        tc = form.center.tabContainer()
        pane =tc.contentPane(title='profile',datapath='.record')
        fb = pane.formbuilder(cols=1, border_spacing='2px')
        fb.field('sigla', validate_len='2:2',validate_len_min_error='Too Short')
        fb.field('regione')
        fb.field('nome')
        fb.field('codice_istat')
        fb.field('ordine')
        fb.field('ordine_tot')
        fb.field('cap_valido')
        tc.contentPane(title='view',datapath='.viewer')
