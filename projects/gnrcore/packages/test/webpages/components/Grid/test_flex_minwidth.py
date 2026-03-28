# -*- coding: utf-8 -*-

"""Test page for flex column min-width enforcement in grids"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:frameGrid"

    def getSampleData(self):
        result = Bag()
        rows = [
            dict(code='PROD-001', description='High performance widget with extended warranty',
                 category='Electronics', quantity=150, unit_price=29.99,
                 supplier='Acme Corp International', notes='Best seller this quarter'),
            dict(code='PROD-002', description='Compact storage solution',
                 category='Hardware', quantity=75, unit_price=49.50,
                 supplier='GlobalTech', notes='New arrival'),
            dict(code='PROD-003', description='Professional development toolkit for enterprise use',
                 category='Software', quantity=200, unit_price=199.00,
                 supplier='DevTools Inc', notes='Volume discount available'),
            dict(code='PROD-004', description='Ergonomic desk accessory',
                 category='Furniture', quantity=30, unit_price=89.90,
                 supplier='Office Solutions Ltd', notes='Limited stock'),
            dict(code='PROD-005', description='Network security appliance',
                 category='Networking', quantity=12, unit_price=599.00,
                 supplier='SecureNet Global Partners', notes='Requires installation'),
        ]
        for i, row in enumerate(rows):
            result.setItem('r_%i' % i, Bag(row))
        return result

    def test_0_mixed_fixed_flex(self, pane):
        """Mixed fixed and flex columns with fillDown and footer. Resize the splitter to squeeze flex columns
        and verify they stop shrinking at min-width. Test trackpad horizontal scroll over grid body."""
        bc = pane.borderContainer(height='500px')
        bc.contentPane(region='right', width='200px', splitter=True,
                       background='#f0f0f0').div('Drag the splitter left to squeeze the grid',
                                                  padding='10px')
        center = bc.contentPane(region='center')

        def struct(struct):
            r = struct.view().rows()
            r.cell('code', width='8em', name='Code')
            r.cell('description', width='auto', name='Description', edit=True)
            r.cell('category', width='auto', name='Category')
            r.cell('quantity', width='6em', dtype='L', name='Qty',
                    totalize=True)
            r.cell('unit_price', width='7em', dtype='N', name='Unit Price',
                    format='#,###.00', totalize=True)
            r.cell('supplier', width='auto', name='Supplier')
            r.cell('notes', width='auto', name='Notes')

        center.data('.sample_data', self.getSampleData())
        center.dataFormula('.grid.store','sample_data', sample_data='=.sample_data',_onStart=True)

        center.bagGrid(frameCode='mixed', datapath='.grid',
                               struct=struct, storepath='.store',
                               height='100%', fillDown=True)

    def test_1_flex_with_columnsets(self, pane):
        """Flex columns organized in columnsets. Resize to verify columnset headers
        and footer widths stay in sync when min-width enforcement kicks in."""
        bc = pane.borderContainer(height='500px')
        bc.contentPane(region='right', width='200px', splitter=True,
                       background='#f0f0f0').div('Drag the splitter left to squeeze the grid',
                                                  padding='10px')
        center = bc.contentPane(region='center')

        def struct(struct):
            r = struct.view().rows()
            r.cell('code', width='8em', name='Product Code')
            r.cell('description', width='auto', name='Description',
                    columnset='product')
            r.cell('category', width='auto', name='Category',
                    columnset='product')
            r.cell('quantity', width='6em', dtype='L', name='Quantity',
                    columnset='numbers')
            r.cell('unit_price', width='7em', dtype='N', name='Unit Price',
                    format='#,###.00', columnset='numbers')
            r.cell('supplier', width='auto', name='Supplier',
                    columnset='supply')
            r.cell('notes', width='auto', name='Notes',
                    columnset='supply')

        center.data('.sample_data', self.getSampleData())
        center.dataFormula('.grid_1.store_1', 'sample_data', sample_data='=.sample_data', _onStart=True)

        center.bagGrid(frameCode='colsets', datapath='.grid_1',
                               struct=struct, storepath='.store_1',
                               height='100%', fillDown=True,
                               grid_footer='Totals',
                               columnset_product='Product Info',
                               columnset_numbers='Quantities',
                               columnset_supply='Supply Chain')

    def test_2_explicit_min_width(self, pane):
        """Explicit min_width override on flex columns. The 'Description' column has min_width='15em'.
        Verify this overrides the auto-calculated value when resizing."""
        bc = pane.borderContainer(height='500px')
        bc.contentPane(region='right', width='200px', splitter=True,
                       background='#f0f0f0').div('Drag the splitter left to squeeze the grid',
                                                  padding='10px')
        center = bc.contentPane(region='center')

        def struct(struct):
            r = struct.view().rows()
            r.cell('code', width='8em', name='Code')
            r.cell('description', width='auto', name='Description',
                    min_width='15em')
            r.cell('category', width='auto', name='Category')
            r.cell('quantity', width='6em', dtype='L', name='Qty')
            r.cell('supplier', width='auto', name='Supplier')

        center.data('.sample_data', self.getSampleData())
        center.dataFormula('.grid_2.store_2', 'sample_data', sample_data='=.sample_data', _onStart=True)

        center.bagGrid(frameCode='minwidth', datapath='.grid_2',
                               struct=struct, storepath='.store_2',
                               height='100%', fillDown=True)
