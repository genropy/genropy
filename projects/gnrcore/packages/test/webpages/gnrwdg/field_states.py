# -*- coding: utf-8 -*-

"""Visual comparison of field states: normal, readOnly, disabled"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_textbox(self, pane):
        "TextBox: normal vs readOnly vs disabled"
        fb = pane.formbuilder(cols=3, border_spacing='10px', fld_width='100%')
        fb.data('.txt_val', 'Sample text')
        fb.textbox(value='^.txt_val', lbl='Normal')
        fb.textbox(value='^.txt_val', lbl='ReadOnly', readOnly=True)
        fb.textbox(value='^.txt_val', lbl='Disabled', disabled=True)

    def test_2_numbertextbox(self, pane):
        "NumberTextBox: normal vs readOnly vs disabled"
        fb = pane.formbuilder(cols=3, border_spacing='10px', fld_width='100%')
        fb.data('.num_val', 42)
        fb.numberTextBox(value='^.num_val', lbl='Normal')
        fb.numberTextBox(value='^.num_val', lbl='ReadOnly', readOnly=True)
        fb.numberTextBox(value='^.num_val', lbl='Disabled', disabled=True)

    def test_3_datetextbox(self, pane):
        "DateTextBox: normal vs readOnly vs disabled"
        fb = pane.formbuilder(cols=3, border_spacing='10px', fld_width='100%')
        fb.dateTextBox(value='^.date_val', lbl='Normal')
        fb.dateTextBox(value='^.date_val', lbl='ReadOnly', readOnly=True)
        fb.dateTextBox(value='^.date_val', lbl='Disabled', disabled=True)

    def test_4_textarea(self, pane):
        "TextArea: normal vs readOnly vs disabled"
        fb = pane.formbuilder(cols=3, border_spacing='10px', fld_width='100%')
        fb.data('.area_val', 'Multiline\nsample text')
        fb.simpleTextArea(value='^.area_val', lbl='Normal', height='4em')
        fb.simpleTextArea(value='^.area_val', lbl='ReadOnly', readOnly=True, height='4em')
        fb.simpleTextArea(value='^.area_val', lbl='Disabled', disabled=True, height='4em')

    def test_5_form(self, pane):
        "Form with mixed field states and validation"
        form = pane.frameForm(frameCode='testForm', datapath='.formtest',
                              store='memory', height='400px',
                              border='1px solid silver', rounded=6)
        fb = form.record.formbuilder(cols=2, border_spacing='10px', fld_width='100%')
        fb.data('.readonly_val', 'Fixed value')
        fb.data('.readonly_num', 100)
        fb.textbox(value='^.name', lbl='Name (notnull)',
                   validate_notnull=True)
        fb.textbox(value='^.surname', lbl='Surname')
        fb.textbox(value='^.readonly_val', lbl='ReadOnly text',
                   readOnly=True)
        fb.numberTextBox(value='^.readonly_num', lbl='ReadOnly number',
                         readOnly=True)
        fb.textbox(value='^.email', lbl='Email (notnull)',
                   validate_notnull=True)
        fb.numberTextBox(value='^.age', lbl='Age (notnull)',
                         validate_notnull=True)
        fb.textbox(value='^.city', lbl='City', disabled=True)
        fb.numberTextBox(value='^.zip', lbl='ZIP', disabled=True)
        fb.checkboxtext(value='^.opts', values='X:One,Y:Two,Z:Three',
                        lbl='Options popup (notnull)', popup=True,
                        validate_notnull=True)
        fb.checkboxtext(value='^.colors', values='R:Red,G:Green,B:Blue',
                        lbl='Colors (no validation)')
        fb.dateTextBox(value='^.birthdate', lbl='Date (notnull)',
                       validate_notnull=True)
        bar = form.bottom.slotBar('locker,*,savebtn,5')
        bar.locker.slotButton('Locker', iconClass='iconbox lock', showLabel=False,
                              action='this.form.publish("setLocked","toggle");',
                              formsubscribe_onLockChange="""var locked=$1.locked;
                              this.widget.setIconClass(locked?'iconbox lock':'iconbox unlock');""")
        bar.savebtn.button('Save', action='this.form.save()')
        pane.dataController("frm.newrecord()",
                            frm=form.js_form, _onStart=True)
