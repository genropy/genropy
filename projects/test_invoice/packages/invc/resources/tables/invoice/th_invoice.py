#!/usr/bin/python
# -*- coding: UTF-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('inv_number')
        r.fieldcell('customer_id',zoom=True)
        r.fieldcell('@customer_id.state')
        r.fieldcell('date')
        r.fieldcell('total',
                    range_low='value<1000',
                    range_low_color='red',
                    range_high='value>10000',
                    range_high_color='green')
        r.fieldcell('vat_total')
        r.fieldcell('gross_total')



    def th_struct_bis(self,struct):
        "Vista alternativa"
        r = struct.view().rows()
        r.fieldcell('inv_number')
        r.fieldcell('customer_id',zoom=True)
        r.fieldcell('date')

    def th_order(self):
        return 'inv_number'

    def th_query(self):
        return dict(column='inv_number', op='contains', val='')

class ViewFromCustomer(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('inv_number')
        r.fieldcell('date')
        r.fieldcell('total')
        r.fieldcell('vat_total')
        r.fieldcell('gross_total')

    def th_order(self):
        return 'inv_number'

    def th_bottom_custom(self,bottom):
        bottom.slotBar('*,sum@total,5,sum@vat_total,5,sum@gross_total,5',
            border_top='1px solid silver',height='23px')

class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.invoiceHead(bc.borderContainer(region='top',datapath='.record',height='150px'))
        self.invoiceRows(bc.contentPane(region='center'))

    def invoiceHead(self,bc):
        left = bc.roundedGroup(title='Invoice head',region='left',width='50%')
        fb = left.formbuilder(cols=1, border_spacing='4px')
        fb.field('inv_number')
        fb.field('date')
        bc.contentPane(region='center').linkerBox('customer_id',margin='2px',openIfEmpty=True,
                                                    columns='$account_name,$state,@customer_type_code.description',
                                                    auxColumns='$suburb,$state',
                                                    newRecordOnly=True,formResource='Form',
                                                    dialog_height='500px',dialog_width='800px')

    def invoiceRows(self,pane):
        th = pane.inlineTableHandler(relation='@rows',viewResource='ViewFromInvoice',picker='product_id')
        bar = th.view.bottom.slotBar('*,fbtot,15',height='20px',background='#EEF2F4',border_top='1px solid silver',padding='3px')
        fb = bar.fbtot.formbuilder(cols=3,border_spacing='3px',fld_format='###,###,###.00',
                fld_class='fakeTextBox fakeNumberTextBox',fld_width='7em')
        fb.div('^.grid.total',lbl='Total')
        fb.div('^.grid.vat',lbl='VAT')
        fb.div('==(_vat || 0) + (_tot || 0)',_vat='^.grid.vat',_tot='^.grid.total',
                    lbl='Gross')
        


    def th_options(self):
        return dict(dialog_height='500px', dialog_width='700px')
