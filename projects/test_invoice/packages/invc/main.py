#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='invc package',sqlschema='invc',sqlprefix=True,
                    name_short='Invc', name_long='Invoicer', name_full='Invc')
                    
    def config_db(self, pkg):
        pass

    def custom_type_money(self):
        return dict(dtype='N',size='14,2',format='#,###.00')
        
    def custom_type_perc(self):
        return dict(dtype='N',size='5,2',format='##.00')


        
class Table(GnrDboTable):
    pass
    
