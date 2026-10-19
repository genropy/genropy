# -*- coding: utf-8 -*-

"""Ask and prompt dialogs: legacy formbuilder vs formlet

``ask=dict(...)`` and ``genro.dlg.prompt`` lay their fields out with the legacy
formbuilder table (label on the left) unless ``formlet`` says otherwise.
``formlet=True`` / ``formlet=False`` decides for one dialog; without it the
dialog follows the instance default::

    <gui use_formlets="true"/>

in ``instanceconfig.xml``. The header of each case shows the default this
instance is running with.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def _instanceDefault(self, pane):
        pane.div('==genro.startArgs.useFormlets?"Instance default: formlet":"Instance default: formbuilder"',
                 font_style='italic', color='#666', margin_bottom='6px')

    def _colorFields(self):
        return [dict(name='myvalue', lbl='My value', validate_notnull=True),
                dict(name='mycolor', lbl='Color', tag='combobox',
                     values='orange,green,blue')]

    def _colorResult(self, pane):
        pane.div('^.myvalue', color='^.mycolor', margin_top='6px')

    def test_0_instance_default(self, pane):
        "No formlet kw: the dialog follows the instance default"
        self._instanceDefault(pane)
        pane.button('Ask', action="SET .myvalue = myvalue; SET .mycolor = mycolor;",
                    ask=dict(title='Which one', fields=self._colorFields()))
        self._colorResult(pane)

    def test_1_formlet_true(self, pane):
        "formlet=True: labels on top, whatever the instance default"
        pane.button('Ask (formlet)', action="SET .myvalue = myvalue; SET .mycolor = mycolor;",
                    ask=dict(title='Which one', formlet=True, fields=self._colorFields()))
        self._colorResult(pane)

    def test_2_formlet_false(self, pane):
        "formlet=False: legacy table with labels on the left, whatever the instance default"
        pane.button('Ask (formbuilder)', action="SET .myvalue = myvalue; SET .mycolor = mycolor;",
                    ask=dict(title='Which one', formlet=False, fields=self._colorFields()))
        self._colorResult(pane)

    def test_3_two_columns(self, pane):
        "cols=2 with a colspan=2 textarea: same tiling in both layouts"
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

    def test_4_dtype_and_defaults(self, pane):
        "Widgets from dtype, default values taken from the action parameters"
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

    def test_5_prompt_single_field(self, pane):
        "genro.dlg.prompt with a single lbl field"
        for label, formlet in (('Formlet', 'true'), ('Formbuilder', 'false'), ('Instance default', 'null')):
            pane.button(label, action=f"""genro.dlg.prompt('Change title',
                            {{lbl:'Title', formlet:{formlet},
                              action:function(value){{SET .title = value;}}}},this);""")
        pane.div('^.title', margin_top='6px')

    def test_6_prompt_message_and_fields(self, pane):
        "genro.dlg.prompt with a message above a widget list"
        for label, formlet in (('Formlet', 'true'), ('Formbuilder', 'false')):
            pane.button(label, action=f"""genro.dlg.prompt('Invite',
                            {{msg:'Who should receive the invitation?', formlet:{formlet},
                              widget:[{{value:'^.email', lbl:'Email', validate_email:true}},
                                      {{value:'^.role', lbl:'Role', wdg:'filteringSelect',
                                        values:'admin:Admin,user:User'}}],
                              action:function(result){{SET .invite = result.getItem('email')+' / '+result.getItem('role');}}}},this);""")
        pane.div('^.invite', margin_top='6px')
