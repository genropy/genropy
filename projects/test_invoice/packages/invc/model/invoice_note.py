#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('invoice_note', pkey='id', name_long='!!Invoice Note',
                        name_plural='!!Invoice Notes')
        self.sysFields(tbl)
        tbl.column('invoice_id', size='22', group='_',
                    name_long='!!Invoice').relation(
            'invoice.id', relation_name='notes',
            mode='foreignkey', onDelete='cascade')
        tbl.column('note_type', size=':20', name_long='!!Note Type')
        tbl.column('note_text', name_long='!!Note Text')
        tbl.column('priority', dtype='I', name_long='!!Priority')
