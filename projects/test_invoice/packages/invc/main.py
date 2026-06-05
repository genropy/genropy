#!/usr/bin/env python
# encoding: utf-8
import re

from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage


def _expand_uppercase(match, expander):
    return 'UPPER(%s)' % match.group(1)


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='invc package',sqlschema='invc',sqlprefix=True,
                    name_short='Invc', name_long='Invoicer', name_full='Invc')

    def config_db(self, pkg):
        pass

    def registerMacros(self, db):
        db.addMacro(
            'UPPERCASE',
            re.compile(r'#UPPERCASE\(([^)]+)\)'),
            _expand_uppercase,
        )

    def custom_type_money(self):
        return dict(dtype='N',size='14,2',format='#,###.00')

    def custom_type_perc(self):
        return dict(dtype='N',size='5,2',format='##.00')


        
class Table(GnrDboTable):
    pass
    
