# -*- coding: utf-8 -*-

"""Grid column filter: filterField on the cell

A cell with filterField gets a filter icon in its header. The icon opens the
list of the values the column holds, each with its count; checking values
filters the grid. filterField=True filters on the cell's own field, a field
name filters on that related field and shows the cell's text. Clicking the
column title still sorts. The filter runs in the browser, so a grid on a
virtual store ignores filterField and shows no icon.

filterFieldDefault on the grid (grid_filterFieldDefault in the th options)
turns filterField on for every cell that shows a plain field, columns added
from the configurator included; template, calculated, values and button cells
are left out, and filterField=False opts a cell out.

For lists, set filterField=True and filterField_aggr=',' on the cell (or use
another separator). Choices and counts refer to individual values; selecting
several values keeps rows containing any of them.

On a date column the popup also takes a period (From / To), bounds included:
a period and checked values exclude each other. The arrow next to the title
turns the order of the values from ascending to descending.
"""

import datetime

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_0_static(self, pane):
        """Static store on glbl.provincia: values, counts and filters in the browser"""
        bc = pane.borderContainer(height='450px')
        bc.contentPane(region='center').plainTableHandler(table='glbl.provincia', datapath='.provincia',
                                                          viewResource='ViewColumnFilter',
                                                          view_store_onStart=True)

    def test_1_virtual(self, pane):
        """Virtual store on glbl.comune: filterField is ignored, no filter icon"""
        bc = pane.borderContainer(height='450px')
        bc.contentPane(region='center').plainTableHandler(table='glbl.comune', datapath='.comune',
                                                          viewResource='ViewColumnFilter',
                                                          virtualStore=True,
                                                          view_store_onStart=True)

    def test_2_default(self, pane):
        """Static store with grid_filterFieldDefault: every plain column gets the filter"""
        bc = pane.borderContainer(height='450px')
        bc.contentPane(region='center').plainTableHandler(table='glbl.provincia', datapath='.provincia_default',
                                                          grid_filterFieldDefault=True,
                                                          view_store_onStart=True)

    def test_3_dates(self, pane):
        """Static rows with a date column: From / To keep the rows of the period, the arrow reverses the list"""
        rows = Bag()
        start = datetime.date(2026, 1, 1)
        for i in range(40):
            rows.addItem(f'r_{i}', None, invoice=f'INV-{i:03}', customer=['Rossi', 'Verdi', 'Bianchi'][i % 3],
                         issued=start + datetime.timedelta(days=i * 9))
        pane.data('.invoices', rows)
        grid = pane.div(height='400px', position='relative').quickGrid(value='^.invoices')
        grid.column('invoice', name='Invoice', width='8em', filterField=True)
        grid.column('customer', name='Customer', width='10em', filterField=True)
        grid.column('issued', name='Issued', width='10em', dtype='D', filterField=True)

    def test_4_invoice_tags(self, pane):
        """Invoice tags: filter Supplier to AKOAN, select Tag SenzaTitoloProgetto: INV-001 stays visible."""
        pane.div('In the Tag filter, SenzaTitoloProgetto must have count 1 '
                 'with Supplier filtered to AKOAN S.A.S. Select it to keep INV-001; also select fattura ok '
                 'to show both invoices. Clear the Tag filter to restore the two supplier invoices.',
                 margin_bottom='10px')
        rows = Bag()
        invoices = [
            ('INV-001', 'AKOAN S.A.S.', 'B14 Restaurants,B14 Verificato,SenzaTitoloProgetto', 54.55),
            ('INV-002', 'AKOAN S.A.S.', 'fattura ok', 301.82),
            ('INV-003', 'Other supplier', 'SenzaTitoloProgetto', 120),
            ('INV-004', 'Other supplier', 'SenzaTitoloProgetto Extra', 80),
            ('INV-005', 'Other supplier', None, 25),
            ('INV-006', 'Other supplier', ' B14 Verificato, B14 Verificato, ,fattura ok ', 60)
        ]
        for i, (invoice, supplier, tags, amount) in enumerate(invoices):
            rows.addItem(f'r_{i}', None, invoice=invoice, supplier=supplier, tags=tags, amount=amount)
        pane.data('.invoices', rows)
        grid = pane.div(height='350px', position='relative').quickGrid(value='^.invoices')
        grid.column('invoice', name='Invoice', width='8em', filterField=True)
        grid.column('supplier', name='Supplier', width='14em', filterField=True)
        grid.column('tags', name='Tag', width='38em', filterField=True, filterField_aggr=',')
        grid.column('amount', name='Amount', width='8em', dtype='N', format='#,##0.00')
