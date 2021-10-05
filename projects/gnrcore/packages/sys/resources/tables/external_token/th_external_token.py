#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('datetime')
        r.fieldcell('expiry')
        r.fieldcell('allowed_user')
        r.fieldcell('connection_id')
        r.fieldcell('max_usages')
        r.fieldcell('allowed_host')
        r.fieldcell('page_path')
        r.fieldcell('method')
        r.fieldcell('parameters')
        r.fieldcell('exec_user')

    def th_order(self):
        return 'datetime'

    def th_query(self):
        return dict(column='datetime', op='contains', val='')

class ViewFromUserobject(BaseComponent):
    def th_hiddencolumns(self):
        return '$id,$page_path,$external_url'

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('datetime',width='10em')
        r.fieldcell('expiry')
        r.fieldcell('allowed_user')
        r.fieldcell('exec_user')
        r.cell('copyurl',calculated=True,name='Copy url',cellClasses='cellbutton',
                    format_buttonclass='copy iconbox',
                    format_isbutton=True,
                    format_onclick="""
            var row = this.widget.rowByIndex($1.rowIndex);
            var external_url = row.external_url;
            var where_pars = this.getRelativeData('#FORM.record.data.where_pars');
            var widgetlist = where_pars.getNodes().map(function(n){
                return {lbl:n.label,value:`^.${n.label}`,placeholder:n.getValue()};
            });
            widgetlist.push({
                value:'^.output',
                lbl:'Output',
                tag:'filteringSelect',
                values:'html:HTML,json:JSON,xls:Excel,tabtext:CSV'
            });
            genro.dlg.prompt("Copy url",{
                    widget:widgetlist,
                    action:function(result){
                        let txtlist = [external_url];
                        result.getNodes().forEach(function(parNode){
                            let value = parNode.getValue();
                            if(!isNullOrBlank(value)){
                                value = encodeURIComponent(value);
                                txtlist.push(`${parNode.label}=${value}`);
                            }
                        });
                        navigator.clipboard.writeText(txtlist.join('&'));
                    }
                }
            );
            """)

    def th_order(self):
        return 'datetime'

    def th_query(self):
        return dict(column='datetime', op='contains', val='')

class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('datetime')
        fb.field('expiry')
        fb.field('allowed_user')
        fb.field('connection_id')
        fb.field('max_usages')
        fb.field('allowed_host')
        fb.field('page_path')
        fb.field('method')
        fb.field('parameters')
        fb.field('exec_user')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
