# -*- coding: utf-8 -*-

from html import escape

from gnr.web.batch.btcaction import BaseResourceAction

caption = '!![en]Move counters to sys.counter'
tags = 'superadmin,_DEV_'
description = '!![en]Analyse, load and check the counters numbered by sys.counter'


class Main(BaseResourceAction):
    batch_prefix = 'mcnt'
    batch_title = 'Move counters to sys.counter'
    batch_cancellable = False
    batch_delay = 0.5

    def pre_process(self):
        self.report = []

    def do(self):
        sys_counter = self.db.table('sys.counter')
        counters = self.batch_parameters.get('counters') or None
        load = self.batch_parameters.get('load')
        tables = sorted({tblobj.fullname for tblobj, field in sys_counter.countersToMigrate(counters)})
        for table in self.btc.thermo_wrapper(tables, message=lambda t, n, m: t):
            self.report.extend(sys_counter.migrateCounters(counters=counters, tables=[table], load=load))
        if load:
            self.db.commit()

    def result_handler(self):
        if not self.report:
            return self.page.localize('!![en]No counter to migrate: set the new_counters switch '
                                      'or name the counters'), dict()
        rows = ''.join('<tr><td>%s.%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            escape(r['table']), escape(r['field']), escape(str(r['period'])), r['count'], escape(r['status']),
            escape('; '.join(str(p) for p in r['problems']))) for r in self.report)
        header = ''.join('<th>%s</th>' % self.page.localize(h) for h in (
            '!![en]Counter', '!![en]Period', '!![en]Numbers', '!![en]Status', '!![en]Problems'))
        return '<table><tr>%s</tr>%s</table>' % (header, rows), dict()

    def table_script_parameters_pane(self, pane, **kwargs):
        switch = self.db.application.experimentalValue('new_counters', 'counters')
        fb = pane.formbuilder(cols=1, border_spacing='10px')
        fb.textbox(value='^.counters', lbl='!![en]Counters', width='25em',
                   placeholder=switch or "* or pkg.table.field,...")
        fb.checkbox(value='^.load', label='!![en]Load the periods not loaded yet')
