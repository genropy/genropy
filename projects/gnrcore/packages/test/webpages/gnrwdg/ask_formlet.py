# -*- coding: utf-8 -*-

"""Client formbuilder: legacy table vs formlet

``genro.dev.formbuilder`` lays fields out in the legacy table (label on the
left) unless ``formlet`` says otherwise. ``formlet=True`` / ``formlet=False``
decides for one form; without it the form follows the experimental instance
flag::

    <experimental><gui use_formlets_in_js_fb="true"/></experimental>

in ``instanceconfig.xml``. Ask and prompt dialogs, tooltip editors with
``fields``, the query parameters dialog and the dateTimeTextBox menu all go
through it; the two formbuilders sitting in a toolbar pin ``formlet=False``.

Every case carries the same switch: it starts from the instance value and
flips ``genro.startArgs.useFormletsInJsFb`` on the fly, so the cases without
an explicit ``formlet`` can be compared without restarting the instance. The
dateTimeTextBox menu is built with its widget, so that case is rebuilt when
the switch changes. The dynamicform case has its own switch for
``df_formlet``: instance flag ``use_formlets_in_dynamicform``, True or False.
"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                    gnrcomponents/dynamicform/dynamicform:DynamicForm"""

    def _instanceDefault(self, pane):
        if not getattr(self, '_formletSwitchReady', False):
            self._formletSwitchReady = True
            pane.dataController("SET gnr.test_formlet_switch = genro.startArgs.useFormletsInJsFb || false;",
                                _onStart=True)
            pane.dataController("genro.startArgs.useFormletsInJsFb = enabled;",
                                enabled='^gnr.test_formlet_switch')
        pane.checkbox(value='^gnr.test_formlet_switch', label='use_formlets_in_js_fb (on the fly)',
                      margin_bottom='6px')

    def _colorFields(self):
        return [dict(name='myvalue', lbl='My value', validate_notnull=True),
                dict(name='mycolor', lbl='Color', tag='combobox',
                     values='orange,green,blue')]

    def _colorResult(self, pane):
        pane.div('^.myvalue', color='^.mycolor', margin_top='6px')

    def test_00_instance_default(self, pane):
        "No formlet kw: the dialog follows the instance default"
        self._instanceDefault(pane)
        pane.button('Ask', action="SET .myvalue = myvalue; SET .mycolor = mycolor;",
                    ask=dict(title='Which one', fields=self._colorFields()))
        self._colorResult(pane)

    def test_01_formlet_true(self, pane):
        "formlet=True: labels on top, whatever the instance default"
        self._instanceDefault(pane)
        pane.button('Ask (formlet)', action="SET .myvalue = myvalue; SET .mycolor = mycolor;",
                    ask=dict(title='Which one', formlet=True, fields=self._colorFields()))
        self._colorResult(pane)

    def test_02_formlet_false(self, pane):
        "formlet=False: legacy table with labels on the left, whatever the instance default"
        self._instanceDefault(pane)
        pane.button('Ask (formbuilder)', action="SET .myvalue = myvalue; SET .mycolor = mycolor;",
                    ask=dict(title='Which one', formlet=False, fields=self._colorFields()))
        self._colorResult(pane)

    def test_03_two_columns(self, pane):
        "cols=2 with a colspan=2 textarea: same tiling in both layouts"
        self._instanceDefault(pane)
        fields = [dict(name='first_name', lbl='First name'),
                  dict(name='last_name', lbl='Last name', validate_notnull=True),
                  dict(name='notes', lbl='Notes', tag='simpleTextArea', colspan=2, height='60px')]
        action = "SET .result = first_name+' '+last_name+(notes?' ('+notes+')':'');"
        pane.button('Formlet', action=action,
                    ask=dict(title='Person', formlet=True, cols=2, fields=fields,
                             dlg_width='420px'))
        pane.button('Formbuilder', action=action,
                    ask=dict(title='Person', formlet=False, cols=2, fields=fields,
                             dlg_width='420px'))
        pane.div('^.result', margin_top='6px')

    def test_04_dtype_and_defaults(self, pane):
        "Widgets from dtype, default values taken from the action parameters"
        self._instanceDefault(pane)
        pane.data('.when', self.workdate)
        pane.data('.qty', 3)
        fields = [dict(name='when', lbl='Date', dtype='D'),
                  dict(name='qty', lbl='Quantity', dtype='L', validate_notnull=True),
                  dict(name='urgent', lbl='Urgent', dtype='B')]
        action = "SET .when = when; SET .qty = qty; SET .urgent = urgent;"
        for label, formlet in (('Formlet', True), ('Formbuilder', False)):
            pane.button(label, action=action, when='=.when', qty='=.qty', urgent='=.urgent',
                        ask=dict(title='Order', formlet=formlet, fields=fields))
        pane.div('==`${when?when.toLocaleDateString():""} - ${qty} - ${urgent}`',
                 when='^.when', qty='^.qty', urgent='^.urgent', margin_top='6px')

    def test_05_prompt_single_field(self, pane):
        "genro.dlg.prompt with a single lbl field"
        self._instanceDefault(pane)
        for label, formlet in (('Formlet', 'true'), ('Formbuilder', 'false'), ('Instance default', 'null')):
            pane.button(label, action=f"""genro.dlg.prompt('Change title',
                            {{lbl:'Title', formlet:{formlet},
                              action:function(value){{SET .title = value;}}}},this);""")
        pane.div('^.title', margin_top='6px')

    def test_06_prompt_message_and_fields(self, pane):
        "genro.dlg.prompt with a message above a widget list"
        self._instanceDefault(pane)
        for label, formlet in (('Formlet', 'true'), ('Formbuilder', 'false'), ('Instance default', 'null')):
            pane.button(label, action=f"""genro.dlg.prompt('Invite',
                            {{msg:'Who should receive the invitation?', formlet:{formlet},
                              widget:[{{value:'^.email', lbl:'Email', validate_email:true}},
                                      {{value:'^.role', lbl:'Role', wdg:'filteringSelect',
                                        values:'admin:Admin,user:User'}}],
                              action:function(result){{SET .invite = result.getItem('email')+' / '+result.getItem('role');}}}},this);""")
        pane.div('^.invite', margin_top='6px')

    def test_07_tooltip_fields(self, pane):
        "quickTooltipPane with fields: follows the instance default"
        self._instanceDefault(pane)
        pane.button('Edit', action="genro.dlg.quickTooltipPane({domNode:this.widget.domNode,fields:fields,datapath:'test_tooltip'})",
                    fields=[dict(lbl='Amount', wdg='numberTextBox', value='^.amount'),
                            dict(lbl='Due date', wdg='dateTextBox', value='^.due')])
        pane.div('==`${amount||""} ${due?due.toLocaleDateString():""}`',
                 amount='^test_tooltip.amount', due='^test_tooltip.due', margin_top='6px')

    def test_08_query_parameters(self, pane):
        "The 'Complete query' dialog of a saved query with ? parameters"
        self._instanceDefault(pane)
        pane.button('Complete query', action="""
            var dlg = genro.dlg.quickDialog('Complete query',{datapath:'test_querypars.where',width:'250px',autoSize:true});
            var wherebag = genro.getData('test_querypars.where');
            if(!wherebag){
                wherebag = new gnr.GnrBag();
                genro.setData('test_querypars.where',wherebag);
            }
            genro.dev.dynamicQueryParsFb(dlg.center._('div',{padding:'10px'}),wherebag,
                                         [{lbl:'Customer',relpath:'c_0',dflt:'Rossi'},{lbl:'City',relpath:'c_1'}],1);
            dlg.bottom._('slotBar',{slots:'*,confirm'})._('button','confirm',{label:'Confirm',action:function(){dlg.close_action();}});
            dlg.show_action();""")
        pane.div('==`${c0||""} - ${c1||""}`', c0='^test_querypars.where.c_0',
                 c1='^test_querypars.where.c_1', margin_top='6px')

    def test_09_datetime_menu(self, pane):
        "The date + time menu of dateTimeTextBox, rebuilt when the switch changes"
        self._instanceDefault(pane)
        pane.div(min_height='1px').remote('datetimeCase', enabled='^gnr.test_formlet_switch')

    def remote_datetimeCase(self, pane, enabled=None, **kwargs):
        pane.datetimeTextBox(value='^.dh', width='12em')
        pane.div('^.dh', margin_top='6px')

    def test_10_dynamicform(self, pane):
        "dynamicFormGroup: df_formlet from the instance flag, or forced on the fly"
        pane.filteringSelect(value='^.df_formlet', lbl='df_formlet',
                             values='instance:Instance flag (use_formlets_in_dynamicform),on:True,off:False',
                             width='22em', margin_bottom='6px')
        pane.data('.df_formlet', 'instance')
        pane.div(min_height='1px').remote('dynamicFormCase', df_mode='^.df_formlet')
        pane.div('==rec?rec.getFormattedValue():""', rec='^.rec', _delay=200,
                 font_family='monospace', font_size='.8em', margin_top='6px')

    def remote_dynamicFormCase(self, pane, df_mode=None, **kwargs):
        fields = [dict(code='colore', description='Colore', data_type='T',
                       wdg_tag='filteringselect', source_filteringselect='r:Rosso,v:Verde',
                       mandatory=True),
                  dict(code='taglia', description='Taglia', data_type='L', wdg_tag='numbertextbox'),
                  dict(code='note', description='Note', data_type='T', wdg_tag='simpletextarea',
                       wdg_kwargs=Bag(dict(colspan=2, height=60)))]
        pane.div(datapath='.rec').dynamicFormGroup(fields=fields, ncol=2,
                              df_formlet={'on': True, 'off': False}.get(df_mode))

    def test_11_user_object(self, pane):
        "genro.dev.userObjectDialog, the save dialog of queries, views and other user objects"
        self._instanceDefault(pane)
        for label, preview in (('Save', 'false'), ('Save with preview', 'true')):
            pane.button(label, action=f"""genro.dev.userObjectDialog('Save view','test_userobject',
                            function(dlg){{dlg.close_action();}},{preview});""")
        pane.div('==`${code||""} ${description||""} ${priv?"(private)":""}`',
                 code='^test_userobject.code', description='^test_userobject.description',
                 priv='^test_userobject.private', margin_top='6px')

    def test_12_fixed_width_fields(self, pane):
        "Fields wider than the dialog: it grows to them and keeps the right margin as wide as the left"
        self._instanceDefault(pane)
        fields = [dict(name='order', lbl='Order', width='20em'),
                  dict(name='chapter', lbl='Chapter', width='30em'),
                  dict(name='account', lbl='Account', width='30em')]
        action = "SET .fixed = [order,chapter,account].join(' / ');"
        for label, formlet in (('Formlet', True), ('Formbuilder', False)):
            pane.button(label, action=action,
                        ask=dict(title='Allocation', formlet=formlet, fields=fields))
        pane.div('^.fixed', margin_top='6px')
