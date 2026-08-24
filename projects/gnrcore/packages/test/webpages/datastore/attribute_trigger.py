# -*- coding: utf-8 -*-

"""Triggers of a set carrying attributes"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:FrameGrid"

    def test_0_grid_selected_id(self, pane):
        """Grid selectedId. Click a row: both counters step. Click the same row again: nothing
        moves. 'Republish selection' writes the same id with the same row data and must move
        nothing. 'Rename selected row' changes the row data, so the id stays and only the
        attributes counter steps"""
        box = pane.div(datapath='.t0')
        box.data('.store', self.gridStore())
        box.data('.id_triggers', 0)
        box.data('.attr_triggers', 0)
        box.bagGrid(frameCode='t0_grid', storepath='.store', struct=self.gridStruct,
                    grid_nodeId='t0_selgrid', height='180px',
                    addrow=False, delrow=False, batchAssign=False)
        fb = box.formbuilder(cols=2, border_spacing='3px')
        fb.div('^.id_triggers', lbl='selectedId triggers')
        fb.div('^.attr_triggers', lbl='selectedId?name triggers')
        fb.div('^.grid.selectedId', lbl='selectedId')
        fb.div('^.grid.selectedId?name', lbl='name from attributes')
        box.dataController("SET .id_triggers = n+1;",
                           selectedId='^.grid.selectedId', n='=.id_triggers')
        box.dataController("SET .attr_triggers = n+1;",
                           rowname='^.grid.selectedId?name', n='=.attr_triggers')
        bar = box.div(margin='5px')
        bar.button('Republish selection').dataController(
            "genro.nodeById('t0_selgrid').publish('updatedSelectedRow');")
        bar.button('Rename selected row').dataController("""
            if(!selectedId){
                return;
            }
            genro.setData(this.absDatapath('.store.'+selectedId+'.name'),
                          'renamed_'+genro.getCounter());
            genro.nodeById('t0_selgrid').publish('updatedSelectedRow');""",
            selectedId='=.grid.selectedId')

    def test_1_setdata_with_attributes(self, pane):
        """genro.setData carrying attributes. Same value and same attributes: no trigger at all.
        Same value with a changed attribute: only the attribute listener steps. Changed value:
        both step"""
        box = pane.div(datapath='.t1')
        box.data('.value_triggers', 0)
        box.data('.attr_triggers', 0)
        fb = box.formbuilder(cols=2, border_spacing='3px')
        fb.div('^.value_triggers', lbl='value triggers')
        fb.div('^.attr_triggers', lbl='attribute triggers')
        fb.div('^.target', lbl='value')
        fb.div('^.target?tag', lbl='tag attribute')
        box.dataController("SET .value_triggers = n+1;", target='^.target', n='=.value_triggers')
        box.dataController("SET .attr_triggers = n+1;",
                           target_tag='^.target?tag', n='=.attr_triggers')
        bar = box.div(margin='5px')
        bar.button('Same value, same tag').dataController(
            "genro.setData(this.absDatapath('.target'),'A',{tag:'first'});")
        bar.button('Same value, new tag').dataController(
            "genro.setData(this.absDatapath('.target'),'A',{tag:'tag_'+genro.getCounter()});")
        bar.button('New value').dataController(
            "genro.setData(this.absDatapath('.target'),'B_'+genro.getCounter(),{tag:'first'});")

    def gridStruct(self, struct):
        r = struct.view().rows()
        r.cell('name', name='Name', width='12em', edit=True)
        r.cell('city', name='City', width='12em', edit=True)

    def gridStore(self):
        result = Bag()
        for i, (name, city) in enumerate([('Anna', 'Milano'), ('Bruno', 'Roma'), ('Carla', 'Napoli')]):
            row = Bag()
            row['name'] = name
            row['city'] = city
            result.setItem('r_%i' % i, row)
        return result
