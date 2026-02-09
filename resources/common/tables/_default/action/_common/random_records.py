# -*- coding: utf-8 -*-

# random_records.py
# Created by Francesco Porcari on 2010-07-02.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.web.batch.btcaction import BaseResourceAction
from gnr.sql.gnrsql_random import RandomRecordGenerator

caption = 'Create random records'
tags = '_DEV_'
description = '!!Create random records'

class Main(BaseResourceAction):
    batch_prefix = 'crr'
    batch_title = 'Create random records'
    batch_cancellable = False
    batch_delay = 0.5
    batch_immediate = True

    def do(self):
        how_many = self.batch_parameters['batch']['how_many']
        batch_prefix = self.batch_parameters['batch'].get('batch_prefix', self.batch_prefix)
        fields = dict(self.batch_parameters['fields'])
        generator = RandomRecordGenerator(self.tblobj)
        generator.generate(how_many, fields=fields, batch_prefix=batch_prefix)

    def table_script_parameters_pane(self, pane, table=None,**kwargs):
        tblobj = self.db.table(table)
        fb = pane.div(border_bottom='1px solid silver',padding='3px').formbuilder(datapath='.batch', cols=2, border_spacing='2px')
        fb.numberTextBox('^.how_many', lbl='How many', width='5em', validate_notnull=True, default_value=10)
        fb.textbox('^.batch_prefix', lbl='Batch prefix', width='5em', validate_notnull=True)
        box_campi = pane.div(max_height='600px',overflow='auto')
        fb = box_campi.div(margin_right='15px').formbuilder(margin='5px',cols=3,
                            border_spacing='3px',
                            dbtable=table,
                            datapath='.fields',
                            fld_width='100%',
                            colswidth='auto',
                            width='650px')
        randomValuesDict = dict()
        if hasattr(tblobj, 'randomValues'):
            randomValuesDict = getattr(tblobj, 'randomValues')()
        for col_name, col in list(tblobj.columns.items()):
            attr = col.attributes
            dtype=attr.get('dtype')
            if not col_name in randomValuesDict and (attr.get('_sysfield') or dtype == 'X'):
                continue
            col_rules = randomValuesDict.get(col_name, dict())
            if col_rules is not False:
                if attr.get('size'):
                    col_rules['size']=attr.get('size')
                fb.data('.%s' %col_name, Bag(col_rules))
                fb.data('.%s.dtype' %col_name, dtype)
                if col_rules.pop('ask',None) == False or col_rules.get('equal_to') or col_rules.get('based_on'):
                    continue
                self.table_script_prepareColPars(fb,col_rules,col_name, dtype)
                fb.numberTextBox(value='^.%s.null_perc' % col_name, lbl='NULL %', width='4em',lbl_width='6em', default_value=col_rules.pop('null_perc',0))


    def table_script_prepareColPars(self, fb, col_rules, col_name, col_dtype):

        kw = fb.prepareFieldAttributes(col_name)
        dictExtract(kw, prefix='validate_',pop=True)

        if col_dtype =='B':
            fb.horizontalSlider(value='^.%s.true_value'%col_name ,lbl=kw['lbl'],
                                minimum=0, maximum=100,
                                intermediateChanges=True,
                                discreteValues=11,
                                width='10em',
                                default_value=col_rules.pop('true_value',50))

            fb.div('^.%s.true_value'%col_name, lbl='True %', _class='fakeTextBox')
            return

        if col_dtype in ('I','L','N','R','DH','D','H'):
            lbl=kw.pop('lbl')
            kw.pop('value',None)
            kw.pop('innerHTML',None)
            if col_dtype =='DH':
                kw['tag']='dateTextBox'
            kw['width']='8em'
            if kw['tag']=='dateTextBox':
                kw['period_to']='.%s.max_value'%col_name

            if 'range' in col_rules:
                operator = 'Greater than' if 'greater_than' in col_rules else 'Less than'
                fb.div(col_rules.get('greater_than') or col_rules.get('less_than') , lbl='%s %s' % (lbl, operator), _class='fakeTextBox')
                fb.div(col_rules['range'], lbl='Range',_class='fakeTextBox')
                return

            if 'greater_than' in col_rules:
                fb.div(col_rules['greater_than'], lbl='%s min' % lbl, _class='fakeTextBox')
            else:
                fb.child(value='^.%s.min_value'%col_name,
                              lbl='%s min' % lbl,
                              default_value=col_rules.pop('min_value',None),
                              validate_notnull=True, **kw)
            kw.pop('period_to',None)
            if 'less_than' in col_rules:
                fb.div(col_rules['less_than'], lbl='%s max' % lbl, _class='fakeTextBox')
            else:
                fb.child(value='^.%s.max_value'%col_name,
                              lbl='%s max' % lbl,
                              default_value=col_rules.pop('max_value',None),
                              validate_notnull=True,
                              **kw)
            return
        if col_dtype in ('T','A') and col_rules.get('random_value'):
            lbl=kw.pop('lbl')
            fb.textbox('^.%s.n_words' % col_name, lbl='%s N.Words' % lbl, default_value=col_rules.pop('n_words',None))
            fb.textbox('^.%s.w_length' % col_name, lbl='%s Word Length' % lbl, default_value=col_rules.pop('w_length',None))
            return
        else:
            kw['colspan']=2
            kw.update(col_rules)
            if kw['tag'].lower()=='dbselect':
                kw['tag'] = 'checkboxtext'
                kw['table']=kw.pop('dbtable')
                kw['popup']=True
                kw['value']='%s.pkeys' % kw['value']
                col_rules['table']=kw['table']
                fb.data('.%s' %col_name, Bag(col_rules))
            else:
                kw['value'] = '%s.value' % kw['value']
            fb.child(**kw)
