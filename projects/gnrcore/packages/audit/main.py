#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='External audit', sqlschema='audit',
                    name_short='Audit', name_long='!!External audit',
                    name_full='External audit')

    def config_db(self, pkg):
        pkg.sqlCode(sql_file='audit.sql')

    def required_packages(self):
        return ['gnrcore:sys']


class Table(GnrDboTable):
    pass
