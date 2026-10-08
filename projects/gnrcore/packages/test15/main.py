#!/usr/bin/env python
# encoding: utf-8

from gnr.app import pkglog as logger
from gnr.app.gnrdbo import GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='test15 package (retired)', sqlschema='test15',
                    name_short='Test15', name_long='Test15', name_full='Test15', _syspackage=True)

    def config_db(self, pkg):
        pass

    def onApplicationInited(self):
        logger.warning("gnrcore:test15 is retired: its examples now live in gnrcore:test. "
                       "Remove it from the instance packages; this placeholder will be deleted.")
