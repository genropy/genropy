# -*- coding: utf-8 -*-

"filteringSelect and comboBox"

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'filteringSelect and comboBox'

    def isDeveloper(self):
        return True
         
    def test_00_filtering(self,pane):
        "Basic filteringSelect. Choose between available values, then press reset to clear values"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.data('.code','1')
        fb.filteringSelect(value='^.code',values='0:Zero robot killed,1:One bridge fallen,2:Two babies born',lbl='With code')
        fb.filteringSelect(value='^.description',values='Zero robot killed,One bridge fallen,Two babies born',lbl='No code',
                           fullTextSearch=True)
        fb.button('Reset values',action='SET .code=null;SET .description=null')
        fb.div('^.code')
        fb.div('^.description')
        
    def test_01_filtering(self,pane):
        "Basic filteringSelect, list of values built as Bag"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        b = Bag()
        b.setItem('r1',None,caption='Foo',id='A')
        b.setItem('r2',None,caption='Bar',id='B')
        b.setItem('r3',None,caption='Spam',id='C')
        fb.data('.store',b)
        fb.filteringSelect(value='^.tbag',lbl='Test bag 1',storepath='.store')
        fb.div('^.tbag')
        
    def test_02_combobox(self,pane):
        "Basic comboBox. Choose values or manually insert a new one."
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.comboBox(value='^.description',values='Zero,One,Two',lbl='Combo')
        fb.div('^.description')
        
    def test_03_filtering(self,pane):
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
        

    def test_04_filteringCombo(self, pane):
        "filteringSelect vs comboBox: in comboBox you can choose values even not suggested values. Displayed value vs real value"
        fb=pane.formbuilder(cols=2)
        fb.filteringSelect(lbl='filteringSelect',value='^.filtering',values='PI:Pippo,PL:Pluto,PA:Paperino')
        fb.comboBox(lbl='comboBox',value='^.combobox',values='PI:Pippo,PL:Pluto,PA:Paperino')
        fb.div('^.filtering')
        fb.div('^.combobox')

    def test_05_localizer(self, pane):
        "filteringSelect with package selector built by localization manager"
        items = Bag()
        for s in self.db.application.localizer.slots:
            items.setItem(s['code'],s['code'],folderPath=s['destFolder'],code=s['code'])
        pane.data('.blocks',items)
        pane.formbuilder(cols=1,border_spacing='3px').filteringSelect(
                                    value='^.currentLocalizationBlock', lbl='!![en]Package',
                                    storepath='.blocks', storeid='code', storecaption='code')

    def test_06_addmissing_prepopulated(self, pane):
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

    def test_07_addmissing_prepopulated_values(self, pane):
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

    def test_08_addmissing_record_load(self, pane):
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

    def test_09_addmissing_validate_case(self, pane):
        """addMissingValue + validate_case='capitalize'.
        Store seeded with canonical entries 'Red', 'Green', 'Blue'. Typing
        'red' in any combo: validate_case normalises to 'Red' before
        addMissingValue checks the store, so the canonical entry matches
        and no duplicate is added. Typing 'yellow' yields 'Yellow' and a
        single new entry shared across the three combos."""
        colors = Bag()
        colors.setItem('r_0', None, id='Red', caption='Red')
        colors.setItem('r_1', None, id='Green', caption='Green')
        colors.setItem('r_2', None, id='Blue', caption='Blue')
        pane.data('.colors', colors)
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.c1', lbl='Color 1', storepath='.colors',
                    addMissingValue=True, validate_case='capitalize')
        fb.div('^.c1', lbl='value')
        fb.comboBox(value='^.c2', lbl='Color 2', storepath='.colors',
                    addMissingValue=True, validate_case='capitalize')
        fb.div('^.c2', lbl='value')
        fb.comboBox(value='^.c3', lbl='Color 3', storepath='.colors',
                    addMissingValue=True, validate_case='capitalize')
        fb.div('^.c3', lbl='value')
        pane.div('Shared store (.colors):', font_weight='bold', margin_top='10px')
        pane.div('^.colors?#asText', white_space='pre', font_family='monospace')

    def test_10_addmissing_validate_case_upper(self, pane):
        """addMissingValue + validate_case='upper' on a canonical store.
        The store is seeded with already-uppercase codes. Typing 'foo' is
        normalised by validate_case to 'FOO' before _autoAddToStore sees
        the value, so the widget never adds the lowercase form. Typing
        'FOO' (already canonical) matches the existing entry — no add."""
        codes = Bag()
        codes.setItem('r_0', None, id='FOO', caption='FOO')
        codes.setItem('r_1', None, id='BAR', caption='BAR')
        pane.data('.codes', codes)
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.k1', lbl='Code', storepath='.codes',
                    addMissingValue=True, validate_case='upper')
        fb.div('^.k1', lbl='value')
        pane.div("Try typing 'foo', 'bar', 'baz'. Only 'baz' (=> 'BAZ') "
                 "should be appended.", font_style='italic', margin_top='5px')
        pane.div('Shared store (.codes):', font_weight='bold', margin_top='10px')
        pane.div('^.codes?#asText', white_space='pre', font_family='monospace')

    def test_11_addmissing_validate_regex(self, pane):
        """addMissingValue + validate_regex.
        The widget accepts only 3-letter uppercase codes. validate_case
        normalises the input, then validate_regex either accepts or rejects.
        _autoAddToStore checks sourceNode._validations.error before adding,
        so rejected values never end up in the store."""
        pane.data('.tla_store', Bag())
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.tla', lbl='TLA', storepath='.tla_store',
                    addMissingValue=True, validate_case='upper',
                    validate_regex=' ^[A-Z]{3}$',
                    validate_regex_error='Three uppercase letters required')
        fb.div('^.tla', lbl='value')
        pane.div("Try 'abc' (accepted as 'ABC'), 'abcd' (rejected, not added).",
                 font_style='italic', margin_top='5px')
        pane.div('Shared store (.tla_store):', font_weight='bold', margin_top='10px')
        pane.div('^.tla_store?#asText', white_space='pre', font_family='monospace')

    def test_12_addmissing_validate_call(self, pane):
        """addMissingValue + validate_call + validate_case.
        validate_call collapses internal whitespace, validate_case applies
        title case. Combined they normalise '  mario   rossi  ' into
        'Mario Rossi'. The store is seeded with two canonical full names:
        retyping any of them in any form should not produce duplicates."""
        people = Bag()
        people.setItem('r_0', None, id='Mario Rossi', caption='Mario Rossi')
        people.setItem('r_1', None, id='Luigi Verdi', caption='Luigi Verdi')
        pane.data('.people', people)
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.name', lbl='Full name', storepath='.people',
                    addMissingValue=True,
                    validate_call="return {value: value.trim().replace(/\\s+/g, ' ')};",
                    validate_case='title')
        fb.div('^.name', lbl='value')
        pane.div("Try '  mario   rossi  ' (matches 'Mario Rossi'). "
                 "Try '  pippo  baudo  ' (added as 'Pippo Baudo').",
                 font_style='italic', margin_top='5px')
        pane.div('Shared store (.people):', font_weight='bold', margin_top='10px')
        pane.div('^.people?#asText', white_space='pre', font_family='monospace')

    def test_13_addmissing_purge_sweep(self, pane):
        """Clean-up of auto-added entries.
        Two combos share a store seeded with two official tags. After the
        user adds extra values, the 'Reset to official' button clears the
        widget values first (so the deferred callback does not re-add) and
        rebuilds the store with only the official entries. The dropdowns of
        both combos must reflect the reset immediately."""
        official = ['alpha', 'beta']
        tags = Bag()
        official_bag = Bag()
        for i, t in enumerate(official):
            tags.setItem('r_%i' % i, None, id=t, caption=t)
            official_bag.setItem('r_%i' % i, None, id=t, caption=t)
        pane.data('.tags', tags)
        pane.data('.official', official_bag)
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.a', lbl='Tag A', storepath='.tags', addMissingValue=True)
        fb.div('^.a', lbl='value')
        fb.comboBox(value='^.b', lbl='Tag B', storepath='.tags', addMissingValue=True)
        fb.div('^.b', lbl='value')
        bar = pane.div(margin_top='10px')
        bar.button('Reset to official', action="""
            SET .a = null;
            SET .b = null;
            var src = GET .official;
            SET .tags = src ? src.deepCopy() : new gnr.GnrBag();
        """)
        pane.div('Shared store (.tags):', font_weight='bold', margin_top='10px')
        pane.div('^.tags?#asText', white_space='pre', font_family='monospace')

    def test_14_addmissing_purge_marker(self, pane):
        """Selective purge using the __autoadded marker.
        _autoAddToStore tags auto-added nodes with __autoadded=true. A purge
        helper iterates the bag, drops only the marked nodes and keeps the
        seeded ones. Useful when 'official' entries are not known by the
        client and the only way to tell them apart is the marker itself."""
        tags = Bag()
        tags.setItem('r_0', None, id='alpha', caption='alpha')
        tags.setItem('r_1', None, id='beta', caption='beta')
        pane.data('.tags', tags)
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.a', lbl='Tag A', storepath='.tags', addMissingValue=True)
        fb.div('^.a', lbl='value')
        fb.comboBox(value='^.b', lbl='Tag B', storepath='.tags', addMissingValue=True)
        fb.div('^.b', lbl='value')
        bar = pane.div(margin_top='10px')
        bar.button('Purge auto-added', action="""
            SET .a = null;
            SET .b = null;
            var bag = GET .tags;
            if(bag){
                var nodes = bag.getNodes().slice();
                for(var i = 0; i < nodes.length; i++){
                    if(nodes[i].attr.__autoadded){
                        bag.popNode(nodes[i].label);
                    }
                }
            }
        """)
        pane.div('Shared store (.tags) — __autoadded nodes are highlighted '
                 'in the dump:', font_weight='bold', margin_top='10px')
        pane.div('^.tags?#asText', white_space='pre', font_family='monospace')

    def test_15_addmissing_invalid_not_added(self, pane):
        """addMissingValue must not enrich the store with invalid values.
        Pure regex validation (no validate_case, no validate_call): if the
        widget is left in error state, _autoAddToStore aborts thanks to the
        sourceNode._validations.error guard. The store stays clean."""
        emails = Bag()
        emails.setItem('r_0', None, id='alice@example.com', caption='alice@example.com')
        pane.data('.emails', emails)
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.comboBox(value='^.email', lbl='Email', storepath='.emails',
                    addMissingValue=True,
                    validate_regex=' ^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$',
                    validate_regex_error='Not a valid email')
        fb.div('^.email', lbl='value')
        pane.div("Type 'pippo' (invalid, NOT added). Then 'bob@example.com' "
                 "(valid, added). The store must keep alice plus only "
                 "well-formed emails.", font_style='italic', margin_top='5px')
        pane.div('Shared store (.emails):', font_weight='bold', margin_top='10px')
        pane.div('^.emails?#asText', white_space='pre', font_family='monospace')
