#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_groupedStruct(self,struct):
        "By type and date"
        r = struct.view().rows()
        r.fieldcell('error_type', width='15em')
        r.fieldcell('__ins_ts', name='Date', width='10em', format='ymd')
        r.cell('_grp_count', name='Cnt', width='4em', group_aggr='sum')

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('__ins_ts', name='Datetime', width='8em')
        r.fieldcell('error_code', name='Error code', width='8em')
        r.fieldcell('id', name='Id', width='15em')
        r.fieldcell('error_type', name='Tipo di errore', width='10em')
        r.fieldcell('description', name='Descrizione', width='20em')
        r.fieldcell('request_host', name='Request Host', width='8em')
        r.fieldcell('request_uri', name='Request URI', width='8em')
        r.fieldcell('rpc_method', name='RPC Method', width='8em')
        r.fieldcell('rpc_kwargs', name='RPC kwargs', width='15em',
                    format_bag_nested=True, format_bag_omitEmpty=False)
        r.fieldcell('username', name='User')
        r.fieldcell('user_ip', name='User ip')
        r.fieldcell('user_agent', name='User agent')

    def th_order(self):
        return '__ins_ts:d'

    def th_query(self):
        return dict(column='__ins_ts', op='equal', val='')


class Form(BaseComponent):
    def th_form(self, form):
        # pane = form.record
        bc = form.center.borderContainer(datapath='#FORM.record')
        self.left(bc.contentPane(region='left',margin='2px',_class='pbl_roundedGroup'))
        self.right(bc.borderContainer(region='center',margin='2px',_class='pbl_roundedGroup'))

    def left(self,pane):
        width='35em'
        pane.div('Error Data',_class='pbl_roundedGroupLabel')
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('error_type',width='15em')
        fb.field('description',width='15em')
        fb.field('username',width='15em')
        fb.field('user_ip',width='15em')
        fb.field('fixed',colspan=2,width=width)
        fb.field('user_agent',colspan=2,width=width,tag='simpleTextArea',height='2.5em')

    def right(self,bc):
        bc.contentPane(region='top').div('Traceback',_class='pbl_roundedGroupLabel')
        bc.contentPane(region='center',overflow='hidden').tracebackViewer(
            value='^#FORM.record.error_data',height='100%')



    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
