# -*- coding: utf-8 -*-

# test_special_action.py
# Created by Francesco Porcari on 2010-07-02.
# Copyright (c) 2011 Softwell. All rights reserved.

from __future__ import division
from past.utils import old_div
from gnr.web.batch.btcaction import BaseResourceAction

caption = '!!Set rows values'
tags = '_DEV_'
description = '!!Set rows values'

class Main(BaseResourceAction):
    batch_prefix = 'srv'
    batch_title = 'Set rows value'
    batch_cancellable = False
    batch_delay = 0.5
    batch_immediate = True
    
    def do(self):
        values = self.batch_parameters.get('values')
        do_triggers = self.batch_parameters.get('do_triggers')

        updater = dict()
        for k,v,forced_null in values.digest('#k,#v,#a.forced_null'):
            if forced_null:
                updater[k] = None
            elif v is not None:
                updater[k] = v
        self.batchUpdate(updater,_raw_update=not do_triggers,message='setting_values',subtable='*')
        self.db.commit()

    def table_script_parameters_pane(self, pane, table=None,**kwargs):
        tblobj = self.db.table(table)
        cols = int(old_div(len(tblobj.columns),30))+1
        box = pane.div(max_height='600px',overflow='auto')
        box.menu(validclass='gnrfieldlabel').menuline('Force value to NULL',
                                                    action="""var lablesn = $2;
                                                              lablesn.setRelativeData('.'+lablesn.attr.fieldname+'?forced_null',true);""")
        fb = box.formbuilder(margin='5px',cols=cols,border_spacing='3px',dbtable=table,datapath='.values')
        for k,v in list(tblobj.columns.items()):
            attr = v.attributes
            if attr.get('dtype') == 'X':
                continue
            #if attr.get('_sysfield') and not (k=='__syscode' and self.isDeveloper()):
            #    continue
            kw = {}
            if attr.get('dtype')=='DH' or attr.get('dtype')=='DHZ':
                kw['tag'] = 'dateTimeTextBox'
                kw['dtype'] = attr.get('dtype')
            f = fb.field(k,validate_notnull=False,html_label=True,zoom=False,lbl_fieldname=k,
                        validate_onAccept='SET .{}?forced_null=false;'.format(k),
                        lbl_color='^.{}?forced_null?=#v?"red":null'.format(k),
                        **kw)
            f.attributes.pop('disabled',None)
            f.attributes.pop('unmodifiable',None)
        box.div(border_top='1px solid silver',padding='3px',text_align='right').checkbox(value='^.do_triggers',label='Do triggers',_tags='_DEV_')


