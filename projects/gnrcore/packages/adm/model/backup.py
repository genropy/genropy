#!/usr/bin/env python
# encoding: utf-8

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
        backups_folder = self.db.application.getPreference(path='backups.backup_folder',pkg='adm') or 'home:maintenance'
        try:
            backupSn = self.db.application.site.storageNode(backups_folder,'backups',f'{filename}.zip')
            print('backup to delete',backupSn.internal_path)
            backupSn.delete()
        except Exception:
            pass

    
    
