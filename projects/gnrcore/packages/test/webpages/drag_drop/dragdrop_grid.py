# -*- coding: utf-8 -*-

"""Drag and drop with grids: drop targets, rows and columns dragged inside a grid, cells edited in place

Drop boxes accept text and grid rows, cells or columns according to their
`dropTypes` and `dropTags`; what lands on them is written into `.last_drop`.
The first grid is a `bagGrid` whose cells are edited in place; the others show
the `includedView` drag options: `selfDragRows` and
`selfDragColumns` (plain, `trashable`, or a callback deciding row by row)
make rows and columns draggable, plus draggable cells (`draggable=True` on a
struct cell).
"""

from gnr.core.gnrbag import Bag
import datetime


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:FrameGrid"""

    def test_0_drop(self, pane):
        """Drop a text, or a row, cell or column dragged from a grid below, onto the boxes: each box accepts only its tags"""
        fb = pane.formbuilder(cols=1)
        dropboxes = fb.div(onDrop="""var dropped = [];
                                   for (var k in data){
                                       dropped.push(k + ': ' + data[k]);
                                   }
                                   this.setRelativeData('.last_drop', dropped.join(', '));""",
                           onDrop_text_plain="this.setRelativeData('.last_drop', 'text_plain: ' + data);",
                           lbl='Drop boxes text/plain',
                           dropTypes='text/plain,gridrow/json,gridcell/json,gridcolumn/json')

        dropboxes.div('no tags', width='100px', height='50px', margin='3px', background_color='lightgray',
                      float='left', dropTarget=True)
        dropboxes.div('only foo', width='100px', height='50px', margin='3px', background_color='#fcfca9',
                      float='left', dropTags='foo', dropTarget=True)
        dropboxes.div('only bar', width='100px', height='50px', margin='3px', background_color='#ffc2f5',
                      float='left', dropTags='bar', dropTarget=True)
        dropboxes.div('only foo AND bar', width='100px', height='50px', margin='3px', background_color='#a7cffb',
                      float='left', dropTags='foo AND bar', dropTarget=True)
        fb.div('^.last_drop', lbl='Last drop')

    def test_1_grid(self, pane):
        """Cells edited in place on the new grid (bagGrid): FS, Name, Qty, New and Date have an editor, and Name refuses values shorter than 4 or longer than 7 characters; rows and columns can be dragged inside the grid"""
        frame = pane.bagGrid(frameCode='dragEditGrid', storepath='.data', datamode='bag',
                             struct=self.editgrid_struct, height='250px',
                             grid_selfDragRows=True, grid_selfDragColumns=True)
        frame.data('.data', self.aux_test_1_grid_data())

    def test_2_grid(self, pane):
        """Drag a row to move it: the moved rows and the target row are written into .last_move; a column dragged out of the grid is trashed"""
        pane = pane.div(height='250px')
        pane.data('.data', self.aux_test_1_grid_data())
        pane.IncludedView(storepath='.data', selfDragColumns='trashable', selfDragRows=True,
                                    struct=self.inputgrid_struct,
                                 afterSelfDropRows="this.setRelativeData('.last_move', rows + ' -> ' + dropInfo.row);",
                                 datamode='bag', editorEnabled=True)
        pane.div('^.last_move')

    def test_3_grid(self, pane):
        """selfDragRows as a callback: even rows can be dragged, and dropped only onto odd rows"""
        pane = pane.div(height='250px')
        pane.data('.data', self.aux_test_1_grid_data())
        pane.IncludedView(storepath='.data', selfDragColumns=True,
            struct=self.inputgrid_struct,
                                 selfDragRows="""var odd= info.row%2;if (info.drag){return odd?false: true}else{return odd?true: false;}"""
                                 ,
                                 datamode='bag', editorEnabled=True)

    def inputgrid_struct(self, struct):
        r = struct.view().rows()
        r.cell('idx', name='N.', width='3em', counter=True)
        r.cell('filter', name='FS', width='10em')
        r.cell('language', name='Lang', width='10em', dtype='T')
        r.cell('name', name='Name', width='10em', dtype='T', draggable=True)  # cells draggable
        r.cell('qt', name='Qty', width='10em', dtype='R')
        r.cell('new', name='New', width='10em', dtype='B')
        r.cell('size', name='Size', width='10em', dtype='T')
        r.cell('date', name='Date', width='10em', dtype='D')

    def editgrid_struct(self, struct):
        r = struct.view().rows()
        r.cell('idx', name='N.', width='3em', counter=True)
        r.cell('filter', name='FS', width='10em',
               edit=dict(tag='filteringSelect', values='A:Alberto,B:Bonifacio,C:Carlo'))
        r.cell('language', name='Lang', width='10em', dtype='T')
        r.cell('name', name='Name', width='10em', dtype='T',
               edit=dict(validate_len='4:7', validate_len_error='!!Name must be 4 to 7 characters'))
        r.cell('qt', name='Qty', width='10em', dtype='R', edit=True)
        r.cell('new', name='New', width='10em', dtype='B', edit=True)
        r.cell('size', name='Size', width='10em', dtype='T')
        r.cell('date', name='Date', width='10em', dtype='D', edit=True)

    def aux_test_1_grid_data(self):
        result = Bag()
        date = datetime.date.today()
        for i in range(100):
            pkey = 'r_%i' % i
            result[pkey] = Bag({'idx': i, '_pkey': pkey, 'filter': 'A', 'language': 'Python',
                                'name': 'Dsc %i' % i, 'qt': None,
                                'new': bool(i % 2), 'size': 'big', 'date': date + datetime.timedelta(i)})
        return result
