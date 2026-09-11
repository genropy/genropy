# -*- coding: utf-8 -*-

"Field text colour against the container it sits in"


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_inheritance(self, pane):
        """An opaque field keeps its own text colour whatever the container sets:
        the coloured container no longer paints the typed text, and the dark one
        no longer hides it"""
        box = pane.div(padding='12px', margin_bottom='14px', border='1px solid #ccc')
        box.div('1. plain container', font_weight='bold', margin_bottom='8px')
        box.textbox(value='^.a', placeholder='type here', width='320px')

        box = pane.div(padding='12px', margin_bottom='14px', border='1px solid #ccc',
                       color='red')
        box.div('2. color:red on the container', font_weight='bold', margin_bottom='8px')
        box.textbox(value='^.b', placeholder='type here', width='320px')

        box = pane.div(padding='12px', margin_bottom='14px', background='#333', color='#fff')
        box.div('3. light text on a dark surface', font_weight='bold', margin_bottom='8px')
        box.textbox(value='^.c', placeholder='type here', width='320px')

    def test_1_borderlessFields(self, pane):
        """borderlessFields is the one case where inheriting is the point: the field
        is transparent, so the light text belongs on the dark surface"""
        box = pane.div(padding='12px', background='#333', color='#fff',
                       _class='borderlessFields')
        box.div('4. same dark surface, borderlessFields', font_weight='bold',
                margin_bottom='8px')
        box.textbox(value='^.d', placeholder='type here', width='320px')
        box.comboBox(value='^.e', values='one,two,three', width='320px')

    def test_2_notEditable(self, pane):
        """readOnly reads --field-readonly-color, which used to be referenced and never
        defined: its inherit fallback hid the value on a light-text container"""
        box = pane.div(padding='12px', background='#333', color='#fff')
        box.div('5. readOnly and disabled on a dark surface', font_weight='bold',
                margin_bottom='8px')
        fb = box.formbuilder(cols=1, border_spacing='3px')
        fb.data('.ro', 'readonly value')
        fb.data('.dis', 'disabled value')
        fb.textbox(value='^.ro', lbl='readOnly', readOnly=True, width='320px')
        fb.textbox(value='^.dis', lbl='disabled', disabled=True, width='320px')

    def test_3_textArea(self, pane):
        """The textarea paints the same background from the same token, so it takes
        the same colour"""
        box = pane.div(padding='12px', background='#333', color='#fff')
        box.div('6. textarea on a dark surface', font_weight='bold', margin_bottom='8px')
        box.simpleTextArea(value='^.f', width='320px', height='80px')
        box.simpleTextArea(value='^.g', width='320px', height='80px', readOnly=True)

    def test_4_forms(self, pane):
        """An ordinary formbuilder: unchanged"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.textbox(value='^.name', lbl='Name')
        fb.textbox(value='^.city', lbl='City')
        fb.comboBox(value='^.kind', lbl='Kind', values='alpha,beta,gamma')
        fb.simpleTextArea(value='^.notes', lbl='Notes', height='60px')
