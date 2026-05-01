#!/usr/bin/python
# -*- coding: UTF-8 -*-

def config(root,application=None):
    invc = root.branch('Invoicer')
    invc.thpage('!!Customers',table='invc.customer')
    invc.thpage('!!Invoice',table='invc.invoice')
    invc.thpage('!!Invoice rows',table='invc.invoice_row')
    invc.thpage('!!Products',table='invc.product')
    invc.thpage('!!Product types',table='invc.product_type')
    invc.thpage('!!Postcodes',table='invc.postcode')
    invc.lookups('Lookup tables',lookup_manager='invc')
