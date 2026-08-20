# -*- coding: utf-8 -*-

"""htablePicker: pick rows of a hierarchical table from a dialog

The HTablePicker component opens a palette showing a hierarchical table as a
tree plus a grid, and writes the selection back into the caller's datapath.
It comes in two flavours: htablePicker, which exchanges the codes of the
hierarchical table itself, and htablePickerOnRelated, which exchanges the
primary keys of a table related to it.
"""


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/htablehandler:HTablePicker'
    htable = 'base.category'
    related_table = 'base.ct_catalog'
    relation_path = '@category_id.code'

    def test_1_testpicker(self, pane):
        """Picker on the hierarchical table: exchange codes

        The textbox holds the current codes and feeds the picker through
        input_codes; what the user selects comes back on output_codes, so the
        same textbox is both the source and the destination of the round trip.
        """
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.codes', lbl='Codes', width='30em')
        fb.button('Show', action='PUBLISH picker_1_open;')
        self.htablePicker(pane, table=self.htable,
                          nodeId='picker_1', datapath='.struct_picker',
                          input_codes='=.#parent.codes',
                          output_codes='.#parent.codes')

    def test_2_testpicker(self, pane):
        """Picker on a related table: exchange primary keys

        htablePickerOnRelated picks rows of related_table through the relation
        named by relation_path, so the picker still shows the hierarchy while
        the values exchanged are the related table's pkeys. Input and output
        paths are distinct here, and the grid columns and the row condition are
        supplied by the caller.
        """
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.pkeys', lbl='Related Pkeys', width='30em')
        fb.div(value='^.output_pkeys', lbl='Related Output Pkeys', width='30em', height='20px', background='red')
        fb.button('Show', action='PUBLISH picker_2_open;')

        def struct(struct):
            r = struct.view().rows()
            r.fieldcell('code', name='Code', width='12em')
            r.fieldcell('description', name='Description', width='20em')
            r.fieldcell('rec_type', name='Type', width='4em')

        self.htablePickerOnRelated(pane, table=self.htable,
                                   related_table=self.related_table,
                                   input_pkeys='=.#parent.pkeys',
                                   output_pkeys='.#parent.output_pkeys',
                                   relation_path=self.relation_path,
                                   grid_struct=struct,
                                   condition='$rec_type IN :rec_types',
                                   condition_pars=dict(rec_types=['I', 'P', 'L']),
                                   nodeId='picker_2', datapath='.struct_picker')
