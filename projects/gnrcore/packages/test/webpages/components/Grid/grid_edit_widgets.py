# -*- coding: utf-8 -*-

"""Test page for all editable widget types in grid cells.
Used to verify widgetInCell CSS styling works for every widget type."""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:frameGrid"

    def test_0_all_widgets(self, pane):
        """Grid with all editable widget types: TextBox, NumberTextBox, DateTextBox, CheckBox, FilteringSelect, SimpleTextarea"""
        pane.data('.store', self._sample_data())
        frame = pane.bagGrid(
            frameCode='allwidgets',
            title='All widget types in grid',
            struct=self._all_widgets_struct,
            storepath='.store',
            datapath='.grid_test',
            height='400px',
            addrow=True,
            delrow=True
        )

    def _all_widgets_struct(self, struct):
        r = struct.view().rows()
        r.cell('text_field', width='12em', name='Text',
               edit=True)
        r.cell('number_field', width='7em', name='Number',
               dtype='N', edit=True)
        r.cell('integer_field', width='5em', name='Integer',
               dtype='L', edit=True)
        r.cell('date_field', width='8em', name='Date',
               dtype='D', edit=True)
        r.cell('bool_field', width='4em', name='Bool',
               dtype='B', edit=True)
        r.cell('select_field', width='10em', name='Select',
               edit=dict(tag='FilteringSelect',
                         values='A:Alpha,B:Beta,C:Gamma,D:Delta'))
        r.cell('textarea_field', width='15em', name='TextArea',
               edit=dict(tag='SimpleTextarea'))
        r.cell('description', width='20em', name='Description',
               edit=True, style='white-space:pre-line')

    def _sample_data(self):
        data = Bag()
        data.setItem('r_0', Bag(dict(
            text_field='Sample text',
            number_field=42.5,
            integer_field=100,
            date_field=None,
            bool_field=True,
            select_field='A',
            textarea_field='Line 1\nLine 2\nLine 3',
            description='Short desc'
        )))
        data.setItem('r_1', Bag(dict(
            text_field='Another item',
            number_field=99.99,
            integer_field=200,
            date_field=None,
            bool_field=False,
            select_field='B',
            textarea_field='Single line',
            description='A longer description to test overflow in narrow columns'
        )))
        data.setItem('r_2', Bag(dict(
            text_field='',
            number_field=0,
            integer_field=0,
            date_field=None,
            bool_field=False,
            select_field='',
            textarea_field='',
            description=''
        )))
        return data

    def test_1_narrow_columns(self, pane):
        """Same widgets but in very narrow columns to test overflow/clipping"""
        pane.data('.store_narrow', self._sample_data())
        frame = pane.bagGrid(
            frameCode='narrow',
            title='Narrow columns stress test',
            struct=self._narrow_struct,
            storepath='.store_narrow',
            datapath='.grid_narrow',
            height='300px',
            addrow='auto'
        )

    def _narrow_struct(self, struct):
        r = struct.view().rows()
        r.cell('text_field', width='5em', name='Text',
               edit=True)
        r.cell('date_field', width='6em', name='Date',
               dtype='D', edit=True)
        r.cell('select_field', width='6em', name='Select',
               edit=dict(tag='FilteringSelect',
                         values='A:Alpha,B:Beta,C:Gamma'))
        r.cell('bool_field', width='3em', name='Ok',
               dtype='B', edit=True)
        r.cell('number_field', width='4em', name='Num',
               dtype='N', edit=True)

    def test_2_single_column(self, pane):
        """Single editable column: row must not disappear on double-click (#805)"""
        pane.data('.store_single', self._sample_data())
        frame = pane.bagGrid(
            frameCode='single',
            title='Single column (row height regression test)',
            struct=self._single_column_struct,
            storepath='.store_single',
            datapath='.grid_single',
            height='300px',
            addrow=True
        )

    def _single_column_struct(self, struct):
        r = struct.view().rows()
        r.cell('text_field', width='20em', name='Text',
               edit=True)

    def test_3_mixed_width(self, pane):
        """Two columns, one without explicit width: row must not shrink on edit (#805)"""
        pane.data('.store_mixed', self._sample_data())
        frame = pane.bagGrid(
            frameCode='mixed',
            title='Mixed width columns (row height regression test)',
            struct=self._mixed_width_struct,
            storepath='.store_mixed',
            datapath='.grid_mixed',
            height='300px',
            addrow=True
        )

    def _mixed_width_struct(self, struct):
        r = struct.view().rows()
        r.cell('text_field', width='20em', name='Text',
               edit=True)
        r.cell('number_field', name='Number',
               dtype='N', edit=True)
