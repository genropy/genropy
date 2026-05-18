# -*- coding: utf-8 -*-
"""Perf probe — 50 realistic groupletGrid instances on one page.

Each instance is a real `invoice_row` resource grouplet over 5 seeded
rows, so the page exercises the same template-loading / row-cloning /
sibling-BagStore path that production pages walk through. The page
logs to the JS console how long it takes from page load until all 50
controllers have completed their `_onBuilt` initialization, so the
overhead of the always-on sibling BagStore can be measured directly
in Chrome / Safari / Firefox devtools.

Open the page, watch the console for:
    [perf_50] all 50 groupletGrids ready in NNN ms

Then open Memory tab → Take heap snapshot to record the steady-state
heap size for comparison against a control page.
"""
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):

    py_requires = ('gnrcomponents/testhandler:TestHandlerFull,'
                   'gnrcomponents/grouplet/grouplet:GroupletGridHandler')

    def _seed(self, n):
        catalogue = [('Apples', 10, 2.50), ('Bread', 2, 1.20),
                     ('Coffee', 1, 12.00), ('Donuts', 6, 1.50),
                     ('Eggs', 12, 0.30)]
        rows = Bag()
        for i in range(1, n + 1):
            prod, qty, price = catalogue[(i - 1) % len(catalogue)]
            rows.setItem(f'r_{i:03d}', Bag(dict(product=prod,
                                                qty=qty, price=price)))
        return rows

    def test_1_50_instances(self, pane):
        """50 invoice grids side by side."""
        n_instances = 50
        pane.div(f'Perf probe: {n_instances} realistic groupletGrid '
                 f'instances. Open the console for the all-ready time.',
                 color='#666', font_style='italic', margin_bottom='8px')
        # Counter wired through dataController: each instance's _onBuilt
        # ticks the counter; when it reaches n_instances we log the
        # elapsed time. `t0` is sampled at page-script time (close enough
        # to navigation-start for this probe).
        pane.dataController("""
            window.__perf50 = {t0: performance.now(), n: 0,
                               target: target};
        """, _onStart=True, target=n_instances)
        body = pane.div(display='grid',
                        grid_template_columns='repeat(2, 1fr)',
                        gap='12px')
        for i in range(1, n_instances + 1):
            cell = body.div(border='1px solid #e5e7eb',
                            border_radius='4px', padding='8px')
            cell.div(f'Invoice #{i}', font_weight='600',
                     margin_bottom='6px', color='#374151')
            cell.data(f'.lines_{i}', self._seed(5))
            grid = cell.groupletGrid(
                storepath=f'.lines_{i}',
                resource='invoice_row',
                defaultRow=dict(qty=1, price=0),
            )
            # Each controller increments the counter on _onBuilt.
            # When all instances are ready, log the elapsed time.
            grid.dataController("""
                var p = window.__perf50;
                if (!p) return;
                p.n += 1;
                if (p.n === p.target) {
                    var ms = Math.round(performance.now() - p.t0);
                    console.log('[perf_50] all ' + p.target
                                + ' groupletGrids ready in ' + ms + ' ms');
                }
            """, _onBuilt=True)
