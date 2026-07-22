#!/usr/bin/env python
# encoding: utf-8

from gnr.app import pkglog as logger


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('backup', pkey='id', name_long='!!Backup', name_plural='!!Backups',rowcaption="$name")
        self.sysFields(tbl)
        tbl.column('name' ,name_long='!!Name')
        tbl.column('start_ts',dtype='DH',name_long='!!Backup start ts')
        tbl.column('end_ts',dtype='DH',name_long='!!Backup end ts')
        tbl.column('file_url', name_long='!!Download')
        
        tbl.formulaColumn('completed', "$end_ts IS NOT NULL", name_long='!!Completed')

    def trigger_onInserted(self, record):
        if self.db.application.getPreference(path='backups.max_copies',pkg='adm'):
            self.deleteSelection(where='$end_ts IS NOT NULL', order_by='$end_ts DESC', 
                                 offset=self.db.application.getPreference(path='backups.max_copies',pkg='adm'))

    def trigger_onDeleted(self,record):
        self.deleteBackupFile(filename=record['name'])

    def deleteBackupFile(self, filename=None):
        # Backups live directly in the backup folder (see the adm:backup `dumpall`
        # action). The file extension depends on the dump format: `.zip` for the
        # general case, `.pgd` for a single postgres store. Match by base name so
        # every format is removed regardless of extension.
        backups_folder = self.db.application.getPreference(path='backups.backup_folder',pkg='adm') or 'maintenance:backups'
        folderSn = self.db.application.site.storageNode(backups_folder)
        deleted = False
        for childSn in (folderSn.children() or []):
            if childSn.isfile and childSn.cleanbasename == filename:
                try:
                    childSn.delete()
                    deleted = True
                except Exception as e:
                    logger.exception('Error deleting backup file %s: %s', childSn.internal_path, e)
        if not deleted:
            logger.warning('No backup file found to delete for: %s', filename)

    
    
