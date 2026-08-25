# -*- coding: utf-8 -*-

"""Heavy page for client-side build profiling.

Intentionally oversized: thousands of source nodes, dojo widgets, dynamic
datapath bindings and bag grids on a single page, to make the client build
phase slow enough to profile. Ugly by design.
"""

from gnr.core.gnrbag import Bag

TABS = 8
FIELDS_PER_TAB = 120
GRID_ROWS = 200
GRID_COLS = 20
PLAIN_DIVS = 3000


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    js_requires = 'heavy_profiler'
    maintable = 'glbl.provincia'

    def windowTitle(self):
        return 'Heavy build profiling page'

    def onIniting(self, request_args, request_kwargs):
        # allows the JS Self-Profiling API (new Profiler(...)) on this page.
        # self.response only exists on the WSGI path: the websocket
        # registration (gnrasync.registerPage) instantiates the page without
        # a response, and the header is meaningless there anyway.
        response = getattr(self, 'response', None)
        if response is not None:
            response.add_header('Document-Policy', 'js-profiling')

    def gridData(self, rows=GRID_ROWS, cols=GRID_COLS):
        result = Bag()
        for r in range(rows):
            row = Bag()
            for c in range(cols):
                if c % 4 == 0:
                    row['col_%i' % c] = 'cell %i/%i' % (r, c)
                elif c % 4 == 1:
                    row['col_%i' % c] = r * c
                elif c % 4 == 2:
                    row['col_%i' % c] = round(r * c / 7.0, 2)
                else:
                    row['col_%i' % c] = 'txt_%i' % (r % 13)
            result.setItem('r_%i' % r, row)
        return result

    def gridStruct(self, struct):
        r = struct.view().rows()
        for c in range(GRID_COLS):
            if c % 4 == 1:
                r.cell('col_%i' % c, width='6em', dtype='L', name='Col %i' % c)
            elif c % 4 == 2:
                r.cell('col_%i' % c, width='7em', dtype='N', name='Col %i' % c,
                       format='#,###.00')
            else:
                r.cell('col_%i' % c, width='8em', name='Col %i' % c)

    def test_0_massive(self, pane):
        """Tabs full of form fields with dynamic bindings plus a bag grid per tab."""
        root = pane.div(nodeId='heavyRoot', datapath='heavy')
        root.data('.grid_data', self.gridData())
        tc = root.tabContainer(height='600px', margin='5px')
        for t in range(TABS):
            tab = tc.borderContainer(title='Tab %i' % t, datapath='.tab_%i' % t)
            top = tab.contentPane(region='top', height='50%', overflow='auto')
            fb = top.formbuilder(cols=6, border_spacing='2px')
            for f in range(FIELDS_PER_TAB):
                mod = f % 5
                if mod == 0:
                    fb.textbox(value='^.fld_%i' % f, lbl='Field %i' % f,
                               validate_notnull=True, validate_len='0:30')
                elif mod == 1:
                    fb.numberTextBox(value='^.num_%i' % f, lbl='Num %i' % f,
                                     format='#,###.00')
                elif mod == 2:
                    fb.dateTextBox(value='^.date_%i' % f, lbl='Date %i' % f)
                elif mod == 3:
                    fb.checkbox(value='^.chk_%i' % f, label='Check %i' % f)
                else:
                    fb.filteringSelect(value='^.sel_%i' % f, lbl='Select %i' % f,
                                       values='a:Alpha,b:Beta,c:Gamma,d:Delta')
            center = tab.contentPane(region='center', overflow='auto')
            center.bagGrid(frameCode='heavy_%i' % t, datapath='.grid',
                           struct=self.gridStruct, storepath='heavy.grid_data',
                           height='100%')

    def test_1_plain_divs(self, pane):
        """Thousands of plain divs with dynamic class/style bindings."""
        root = pane.div(nodeId='divsRoot', datapath='divs', overflow='auto',
                        height='300px')
        root.data('.status', 'odd')
        for i in range(PLAIN_DIVS):
            root.div('div nr %i' % i, _class='^.status', font_size='11px',
                     display='inline-block', padding='1px', margin='1px',
                     border='1px solid silver')

    def test_2_tablehandler(self, pane):
        """A couple of plain tablehandlers."""
        bc = pane.borderContainer(height='500px')
        bc.contentPane(region='left', width='50%').plainTableHandler(
            table='glbl.provincia', view_store_onStart=True)
        bc.contentPane(region='center').plainTableHandler(
            table='glbl.regione', view_store_onStart=True)

    def test_3_data_storm(self, pane):
        """Buttons to stress data triggers and rebuilds after page load.

        The rebuild targets the bound-divs subtree: node.rebuild() re-expands
        the already-expanded source, and component nodes (formbuilder,
        bagGrid/framepane) do not survive that — _beforeCreation moves their
        attributes into _saved_attributes on first expansion and nothing
        restores them, so a second expansion finds them empty. Pre-existing
        behavior, unrelated to this branch's changes.
        """
        box = pane.div(datapath='storm')
        fb = box.formbuilder(cols=3)
        fb.button('Data storm (600 set)', fire='.run_storm')
        fb.button('Rebuild bound divs', fire='.run_rebuild')
        fb.div('^.report', lbl='Last run')
        box.dataController("""
            var t0 = performance.now();
            for (var t=0; t<6; t++){
                for (var f=0; f<100; f++){
                    genro.setData('heavy.tab_'+t+'.fld_'+(f*5), 'storm '+f);
                }
            }
            SET .report = 'storm: '+(performance.now()-t0).toFixed(1)+' ms';
        """, _fired='^.run_storm')
        box.dataController("""
            var t0 = performance.now();
            genro.nodeById('divsRoot').rebuild();
            SET .report = 'rebuild: '+(performance.now()-t0).toFixed(1)+' ms';
        """, _fired='^.run_rebuild')
