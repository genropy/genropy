# -*- coding: utf-8 -*-

"""A grid shown as a tree by the path in its first column

The first column of the struct may carry hierarchical='<separator>': its value is
read as a path, the separator splits the levels, the cell shows the last segment
and the rows nest by path. An ancestor that is not among the rows shows as a
virtual row. Everything else is the ordinary grid: virtual rendering, sort,
column resize, selection.
"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:FrameGrid"

    def test_1_paths(self, pane):
        """Rows whose first column holds a '/' path. Atlantis has no row of its own: its
        cities bring it in as virtual ancestors. Click a header to sort every level"""
        bc = pane.borderContainer(height='500px', datapath='.t1')
        bc.data('.rows', self.geoRows())
        bc.contentPane(region='center').bagGrid(frameCode='t1_grid', storepath='.rows',
                    struct=self.geoStruct, datamode='attr', title="hierarchical='/'",
                    gridEditor=False, addrow=False, delrow=False, batchAssign=False)

    def test_2_dotted_codes(self, pane):
        """A chart of accounts nested by its dotted codes, hierarchical='.'. Accounts 3 and
        3.1 have no row: they show as virtual ancestors of 3.1.01"""
        bc = pane.borderContainer(height='350px', datapath='.t2')
        bc.data('.rows', self.accountRows())
        bc.contentPane(region='center').bagGrid(frameCode='t2_grid', storepath='.rows',
                    struct=self.accountStruct, datamode='attr', title="hierarchical='.'",
                    gridEditor=False, addrow=False, delrow=False, batchAssign=False)

    def test_3_changes(self, pane):
        """Changes made to the rows reach the grid: add a row under the selected one,
        change its population (not the path), delete it"""
        bc = pane.borderContainer(height='400px', datapath='.t3')
        bc.data('.rows', self.geoRows(continents=2, countries=3, cities=3, atlantis=False))
        bar = bc.contentPane(region='top').div(margin='5px')
        bar.button('Add child').dataController("""
            var node = selected && rows.getNode(selected);
            if(!node){
                return;
            }
            var pkey = 'new_'+genro.getCounter();
            rows.setItem(pkey,null,{_pkey:pkey,description:node.attr.description+'/New '+pkey,population:1,area:1});
            """, rows='=.rows', selected='=.grid.selectedId')
        bar.button('Population +1000').dataController("""
            var node = selected && rows.getNode(selected);
            if(node){
                node.updAttributes({population:node.attr.population+1000});
            }
            """, rows='=.rows', selected='=.grid.selectedId')
        bar.button('Delete').dataController("""
            var node = selected && rows.getNode(selected);
            if(node){
                rows.popNode(node.label);
            }
            """, rows='=.rows', selected='=.grid.selectedId')
        bar.span('^.grid.selectedId', margin_left='10px')
        bc.contentPane(region='center').bagGrid(frameCode='t3_grid', storepath='.rows',
                    struct=self.geoStruct, datamode='attr', title='Changes',
                    gridEditor=False, addrow=False, delrow=False, batchAssign=False)

    def geoStruct(self, struct):
        r = struct.view().rows()
        r.cell('description', name='Name', width='20em', hierarchical='/')
        r.cell('population', name='Population', width='8em', dtype='L')
        r.cell('area', name='Area', width='7em', dtype='N', format='#,###.0')

    def accountStruct(self, struct):
        r = struct.view().rows()
        r.cell('code', name='Code', width='10em', hierarchical='.')
        r.cell('description', name='Description', width='20em')

    def geoRows(self, continents=5, countries=8, cities=25, atlantis=True):
        result = Bag()

        def add(pkey, path, population, area):
            result.setItem(pkey, None, _pkey=pkey, description=path, population=population, area=area)

        for c in range(continents):
            continent = 'Continent %i' % c
            add('c%i' % c, continent, 0, 0)
            for k in range(countries):
                country = '%s/Country %i.%i' % (continent, c, k)
                add('c%ik%i' % (c, k), country, 0, 0)
                for t in range(cities):
                    add('c%ik%it%i' % (c, k, t), '%s/City %i.%i.%i' % (country, c, k, t),
                        1000 * (t + 1) + 37 * k + c, 1.5 * (t + 1) + k)
        if atlantis:
            for t in range(3):
                add('atlantis%i' % t, 'Atlantis/Lost Country/City %i' % t, 100 * (t + 1), t + 1)
        return result

    def accountRows(self):
        result = Bag()
        for code, description in (('1', 'Assets'), ('1.1', 'Current assets'), ('1.1.01', 'Cash'),
                                  ('1.1.02', 'Bank'), ('1.2', 'Fixed assets'), ('1.2.01', 'Buildings'),
                                  ('2', 'Liabilities'), ('2.1', 'Payables'), ('2.1.01', 'Suppliers'),
                                  ('3.1.01', 'Sales revenues')):
            result.setItem(code.replace('.', '_'), None, _pkey=code, code=code, description=description)
        return result
