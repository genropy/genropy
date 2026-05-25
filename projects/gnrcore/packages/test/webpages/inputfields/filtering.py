# -*- coding: utf-8 -*-

"filteringSelect and comboBox"

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'filteringSelect and comboBox'

    def isDeveloper(self):
        return True
         
    def test_0_filtering(self,pane):
        "Basic filteringSelect. Choose between available values, then press reset to clear values"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.data('.code','1')
        fb.filteringSelect(value='^.code',values='0:Zero robot killed,1:One bridge fallen,2:Two babies born',lbl='With code')
        fb.filteringSelect(value='^.description',values='Zero robot killed,One bridge fallen,Two babies born',lbl='No code',
                           fullTextSearch=True)
        fb.button('Reset values',action='SET .code=null;SET .description=null')
        fb.div('^.code')
        fb.div('^.description')
        
    def test_1_filtering(self,pane):
        "Basic filteringSelect, list of values built as Bag"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        b = Bag()
        b.setItem('r1',None,caption='Foo',id='A')
        b.setItem('r2',None,caption='Bar',id='B')
        b.setItem('r3',None,caption='Spam',id='C')
        fb.data('.store',b)
        fb.filteringSelect(value='^.tbag',lbl='Test bag 1',storepath='.store')
        fb.div('^.tbag')
        
    def test_2_combobox(self,pane):
        "Basic comboBox. Choose values or manually insert a new one."
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.comboBox(value='^.description',values='Zero,One,Two',lbl='Combo')
        fb.div('^.description')
        
    def test_3_filtering(self,pane):
        "Same list of values built as Bag, but store is built with keys"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        b = Bag()
        b.setItem('A',None,caption='Foo')
        b.setItem('B',None,caption='Bar')
        b.setItem('C',None,caption='Spam')
        fb.data('.store',b)
        fb.filteringSelect(value='^.tbag',lbl='Test bag 3',storepath='.store',
                            storeid='#k')  
        fb.div('^.tbag')
        

    def test_4_filteringCombo(self, pane):
        "filteringSelect vs comboBox: in comboBox you can choose values even not suggested values. Displayed value vs real value"
        fb=pane.formbuilder(cols=2)
        fb.filteringSelect(lbl='filteringSelect',value='^.filtering',values='PI:Pippo,PL:Pluto,PA:Paperino')
        fb.comboBox(lbl='comboBox',value='^.combobox',values='PI:Pippo,PL:Pluto,PA:Paperino')
        fb.div('^.filtering')
        fb.div('^.combobox')

    def test_5_localizer(self, pane):
        "filteringSelect with package selector built by localization manager"
        items = Bag()
        for s in self.db.application.localizer.slots:
            items.setItem(s['code'],s['code'],folderPath=s['destFolder'],code=s['code'])
        pane.data('.blocks',items)
        pane.formbuilder(cols=1,border_spacing='3px').filteringSelect(
                                    value='^.currentLocalizationBlock', lbl='!![en]Package',
                                    storepath='.blocks', storeid='code', storecaption='code')

    def test_6_addmissing_prepopulated(self, pane):
        """addMissingValue with prepopulated store via fb.data().
        Three comboboxes share the same storepath '.tags' which starts with
        two known options. Typing a new value in any combo adds it to the
        shared store so the other two see it immediately."""
        tags = Bag()
        tags.setItem('r_0', None, id='alpha', caption='alpha')
        tags.setItem('r_1', None, id='beta', caption='beta')
        pane.data('.tags', tags)
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.t1', lbl='Tag 1', storepath='.tags', addMissingValue=True)
        fb.div('^.t1', lbl='value')
        fb.comboBox(value='^.t2', lbl='Tag 2', storepath='.tags', addMissingValue=True)
        fb.div('^.t2', lbl='value')
        fb.comboBox(value='^.t3', lbl='Tag 3', storepath='.tags', addMissingValue=True)
        fb.div('^.t3', lbl='value')
        pane.div('Shared store (.tags):', font_weight='bold', margin_top='10px')
        pane.div('^.tags?#asText', white_space='pre', font_family='monospace')

    def test_7_addmissing_prepopulated_values(self, pane):
        """addMissingValue with empty store but prepopulated values.
        The store '.tags' starts empty, but t1/t2/t3 are seeded via fb.data().
        At rendering time each combobox finds its value missing from the store
        and adds it: the shared store ends up containing all three values
        without any user action or dataController."""
        pane.data('.tags', Bag())
        pane.data('.t1', 'foo')
        pane.data('.t2', 'bar')
        pane.data('.t3', 'baz')
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.t1', lbl='Tag 1', storepath='.tags', addMissingValue=True)
        fb.div('^.t1', lbl='value')
        fb.comboBox(value='^.t2', lbl='Tag 2', storepath='.tags', addMissingValue=True)
        fb.div('^.t2', lbl='value')
        fb.comboBox(value='^.t3', lbl='Tag 3', storepath='.tags', addMissingValue=True)
        fb.div('^.t3', lbl='value')
        pane.div('Shared store (.tags):', font_weight='bold', margin_top='10px')
        pane.div('^.tags?#asText', white_space='pre', font_family='monospace')

    def test_8_addmissing_record_load(self, pane):
        """addMissingValue on a simulated record load.
        The store starts empty; pressing 'Load record' writes three values
        at once into the record path. Each combobox sees its value arrive via
        datapath binding and auto-adds it to the shared store. After loading
        all three options become suggestable on every combo."""
        pane.data('.options', Bag())
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.record.color1', lbl='Color 1',
                    storepath='.options', addMissingValue=True)
        fb.div('^.record.color1', lbl='value')
        fb.comboBox(value='^.record.color2', lbl='Color 2',
                    storepath='.options', addMissingValue=True)
        fb.div('^.record.color2', lbl='value')
        fb.comboBox(value='^.record.color3', lbl='Color 3',
                    storepath='.options', addMissingValue=True)
        fb.div('^.record.color3', lbl='value')
        bar = pane.div(margin_top='10px')
        bar.button('Load record A', action="""
            SET .record.color1 = 'red';
            SET .record.color2 = 'green';
            SET .record.color3 = 'blue';
        """)
        bar.button('Load record B', action="""
            SET .record.color1 = 'cyan';
            SET .record.color2 = 'magenta';
            SET .record.color3 = 'yellow';
        """)
        bar.button('Reset', action="""
            SET .record = null;
            SET .options = new gnr.GnrBag();
        """)
        pane.div('Shared store (.options):', font_weight='bold', margin_top='10px')
        pane.div('^.options?#asText', white_space='pre', font_family='monospace')
