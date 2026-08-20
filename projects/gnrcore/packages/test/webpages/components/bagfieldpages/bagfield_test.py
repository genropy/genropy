# -*- coding: utf-8 -*-

"""bagField: edit a Bag stored in a single field through a sub-form

A bagField renders a button that opens a dialog holding a form; what the form
writes is stored as a Bag under the field's own value path. The form can be
supplied in three ways: a method passed explicitly, a bf_<name> method on the
page, or a BagField_<name> class in a _resources module — this page shows all
three.
"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull"""

    def test_1_pane(self, pane):
        """Explicit method: the form is the callable passed as method=

        myhandler receives the dialog pane and fills it, so the bagField needs
        no naming convention at all.
        """
        bc = pane.borderContainer(height='400px', _class='mum')
        top = bc.contentPane(region='top', height='200px', _class='zzz')
        top.bagField(value='^.value', method=self.myhandler)
        bc.contentPane(region='center')

    def test_2_field(self, pane):
        """Convention on the page: bf_alfa and bf_beta serve .alfa and .beta

        With no method= the component looks for a bf_<field> method on the
        page, where <field> is the last segment of the value path. Two fields,
        two different forms.
        """
        bc = pane.borderContainer(height='400px')
        bc.contentPane(region='top', height='50px', background='silver')
        center = bc.contentPane(region='center')
        fb = center.formbuilder(cols=2, lblpos='T')
        fb.bagField('^.alfa', lbl='Alfa')
        fb.bagField('^.beta', lbl='Beta')

    def test_3_field(self, pane):
        """field= decouples the form from the value path

        Both fields here are edited by bf_alfa: the second one stores its Bag
        under .alfa_2 but declares field='alfa', so the same form is reused on
        a different destination.
        """
        bc = pane.borderContainer(height='400px')
        bc.contentPane(region='top', height='50px', background='silver')
        center = bc.contentPane(region='center')
        fb = center.formbuilder(cols=2, lblpos='T')
        fb.bagField('^.alfa', lbl='Alfa')
        fb.bagField('^.alfa_2', lbl='Alfa 2', field='alfa')

    def test_4_resource(self, pane):
        """Convention in a resource: BagField_gamma and BagField_delta

        When the page has no bf_<field> method the lookup continues into the
        _resources modules, where a BagFieldForm subclass named
        BagField_<field> provides bf_content. See
        _resources/bf_bagfield_test.py.
        """
        bc = pane.borderContainer(height='400px')
        bc.contentPane(region='top', height='50px', background='silver')
        center = bc.contentPane(region='center')
        fb = center.formbuilder(cols=2, lblpos='T')
        fb.bagField('^.gamma', lbl='Gamma')
        fb.bagField('^.delta', lbl='Delta')

    @public_method
    def myhandler(self, pane, **kwargs):
        """Form used by test_1_pane, passed explicitly as method="""
        fb = pane.formbuilder()
        fb.textbox(value='^.foo', lbl='Foo')
        fb.textbox(value='^.bar', lbl='Bar')

    @public_method
    def bf_alfa(self, pane, **kwargs):
        """Form found by convention for the bagField named alfa"""
        fb = pane.formbuilder()
        fb.textbox(value='^.foo', lbl='Foo')
        fb.textbox(value='^.bar', lbl='Bar')

    @public_method
    def bf_beta(self, pane, **kwargs):
        """Form found by convention for the bagField named beta"""
        fb = pane.formbuilder()
        fb.textbox(value='^.boo', lbl='Boo')
        fb.textbox(value='^.sob', lbl='Sob')
