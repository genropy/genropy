#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='Tables for the XTD and relidx tests', sqlschema='xtd_test',
                    sqlprefix=True, name_short='XTD test', name_long='XTD test',
                    name_full='XTD test')

    def config_db(self, pkg):
        pass


class Table(GnrDboTable):
    pass
