# -*- coding: utf-8 -*-

# dd_tree.py
# Created by Francesco Porcari on 2010-10-01.
# Copyright (c) 2010 Softwell. All rights reserved.

"""Tree with drag & drop"""
from __future__ import print_function

from builtins import object
from gnr.core.gnrbag import Bag, DirectoryResolver

print('Tree with drag & drop')
class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull"""

    def test_1_simple(self, pane):
        """Simple Drag in hierarchical tree structure"""
        pane.css('.foo', 'color:pink;')
        pane.css('.bar', 'background-color:yellow;')
        root = pane.div(height='200px', overflow='auto')
        root.data('.tree.data', self.treedata())
        root.tree(storepath='.tree.data', dropTarget=True,
                  draggable=True,
                  onDrag="""function(dragValues){console.log(dragValues)}""",
                  dragClass='draggedItem',
                  onDrop_text_plain='alert(data)',
                  onDrop_treenode='alert(data.fullpath)')
    
    def treedata(self):
        b = Bag()
        b.setItem('person', None, node_class='foo')
        b.setItem('person.name', 'John', job='superhero', node_class='bar')
        b.setItem('person.age', 22)
        b.setItem('person.sport.tennis', 'good')
        b.setItem('person.sport.football', 'poor')
        b.setItem('person.sport.golf', 'medium')
        b.setItem('pet.animal', 'Dog', race='Doberman')
        return b

    def test_2_disk(self, pane):
        """Disk Directory Drag (Please update code with your custom path value)"""
        root = pane.div(height='200px', overflow='auto')
        root.data('.disk', Bag(dict(root=DirectoryResolver('/Users/')))) #Please update code with your custom value
        root.tree(storepath='.disk', hideValues=True, inspect='shift', draggable=True, dragClass='draggedItem')

    def test_3_data(self, pane):
        """Data Drag (as available in Inspector > Data)"""
        root = pane.div(height='200px', overflow='auto')
        root.tree(storepath='*D', hideValues=True, inspect='shift', draggable=True, dragClass='draggedItem')

    def test_4_source(self, pane):
        """Source Drag (as available in Inspector > Source)"""
        root = pane.div(height='200px', overflow='auto')
        root.tree(storepath='*S', hideValues=True, inspect='shift', draggable=True, dragClass='draggedItem')

    
