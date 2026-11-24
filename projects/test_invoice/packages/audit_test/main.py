#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='Tables for the external audit tests', sqlschema='audit_test',
                    sqlprefix=True, name_short='Audit test', name_long='Audit test',
                    name_full='Audit test')

    def config_db(self, pkg):
        pass

    def required_packages(self):
        return ['gnrcore:audit']


class Table(GnrDboTable):
    pass
