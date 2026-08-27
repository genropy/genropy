# -*- coding: utf-8 -*-

"""Triggers of a set carrying attributes"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:FrameGrid"

    def test_0_grid_selected_id(self, pane):
        """Grid selectedId. Click a row: both counters step. Click the same row again: nothing
        moves. 'Republish selection' writes the same id with the same row data and must move
        nothing. 'Rename selected row' changes the row data, so the id stays, only the attributes
        counter steps and 'changedAttr' must read name: the consumers that branch on that field
        (the form changes logger, a _class bound to an attribute) are blind without it"""
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
        fb.div('^.changed_attr', lbl='changedAttr of the last trigger')
        box.dataController("SET .id_triggers = n+1;",
                           selectedId='^.grid.selectedId', n='=.id_triggers')
        box.dataController("SET .attr_triggers = n+1; SET .changed_attr = _triggerpars.kw.changedAttr;",
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
        both step. The last button writes an attribute by path and carries a second one: both
        have to land, the '?attr' road obeys the same rule as the value one"""
        box = pane.div(datapath='.t1')
        box.data('.value_triggers', 0)
        box.data('.attr_triggers', 0)
        fb = box.formbuilder(cols=2, border_spacing='3px')
        fb.div('^.value_triggers', lbl='value triggers')
        fb.div('^.attr_triggers', lbl='attribute triggers')
        fb.div('^.target', lbl='value')
        fb.div('^.target?tag', lbl='tag attribute')
        fb.div('^.target?other', lbl='other attribute')
        fb.div('^.changed_attrs', lbl='changedAttrs list')
        box.dataController("SET .value_triggers = n+1;", target='^.target', n='=.value_triggers')
        box.dataController("""SET .attr_triggers = n+1;
                              SET .changed_attrs = triggerChangedAttrs(_triggerpars.kw).join(',');""",
                           target_tag='^.target?tag', n='=.attr_triggers')
        bar = box.div(margin='5px')
        bar.button('Same value, same tag').dataController(
            "genro.setData(this.absDatapath('.target'),'A',{tag:'first'});")
        bar.button('Same value, new tag').dataController(
            "genro.setData(this.absDatapath('.target'),'A',{tag:'tag_'+genro.getCounter()});")
        bar.button('New value').dataController(
            "genro.setData(this.absDatapath('.target'),'B_'+genro.getCounter(),{tag:'first'});")
        bar.button('Tag by path, carrying another attribute').dataController(
            """genro.setData(this.absDatapath('.target?tag'), 'bypath_'+genro.getCounter(),
                          {other:'other_'+genro.getCounter()});""")

    def test_2_more_than_one_attribute(self, pane):
        """Two attributes changed by a single set. Every consumer that branches on the changed
        name must still react: 'changedAttr' stays empty because no single attribute can be
        named, so the list is the only road. The _class bound to '?style' must drop its previous
        class even when 'tag' travels with it, and the last button deletes 'tag' while writing
        'style': a removed attribute is a change of its own path"""
        box = pane.div(datapath='.t2')
        box.data('.target', 'A', tag='first', style='testclass_a')
        box.data('.attr_triggers', 0)
        fb = box.formbuilder(cols=2, border_spacing='3px')
        fb.div('^.attr_triggers', lbl='tag attribute triggers')
        fb.div('^.target?tag', lbl='tag attribute')
        fb.div('^.target?style', lbl='style attribute')
        fb.div('^.changed_attr', lbl='changedAttr (empty when more than one)')
        fb.div('^.changed_attrs', lbl='changedAttrs list')
        fb.div('Bound to ?style', _class='^.target?style', lbl='node with _class on an attribute')
        box.dataController("""SET .attr_triggers = n+1;
                              SET .changed_attr = _triggerpars.kw.changedAttr;
                              SET .changed_attrs = triggerChangedAttrs(_triggerpars.kw).join(',');""",
                           target_tag='^.target?tag', n='=.attr_triggers')
        bar = box.div(margin='5px')
        bar.button('Change tag and style together').dataController(
            """var c = genro.getCounter();
               genro.getDataNode(this.absDatapath('.target')).updAttributes(
                   {tag:'tag_'+c, style:'testclass_'+c}, true);""")
        bar.button('Change style only').dataController(
            """genro.setData(this.absDatapath('.target?style'), 'testclass_'+genro.getCounter());""")
        bar.button('Drop tag, write style').dataController(
            """genro.setData(this.absDatapath('.target'), 'A',
                          {tag:null, style:'testclass_'+genro.getCounter()});""")

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
