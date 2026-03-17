#!/usr/bin/env python
# encoding: utf-8
import logging

from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

logger = logging.getLogger('gnr.pkg.sys')

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(sqlschema='sys',
                    comment='sys',
                    name_short='System',
                    name_long='System',
                    name_full='System',_syspackage=True)

    def onDbStarting(self):
        self.db.changeLogTable = 'sys.dbchange'

    def errorHandler(self, **kwargs):
        try:
            self.db.table('sys.error').errorHandler(**kwargs)
        except Exception:
            logger.exception('sys.errorHandler: failed to write to sys.error')


class Table(GnrDboTable):
    def isInStartupData(self):
        return False
        
    def use_dbstores(self,forced_dbstore=None, env_forced_dbstore=None,**kwargs):
        return forced_dbstore or env_forced_dbstore or False
