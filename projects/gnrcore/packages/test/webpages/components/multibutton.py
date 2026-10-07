# -*- coding: utf-8 -*-

"""multibutton"""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):

    py_requires="gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    
    def windowTitle(self):
        return 'Multibutton test'
        
    def test_0_multibutton_base(self,pane):
        "Values declared inline as a code:caption list, the picked code written into the datastore"
        pane.multibutton(value='^.base',values='pippo:Pippo,paperino:Paperino')
        pane.textbox(value='^.base')

    def test_1_itemsMaxWidth(self,pane):
        "itemsMaxWidth caps the width of the whole item strip, so extra values collapse"
        pane.textbox(value='^.base',lbl='Curr selected')
        pane.textbox(value='^.values',lbl='Curr values',default='pippo:Pippo,pluto:Pluto,paperino:Paperino,mario:Mario,l:luca,c:Cesare,p:Pancrazio,o:Ortensia,a:Antonella,b:Brigitta')
        pane.div(height='20px')
        pane.div(_class='mobile_bar').multibutton(value='^.base',values='^.values',itemsMaxWidth='300px',content_max_width='40px')

    def test_2_multibutton_storepath(self,pane):
        "Items read from a Bag through storepath, inside a slotToolbar slot"
        frame = pane.framePane(frameCode='frameMultibuttonStorepath',height='100px',shadow='3px 3px 5px gray',
                                border='1px solid #bbb',rounded_top=10,margin='10px')
        bar = frame.top.slotToolbar(slots='*,mb,*')

        bar.data('.multibutton.data',self.getmbdata())
        bar.mb.multibutton(value='^.multibutton.value',storepath='.multibutton.data')
        frame.textbox(value='^.multibutton.value')
        frame.textbox(value='^.multibutton.data.pippo?caption')

    def test_3_multibutton_items_path(self,pane):
        "Same Bag passed through items instead of storepath"
        pane.data('.multibutton.data',self.getmbdata())
        pane.multibutton(value='^.base',items='^.multibutton.data')
        pane.textbox(value='^.base')

    def test_4_multibutton_items_struct(self,pane):
        "Items declared one by one: Pippo's action, disabled by the checkbox, writes into .last_action; Paperino has a deleteAction"
        pane.checkbox(value='^.disabled')
        mb = pane.multibutton(value='^.base',sticky=False)
        mb.item('pippo',caption='Pippo',disabled='^.disabled',action='this.setRelativeData(".last_action","Pippo clicked");')
        mb.item('paperino',caption='Paperino',deleteAction=True)
        pane.div('^.last_action')

    def test_5_multibutton_items_delay(self,pane):
        "sticky=False items: .base is shown below, Delayed notifies it after 400ms, Different writes into .last_action instead"
        mb = pane.multibutton(value='^.base',sticky=False)

        mb.item('pippo',caption='Pippo')
        mb.item('paperino',caption='Paperino')
        mb.item('delayed',caption='Delayed',_delay=400)
        mb.item('different',caption='Different',action='this.setRelativeData(".last_action","I am different");')
        pane.div('^.base')
        pane.div('^.last_action')

    def test_6_multibutton_dbstore(self,pane):
        "Items coming from adm.tblinfo: the tables of the package selected in the neighbouring dbselect"
        frame = pane.framePane(frameCode='frameMultibuttonStore',height='400px')
        bar = frame.top.slotToolbar(slots='10,package_select,*,mb,10')
        bar.package_select.dbselect(value='^.package',dbtable='adm.pkginfo')
        mb = bar.mb.multibutton(value='^.table_selected',caption='tblid')
        mb.store(table='adm.tblinfo',where='$pkgid=:pkg',pkg='^.package')

    def test_7_multibuttonForm(self,pane):
        """multiButtonForm opened as a remoteDialog: one button per table of the picked package, each with its own form.
        The package is kept at the ABSOLUTE path aux.package on purpose: the dialog content is built outside the case and reads it from there"""
        bc = pane.borderContainer(height='500px')
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.button('Open',action='genro.dlg.remoteDialog("pr_multi","multibuttonPackageForm");')
        fb.dbselect(value='^aux.package',dbtable='adm.pkginfo',lbl='Package')

    @public_method
    def multibuttonPackageForm(self,pane,**kwargs):
        "Content of the remoteDialog of test_7_multibuttonForm: a multiButtonForm on the adm.tblinfo records of aux.package"
        bc = pane.borderContainer(height='300px',width='400px',datapath='multibutton_form')
        bc.contentPane(region='center').multiButtonForm(table='adm.tblinfo',condition='$pkgid=:pkg',caption='tblid',
                                condition_pkg='^aux.package',condition__onBuilt=True,formResource='Form')

    def test_8_multibutton_dbstore_mixed(self,pane):
        "Three multibuttons on one value: a sticky item, the adm.tblinfo tables of the picked package, and one hidden unless the package is adm"
        frame = pane.framePane(frameCode='frameMultibuttonStoreMixed',height='400px')
        bar = frame.top.slotToolbar(slots='10,package_select,*,mb_0,5,mb,5,mb_1,10')
        bar.package_select.dbselect(value='^.package',dbtable='adm.pkginfo')
        mb_0 = bar.mb_0.multibutton(value='^.curval',caption='nome',mandatory=False)
        mb_0.item('Pippo',sticky=True)

        mb = bar.mb.multibutton(value='^.curval',caption='tblid',mandatory=False)
        mb.store(table='adm.tblinfo',where='$pkgid=:pkg',pkg='^.package')

        mb_1 = bar.mb_1.multibutton(value='^.curval',caption='nome',hidden='^.package?=#v!="adm"',mandatory=False)
        mb_1.item('Paperino',sticky=True)

    def test_9_multibutton_dark_container(self,pane):
        """Hover and pressed states on a dark container"""
        pane.data('.dark','pluto')
        box = pane.div(background='var(--toolbar-dark-bg)',padding='12px')
        box.multibutton(value='^.dark',values='pippo:Pippo,pluto:Pluto,paperino:Paperino')

    def test_10_multibutton_insert(self,pane):
        "plusItem asks for a package and appends it; the second multibutton lists that package's tables"
        pane.data('.packages.store', Bag())
        mbpkg = pane.multibutton(value='^.package', items='^.packages.store',
                        identifier='pkgid',caption='pkgid',deleteAction=True)
        mbpkg.plusItem(ask=dict(title='New package',fields=[
                    dict(name='pkgid',lbl='Package',wdg='dbselect',dbtable='adm.pkginfo')
                ]),selectLast=True)
        mbtbl = pane.multibutton(value='^.table_selected',caption='tblid', deleteAction=True)
        mbtbl.store(table='adm.tblinfo',where='$pkgid=:pkg',pkg='^.package')

    def getmbdata(self):
        "Bag of code/caption items shared by test_2_multibutton_storepath and test_3_multibutton_items_path"
        result = Bag()
        result.setItem('pippo',None,caption='Pippo')
        result.setItem('pluto',None,caption='Pluto')
        result.setItem('paperino',None,caption='Paperino')
        return result
