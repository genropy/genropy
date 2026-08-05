"""DB-backed groupletGrid demo (Item 14).

  test_1_region_provinces — `thFormHandler(table='glbl.regione',
                            formResource='RegionWithProvinces')` shows a
                            regione record. The form materialises
                            `province_principali_sigla` (CSV) into a
                            Bag of rows at load and serialises it back
                            at save. Each row is a `province_picker`
                            grouplet whose dbselect is filtered by the
                            currently edited regione.
                            Save is explicit (no autoSave — that's
                            Item 24).
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     th/th:TableHandler,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_1_region_provinces(self, pane):
        """Pick a regione, edit its 'province principali' via
        groupletGrid, save back to DB as a comma-separated string."""
        bc = pane.borderContainer(height='560px')
        toolbar = bc.contentPane(region='top', datapath='.toolbar',
                                 padding='8px', border_bottom='1px solid silver')
        toolbar.div('Pick a regione to edit. The grid below renders '
                    "`province_principali_sigla` as one row per province, "
                    'each row constrained to provinces of that regione. '
                    'Save persists the CSV back to the DB.',
                    color='#555', font_style='italic',
                    margin_bottom='6px')
        toolbar.dbSelect(value='^.regione_sigla',
                         dbtable='glbl.regione',
                         hasDownArrow=True,
                         width='20em',
                         lbl='!!Regione',
                         validate_onAccept="""
                             if (userChange) {
                                 genro.formById('region_provinces_form')
                                      .load({destPkey: value});
                             }
                         """)

        bc.contentPane(region='center').thFormHandler(
            table='glbl.regione',
            formResource='RegionWithProvinces',
            formId='region_provinces_form',
            datapath='.regione')
