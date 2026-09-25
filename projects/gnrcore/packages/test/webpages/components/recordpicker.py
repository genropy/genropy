"""Record picker with geographic data, immediate checked paths and themed templates."""

from gnr.core.gnrbag import Bag


COLUMNS = '$nome,$sigla,$regione,@regione.nome AS regione_nome,$codice_istat'
CARD = '<strong>$nome</strong><div>$sigla · $regione_nome</div>'
PREVIEW = '<div>$regione_nome ($regione)</div><hr><div>ISTAT: $codice_istat</div><div>$nome ($sigla)</div>'


class GnrCustomWebPage:
    py_requires = 'gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/recordpicker/recordpicker:RecordPicker'
    css_requires = 'recordpicker/examples'

    def provinces(self, pane):
        if 'glbl' not in self.db.packages:
            pane.div('These examples require the glbl package and its startup data.')
            return False
        store = self.db.table('glbl.provincia').query(columns=COLUMNS, order_by='$nome').selection()
        pane.data('.provinces', store.output('selection', caption=True))
        pane.div('^.checked', lbl='Checked province codes', _class='rp_example_output')
        return True

    def test_0_cards(self, pane):
        """Bag source: empty until typing; clicking writes the checked path immediately."""
        if not self.provinces(pane):
            return
        pane.recordPicker(checkedId='^.checked', storepath='.provinces',
                          columns='nome,sigla,regione_nome', template=CARD, cols=3, boxHeight='240px',
                          nodeId='rp_cards')
        pane.div('The content below stays in place.', _class='rp_example_anchor')

    def test_1_extended_preview(self, pane):
        """Single selection: click a row to select it and display its extended preview."""
        if not self.provinces(pane):
            return
        pane.recordPicker(checkedId='^.checked', storepath='.provinces', layout='list',
                          preview=True, preview_template=PREVIEW, boxHeight='300px', columns='nome,sigla,regione_nome',
                          template=CARD, selectedRecord='^.record', nodeId='rp_preview')

    def test_2_dialog(self, pane):
        """A clickable template opens the dialog; only confirmation changes the displayed record."""
        if not self.provinces(pane):
            return
        pane.recordPickerButton(record='^.chosen_record', placeholder='!!Select province',
                                template=CARD, action="genro.wdgById('rp_dialog').show();")
        dialog = pane.dialog(nodeId='rp_dialog', title='!!Choose province', closable=True,
                             _class='rp_example_dialog', width='640px',
                             connect_onShowing='SET .draft = GET .checked;')
        content = dialog.div(_class='rp_example_dialog_content')
        content.recordPicker(checkedId='^.draft', storepath='.provinces',
                             columns='nome,sigla,regione_nome', template=CARD,
                             layout='list', boxHeight='320px', selectedRecord='^.draft_record',
                             nodeId='rp_dialog_picker')
        actions = content.div(_class='rp_example_dialog_actions')
        actions.button('!!Cancel', action="genro.wdgById('rp_dialog').hide();")
        actions.button('!!Confirm', disabled='^.draft?=!#v',
                       action="""
                           SET .chosen_record = GET .draft_record;
                           SET .checked = GET .draft;
                           genro.wdgById('rp_dialog').hide();
                       """)

    def test_3_multicheck_resource(self, pane):
        """Resource template, up to three checks across searches; compact preview follows the last check."""
        if not self.provinces(pane):
            return
        pane.recordPicker(checkedId='^.checked', storepath='.provinces', multiSelect=True,
                          maxSelect=3, preview=True, cols=2, boxHeight='280px', columns='nome,sigla,regione_nome',
                          template_resource='recordpicker/province', selectedRecord='^.records',
                          selectedCaption='^.caption', nodeId='rp_multiple')

    def test_4_database(self, pane):
        """Live glbl.provincia search with bounded results and hydration of prechecked records."""
        if 'glbl' not in self.db.packages:
            pane.div('This example requires the glbl package.')
            return
        pane.data('.checked', 'MI,TO')
        pane.div('^.checked', lbl='Checked province codes', _class='rp_example_output')
        pane.recordPicker(checkedId='^.checked', table='glbl.provincia', columns='$nome,$sigla',
                          hiddenColumns=COLUMNS, multiSelect=True, limit=8, cols=4, boxHeight='240px',
                          template=CARD, nodeId='rp_database')

    def test_5_condition(self, pane):
        """Reactive database condition; changing the region refreshes the current search."""
        if 'glbl' not in self.db.packages:
            pane.div('This example requires the glbl package.')
            return
        pane.data('.region', 'LOM')
        pane.formbuilder().dbSelect(value='^.region', dbtable='glbl.regione', lbl='Region')
        pane.div('^.checked', lbl='Checked province codes', _class='rp_example_output')
        pane.recordPicker(checkedId='^.checked', table='glbl.provincia', columns='$nome,$sigla',
                          hiddenColumns=COLUMNS, condition='$regione=:region', condition_region='^.region',
                          template=CARD, nodeId='rp_condition')

    def test_6_empty_disabled(self, pane):
        """Empty store and reactive disabled state."""
        pane.data('.empty', Bag())
        pane.checkbox(value='^.disabled', label='Disabled')
        pane.recordPicker(checkedId='^.checked', storepath='.empty',
                          disabled='^.disabled', nodeId='rp_empty')

    def test_7_optional_radio(self, pane):
        """Optional radio and selected summary; external checkedId updates."""
        if not self.provinces(pane):
            return
        pane.button('Select Roma', action="SET .checked = 'RM';")
        pane.button('Clear selection', action='SET .checked = null;')
        pane.recordPicker(checkedId='^.checked', storepath='.provinces', showRadio=True, showSelected=True, cols=3, boxHeight='240px',
                          columns='nome,sigla,regione_nome', template=CARD, nodeId='rp_radio')
