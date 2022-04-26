# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires="""gnrcomponents/testhandler:TestHandlerBase,
                    gnrcomponents/tpleditor:TemplateEditor,
                    gnrcomponents/tpleditor:PaletteTemplateEditor"""

    def test_0_templateEditor(self,pane):
        "Template Editor can be embedded directly in contentPane"
        bc = pane.borderContainer(height='600px')
        bc.contentPane(region='center').templateEditor(maintable='fatt.fattura')

    def test_1_importTemplate(self,pane):
        "ckEditor is just the Template Editor block where text can be edited"
        content = pane.borderContainer(height='625px')
        top = content.borderContainer(region='top', height='25px')
        top.button('IMPORTA TEMPLATE').dataRpc(self.importTemplate, _ask=dict(title='Import template', 
                                    fields=[dict(name='query_object_id', lbl='Template', tag='dbselect', hasDownArrow=True, 
                                    table='adm.userobject', condition='$objtype=:tpl', condition_tpl='template',
                                    rowcaption='$code,$description', auxColumns='$description,$userid')]))

        middle = content.contentPane(region='center')
        middle.ckeditor(value='^.body', height='100%', width='100%')

    @public_method
    def importTemplate(self, query_object_id=None):
        compiled_data = Bag(self.db.table('adm.userobject').readColumns(query_object_id, columns='$data'))
        compiled_tpl = compiled_data['compiled.main']
        self.setInClientData(value=compiled_tpl, path='test.test_1_importTemplate.body')

    def test_2_palette(self,pane):
        "paletteTemplateEditor shows an icon to open Template Editor inside a palette"
        pane.paletteTemplateEditor(maintable='fatt.fattura', paletteCode='templatePaletteCode',
                                        dockButton_iconClass='iconbox create_edit_html_template')