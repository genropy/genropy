#!/usr/bin/python
# -*- coding: UTF-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrnumber import decimalRound

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('invoice_id')
        r.fieldcell('product_id')
        r.fieldcell('quantity')
        r.fieldcell('unit_price')
        r.fieldcell('vat_rate')
        r.fieldcell('tot_price')
        r.fieldcell('vat')

    def th_order(self):
        return 'invoice_id'

    def th_query(self):
        return dict(column='invoice_id', op='contains', val='')

class ViewFromProduct(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('invoice_id')
        r.fieldcell('@invoice_id.@customer_id.account_name',name='Customer')
        r.fieldcell('quantity')
        r.fieldcell('unit_price')
        r.fieldcell('vat_rate')
        r.fieldcell('tot_price')
        r.fieldcell('vat')

    def th_bottom_custom(self,bottom):
        bottom.slotBar('*,sum@quantity,5,sum@tot_price,5',border_top='1px solid silver',height='23px')


class ViewFromInvoice(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('product_id',edit=dict(remoteRowController=True,validate_notnull=True))
        r.fieldcell('quantity',edit=dict(remoteRowController=True))
        r.fieldcell('unit_price')
        r.fieldcell('vat_rate')
        r.fieldcell('tot_price',totalize='.total')
        r.fieldcell('vat',totalize='.vat')

    @public_method
    def th_remoteRowController(self,row=None,field=None,**kwargs):
        field = field or 'product_id' 
        if not row['product_id']:
            return
        if not row['quantity']:
            row['quantity'] = 1
        if field == 'product_id':
            unit_price,vat_rate = self.db.table('invc.product').readColumns(columns='$unit_price,@vat_type_code.vat_rate',pkey=row['product_id'])
            row['unit_price'] = unit_price
            row['vat_rate'] = vat_rate
        row['tot_price'] = decimalRound(row['quantity'] * row['unit_price'])
        row['vat'] = decimalRound(row['vat_rate'] * row['tot_price'] /100)
        return row

class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('invoice_id')
        fb.field('product_id')
        fb.field('quantity')
        fb.field('unit_price')
        fb.field('vat_rate')
        fb.field('tot_price')
        fb.field('vat')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
