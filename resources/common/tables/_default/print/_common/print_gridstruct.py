# -*- coding: utf-8 -*-

# test_special_action.py
# Created by Francesco Porcari on 2010-07-02.
# Copyright (c) 2010 Softwell. All rights reserved.

from gnr.web.batch.btcprint import BaseResourcePrint



tags='user'
caption = '!!Print grid'
description='!!Print grid'

class Main(BaseResourcePrint):
    batch_prefix = 'pr_grid'
    batch_cancellable = True
    batch_delay = 0.5
    batch_immediate = 'print'
    batch_title = 'Print grid'
    print_mode = 'pdf'
    html_res = 'html_res/print_gridstruct'

    def do(self):
        struct = self.batch_parameters['currentGridStruct']
        totalize_mode = self.batch_parameters['totalize_mode']
        totalize_footer = self.batch_parameters['totalize_footer']
        totalize_carry = self.batch_parameters['totalize_carry']
        if totalize_mode or totalize_footer or totalize_carry:
            self.htmlMaker.totalize_mode = totalize_mode or 'doc'
            self.htmlMaker.totalize_footer = totalize_footer or True
            self.htmlMaker.totalize_carry = totalize_carry
        self.htmlMaker.page_orientation = self.batch_parameters['orientation'] or 'V'
        self.htmlMaker.htmlTemplate = self.batch_parameters['letterhead_id']
        self.htmlMaker.sourceStruct = struct
        self.htmlMaker.row_table = getattr(self,'maintable',None)
        self.htmlMaker.callingBatch = self
        self.print_record(record='*',storagekey='x')
        
    def table_script_parameters_pane(self,pane,extra_parameters=None,record_count=None,**kwargs):
        pane = pane.div(padding='10px',min_height='60px')        
        fb = pane.formbuilder(cols=1,fld_width='20em',border_spacing='4px')
        fb.textbox(value='^.print_title',lbl='!!Title')
        fb.filteringSelect(value='^.orientation',lbl='!!Orientation',values='H:Horizontal,V:Vertical',default='V')
        fb.dbSelect(dbtable='adm.htmltemplate', value='^.letterhead_id',lbl='!!Letterhead',hasDownArrow=True)
        fb.filteringSelect(value='^.totalize_mode', lbl='!!Totalize',values='doc:Document,page:Page')
        fb.textbox(value='^.totalize_carry',lbl='!!Carry',hidden='^.totalize_mode?=#v!="page"')
        fb.textbox(value='^.totalize_footer',lbl='!!Footer',hidden='^.totalize_mode?=!#v')
        fb.checkbox(value='^.allrows',label='!!Print all rows')
        fb.dataController("""
                        var grid = genro.wdgById(gridId);
                        SET .grid_datamode = grid.datamode;
                        SET .currentGridStruct = grid.getExportStruct();""",
                        _onBuilt=True,gridId=extra_parameters['gridId'])