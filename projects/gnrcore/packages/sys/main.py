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

    def onError(self, error_info):
        try:
            tbl = self.db.table('sys.error')
            error_id = error_info.get('error_id', '')
            record_id = error_id.ljust(22, '_') if error_id else None
            error_type = error_info.get('error_type', 'ERR')
            rec = dict(
                description=error_info.get('description'),
                error_data=error_info.get('traceback'),
                username=error_info.get('user'),
                user_ip=error_info.get('user_ip'),
                user_agent=error_info.get('user_agent'),
                error_type=error_type
            )
            if record_id:
                rec['id'] = record_id
            with self.db.tempEnv(connectionName='system',
                                 storename=self.db.rootstore):
                tbl.insert(rec)
                self.db.commit()
        except Exception:
            logger.exception('sys.onError: failed to write to sys.error')


class Table(GnrDboTable):
    def isInStartupData(self):
        return False
        
    def use_dbstores(self,forced_dbstore=None, env_forced_dbstore=None,**kwargs):
        return forced_dbstore or env_forced_dbstore or False
