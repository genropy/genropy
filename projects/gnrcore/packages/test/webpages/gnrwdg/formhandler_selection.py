# -*- coding: utf-8 -*-

"""A form fed by a selection store: navigating a grid instead of loading one record

`formStore(storeType='Collection')` loads a whole selection into the form, so the
toolbar's navigation arrows walk the records without a round trip, and a grid on
the side can drive the form by publishing `load`. The cases go from that pairing
(the grid and the form as two separate widgets) to `linkedForm`, which is the
grid building its own form -- in a dialog, in a pane of the caller's choosing, or
nested inside the form of the parent record.
"""

from gnr.web.gnrwebstruct import struct_method


class GnrCustomWebPage(object):
    user_polling=0
    auto_polling=0
    py_requires="""gnrcomponents/testhandler:TestHandlerFull,
                    gnrcomponents/formhandler:FormHandler"""

    @struct_method
    def formTester(self,pane,frameCode=None,startKey=None,**kwargs):
        """The form the cases reuse: a frameForm over a Collection store of glbl.provincia"""
        form = pane.frameForm(frameCode=frameCode,rounded_bottom=10,childname='form',**kwargs)
        form.testToolbar()
        store = form.formStore(table='glbl.provincia',storeType='Collection',
                               handler='recordCluster')
        fb = form.center.contentPane(datapath='.record').formbuilder(cols=2, border_spacing='4px', width="400px",fld_width="100%")
        fb.formContent()
        return form

    @struct_method
    def testToolbar(self,form,startKey=None):
        """The form toolbar: the navigation arrows are what a Collection store adds"""
        tb = form.top.slotToolbar('navigation,*,|,semaphore,|,formcommands,|,locker',border_bottom='1px solid silver')
        return tb

    @struct_method
    def formContent(self,fb):
        """The record fields, sigla checking that it stays unique"""
        fb.field('sigla',validate_nodup=True)
        fb.field('regione')
        fb.field('nome')
        fb.field('codice_istat')
        fb.field('ordine')
        fb.field('ordine_tot')
        fb.field('cap_valido')
        return fb

    def test_0_base(self,pane):
        """An includedView and a form as two widgets: selecting a row publishes load on the form"""
        bc = pane.borderContainer(height='250px')
        frame = bc.framePane('province_0',region='left',width='300px')

        tb = frame.top.slotToolbar('*,selector,20,reloader')
        tb.selector.dbselect(value='^.regione',dbtable='glbl.regione',lbl='Regione')
        tb.reloader.button('reload',fire='.reload')
        iv = frame.includedView(struct='sigla,nome',autoSelect=True,selectedId='.selectedPkey',
                           selfsubscribe_onSelectedRow='genro.formById("provincia_0_form").publish("load",{destPkey:$1.selectedId});',
                           subscribe_form_provincia_0_onLoaded="this.widget.selectByRowAttr('_pkey',$1.pkey)")
        iv.selectionStore(table='glbl.provincia',where='$regione=:r',r='^.regione',_fired='^.reload')

        form = bc.contentPane(region='center',border='1px solid blue').formTester(frameCode='provincia_0')
        form.store.attributes['parentStore'] = 'province_0_grid'

    def test_1_base(self,pane):
        """The same pairing with a searchable, counting toolbar over the grid"""
        bc = pane.borderContainer(height='250px')
        frame = bc.framePane('province_1',region='left',width='600px')
        tb = frame.top.slotToolbar('selector,searchOn,reloader,count')
        tb.selector.dbselect(value='^.regione',dbtable='glbl.regione',lbl='Regione')
        tb.reloader.button('reload',fire='.reload')
        iv = frame.includedView(struct='sigla,nome',autoSelect=True,selectedId='.selectedPkey',
                           selfsubscribe_onSelectedRow='genro.formById("provincia_1_form").publish("load",{destPkey:$1.selectedId});',
                           subscribe_form_provincia_1_onLoaded="this.widget.selectByRowAttr('_pkey',$1.pkey)")
        iv.selectionStore(table='glbl.provincia',where='$regione=:r',r='^.regione',_fired='^.reload')
        form = bc.contentPane(region='center').formTester(frameCode='provincia_1')
        form.store.attributes['parentStore'] = 'province_1_grid'

    def test_2_linkedForm(self,pane):
        """linkedForm: the grid builds the form itself and opens it in a dialog on double click"""
        bc = pane.borderContainer(height='250px')
        frame = bc.framePane(region='left',frameCode='province_2',width='300px')
        # the grid comes first: the addrow slot of the toolbar reads frame.grid
        iv = frame.includedView(struct='sigla,nome',autoSelect=True)
        iv.selectionStore(table='glbl.provincia',where='$regione=:r',
                          r='^.regione',_fired='^.reload')
        tb = frame.top.slotToolbar('selector,*,addrow,10')
        tb.selector.dbselect(value='^.regione',dbtable='glbl.regione',lbl='Regione')
        form = iv.linkedForm(frameCode='provincia_2',loadEvent='onRowDblClick',
                             dialog_title='Prova',
                             dialog_height='300px',
                             dialog_width='500px')
        form.store.handler('load',default_regione='=#province_2_frame.regione')
        form.testToolbar()
        bc.contentPane(region='center',border='1px solid blue')
        form.store.handler('save')
        pane = form.center.contentPane(datapath='.record')
        pane.formbuilder(cols=2,border_spacing='4px',width='400px',fld_width='100%').formContent()

    def test_3_linkedForm_pane(self,pane):
        """The same linkedForm built into a pane of the page (formRoot) instead of a dialog"""
        bc = pane.borderContainer(height='250px')
        frame = bc.framePane('province_3',region='left',width='300px')
        tb = frame.top.slotToolbar('*,selector,20,reloader')
        tb.selector.dbselect(value='^.regione',dbtable='glbl.regione',lbl='Regione')
        tb.reloader.button('reload',fire='.reload')
        iv = frame.includedView(struct='sigla,nome',autoSelect=True)
        iv.selectionStore(table='glbl.provincia',where='$regione=:r',
                          r='^.regione',_fired='^.reload')
        center = bc.contentPane(region='center',border='1px solid blue')
        form=iv.linkedForm(frameCode='provincia_3',loadEvent='onSelected',
                            formRoot=center,store_startKey='*norecord*',
                            store_onSaved='reload')
        form.testToolbar()
        pane = form.center.contentPane(datapath='.record')
        pane.formbuilder(cols=2, border_spacing='4px', width="400px",fld_width="100%").formContent()

    def formCb(self,pane):
        """A form body as a callable, for a case wanting to pass it around"""
        pane.formbuilder(cols=2, border_spacing='4px', width="400px",fld_width="100%").formContent()

    def test_4_linkedForm_pane_nested(self,pane):
        """A form of glbl.regione holding the grid of its province, each with its own linkedForm"""
        mainform = pane.frameForm(frameCode='regione_4',height='500px',table='glbl.regione',
                                store='recordCluster',store_startKey='*norecord*')
        tb = mainform.top.slotToolbar('selector,*,|,semaphore,|,formcommands,|,locker')
        tb.selector.dbselect(value='^.regione',dbtable='glbl.regione',lbl='Regione',
                             validate_onAccept='this.form.load({"destPkey":value});',parentForm=False)
        bc = mainform.center.borderContainer(datapath='.record')
        regione = bc.contentPane(region='left',margin='2px')
        regione.div('!!Regione',background='darkblue',color='white',rounded_top=12,padding='4px')
        fb = regione.formbuilder(cols=2, border_spacing='3px')
        fb.field('sigla')
        fb.field('nome')
        fb.field('codice_istat')
        fb.field('ordine')
        fb.field('zona')
        province = bc.framePane('province_regione_4',region='center',margin='2px',datapath='.#parent.provincia')
        # the grid comes first: the addrow slot of the toolbar reads frame.grid
        iv = province.includedView(struct='sigla,nome',autoSelect=True)
        iv.selectionStore(table='glbl.provincia',where='$regione=:r',r='^.#parent.record.sigla')
        province.top.slotToolbar('*,addrow,delrow',addrow_parentForm=True,delrow_parentForm=True)
        form=iv.linkedForm(frameCode='provincia_4',loadEvent='onRowDblClick',
                            dialog_title='Provincia',dialog_height='300px',dialog_width='400px',store_onSaved='reload')
        form.testToolbar()
        form.store.handler('save')
        fb = form.center.contentPane(datapath='.record').formbuilder(cols=2, border_spacing='4px', width="400px",fld_width="100%").formContent()
        fb.textbox(value='^.auxdata.prova',lbl='Prova')
        fb.textbox(value='^.auxdata.mia',lbl='Mia')
        fb.textbox(value='^.auxdata.foo.bar',lbl='Bar')
