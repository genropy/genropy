#!/usr/bin/python
# -*- coding: UTF-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('account_name')
        r.fieldcell('email')
        r.fieldcell('phone')
        r.fieldcell('customer_type_code')
        r.fieldcell('payment_type_code')
        r.fieldcell('street_address')
        r.fieldcell('state')
        r.fieldcell('suburb')
        r.fieldcell('postcode')
        r.fieldcell('n_invoices')
        r.fieldcell('invoiced_total',format='#,###.00')


    def th_order(self):
        return 'account_name'

    def th_query(self):
        return dict(column='account_name', op='contains', val='')

    def th_sections_shop(self):
        return [dict(code='all',caption='All customers'),
                dict(code='with_invoices',caption='With invoices',condition='$n_invoices>0'),
                dict(code='without_invoices',caption='Without invoices',condition='$n_invoices=0')]


    def th_top_toolbarsuperiore(self,top):
        top.slotToolbar('5,sections@shop,*,sections@customer_type_code,5',
                        childname='upper',_position='<bar',gradient_from='#999',gradient_to='#666')

    def th_options(self):
        return dict(fileImport='txt')


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.customerData(bc.roundedGroupFrame(title='Customer data',region='top',datapath='.record',height='160px'))
        tc = bc.tabContainer(region = 'center',margin='2px')
        self.customerInvoices(tc.contentPane(title='Invoices'))
        self.customerProducts(tc.contentPane(title='Invoiced products'))
        self.customerNotes(tc.contentPane(title='Notes',datapath='.record'))

    def customerData(self,pane):
        fb = pane.div(margin_left='50px',margin_right='80px').formbuilder(cols=3, border_spacing='4px',colswidth='auto',fld_width='100%')
        fb.field('account_name',colspan=3)
        fb.field('email',colspan=3)
        fb.field('phone')
        fb.field('customer_type_code')
        fb.field('payment_type_code')
        fb.field('street_address',colspan=3)
        fb.field('suburb')
        fb.field('state')
        fb.field('postcode')


    def customerNotes(self,frame):
        frame.simpleTextArea(value='^.note',editor=True)

    def customerInvoices(self,pane):
        pane.dialogTableHandler(relation='@invoices',
                                viewResource='ViewFromCustomer')

    def customerProducts(self,pane):
        pane.plainTableHandler(table='invc.product',
                                condition='@rows.@invoice_id.customer_id =:cust_id',
                                condition_cust_id='^#FORM.record.id',export=True)

    def th_options(self):
        return dict(dialog_height='550px', dialog_width='800px',doc=True,selector=True)

