# -*- coding: utf-8 -*-

"""Drag and drop: drag values and tags, and detachable panes

Any widget becomes a drag source with `draggable=True`; `dragTags` (which
implies `draggable`) labels what is dragged. A widget with a data value drags
that value; `drag_value=` overrides it with a path (`=ccc.nnn.kkk`,
`=hhh.kkk?.yyy`) or an observer (`^mydata`), and `drag_cb=` computes it in a
callback that receives the `sourceNode`. HTML5 drag and drop is used, so
values can also be dragged to another application, and files can be dragged in.
A drop target filters with `dropTypes` (`text/plain`, `xml`, `Files`, ...) and
`dropTags`, where a comma is an OR and AND is explicit (`client AND good,payer`);
`onDrop` runs a script and `drop_ext` restricts file extensions.

    DRAG                        DROP
    draggable=True              dropTags = 'foo AND Bar'
    dragTags='foo AND Bar'      dropTypes = 'text/plain', 'xml', 'Files'
                                onDrop = "js"
                                drop_ext = 'gif' or 'py' or 'bar' , etc

`test_0_simple` shows drag sources with toggled and fixed `draggable` and
with tags; `test_1_detachable_tab` shows `detachable` panes dragged out of a
tabContainer into a floating window.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull"""
                      
    def test_0_simple(self, pane):
        """Try checking "draggable" option and dragging fields. Other fields will always be draggable."""
        fb = pane.formbuilder(cols=2, dragClass='draggedItem')
        fb.div('Drag Me', width='70px', height='30px', margin='3px',
               background_color='green', lbl='drag it', draggable='^.cb1')
        fb.checkbox(value='^.cb1', label='draggable')
        
        fb.data('.mydiv', 'aaaabbbbbccc')
        fb.textBox(value='^.name', lbl='my name', draggable='^.cb2')
        
        fb.checkbox(value='^.cb2', label='draggable')
        fb.textBox(value='^.name2', lbl='alwaysdraggable', draggable=True)
        fb.br()
        
        # dragValue="^.valueToDrag" can also be used, or onDrag="... sets the value to drag ..."
        #
        # See tablehandler_core.py and tablehandler_list.py for some examples
        #
        # onDrag can:
        # - return False, to abort the drag & drop;
        # - it receives dragValues, dragInfo, treeItem (the last one is meaningful only when dragging from a tree)
        # - dragValues is the envelope where other data can be added
        
        fb = pane.formbuilder(dragClass='draggedItem')
        fb.div('^.mydiv', lbl='my div', draggable=True)
        fb.div('drag foo', dragTags='foo', lbl='drag with foo', draggable=True)
        fb.div('drag bar', dragTags='bar', lbl='drag with bar', draggable=True)
        fb.div('drag foo,bar', dragTags='foo,bar', lbl='drag with foo,bar', draggable=True)

    def test_1_detachable_tab(self, pane):
        """Hold shift and drag a coloured pane out of its tab: a detachable pane moves into a floating window and leaves a placeholder in the tab"""
        tc = pane.tabContainer(height='300px', width='400px')
        one = tc.contentPane(title='One', overflow='hidden').contentPane(background_color='pink', detachable=True)
        one.div('one')
        two = tc.contentPane(title='Two').contentPane(background_color='yellow', detachable=True)
        two.div('two')
        three = tc.contentPane(title='Three').contentPane(background_color='lime', detachable=True)
        three.div('three')
