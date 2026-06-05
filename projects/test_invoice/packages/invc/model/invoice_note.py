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
        tbl.formulaColumn('is_warning',
                          sql_formula="$note_type LIKE :warn_pat",
                          var_warn_pat='WARN%%',
                          dtype='B', name_long='Is Warning')
        tbl.formulaColumn('note_type_clean',
                          sql_formula="UPPER(TRIM($note_type))",
                          dtype='T', name_long='Note Type Clean')
        tbl.formulaColumn('created_date',
                          sql_formula="date_trunc('day', $__ins_ts)",
                          dtype='D', name_long='Created Date')
        # RTRIM - pattern erpy
        tbl.formulaColumn('note_text_rtrim',
                          sql_formula="RTRIM($note_text)",
                          dtype='T', name_long='Note Text Rtrim')
