#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('author', pkey='id', name_long='!!Author', 
                        name_plural='!!Authors', caption_field='fullname')
        self.sysFields(tbl)

        tbl.column('firstname', name_long='!!First name',
                    validate_notnull=True, validate_notnull_error='!!Mandatory field')
        tbl.column('lastname', name_long='!!Last name',
                    validate_notnull=True, validate_notnull_error='!!Mandatory field')
        
        tbl.formulaColumn('fullname', """$firstname||' '||$lastname""", name_long=u'!!Full name',static=True)
