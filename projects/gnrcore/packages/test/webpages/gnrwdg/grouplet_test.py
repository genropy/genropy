# -*- coding: utf-8 -*-

"""Test page for Grouplet widget"""

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler"""

    def test_1_handler(self, pane):
        """Grouplet with handler callable"""
        pane.grouplet(value='^.ship_address',handler=self.grp_address)

    def test_2_value_path(self, pane):
        """Grouplet bound to a data value path"""
        pane.data('.contact', Bag(dict(email='test@example.com', phone='123456')))
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.name', lbl='Name')
        pane.grouplet(value='^.contact', handler=self.grp_contact)

    def test_3_multiple_grouplets(self, pane):
        """Multiple grouplets on the same page"""
        bc = pane.borderContainer(height='400px')
        left = bc.contentPane(region='left', width='50%', splitter=True)
        right = bc.contentPane(region='center')
        left.grouplet(value='^.addresses',handler=self.grp_address)
        right.grouplet(value='^.contacts',handler=self.grp_contact)

    def test_4_resource(self, pane):
        """Grouplet loaded from resource file"""
        pane.grouplet(value='^.address_in_res',resource='address_fields')

    @public_method
    def grp_address(self, pane,**kwargs):
        fb = pane.formlet(cols=3, border_spacing='3px')
        fb.textbox(value='^.street', lbl='Street',colspan=3)
        fb.textbox(value='^.city', lbl='City')
        fb.textbox(value='^.zip', lbl='ZIP',width='5em')
        fb.textbox(value='^.country', lbl='Country')


    @public_method
    def grp_contact(self, pane, **kwargs):
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.textbox(value='^.email', lbl='Email')
        fb.textbox(value='^.phone', lbl='Phone')
        fb.dateTextBox(value='^.birthdate', lbl='Birth Date')
        fb.textbox(value='^.notes', lbl='Notes', colspan=2, width='100%')

