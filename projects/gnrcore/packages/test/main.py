#!/usr/bin/env python
# encoding: utf-8

from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='test package', sqlschema='test',
                    name_short='Test', name_long='Test', name_full='Test',_syspackage=True)

    def config_db(self, pkg):
        pass

    def loginUrl(self):
        return 'test/login'

class Table(GnrDboTable):
    pass

class WebPage(object):
    package_py_requires = 'gnrcomponents/source_viewer/source_viewer:SourceViewer'
