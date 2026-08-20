# encoding: utf-8

import os 
from gnr.core.gnrlang import gnrImport

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('upgrade', pkey='codekey',pkey_columns='pkg,filename', pkey_columns_joiner='|',
                        name_long='!!Upgrade ', name_plural='!!Upgrades',caption_field='codekey')
        self.sysFields(tbl,id=False)
        tbl.column('codekey',size=':80',name_long='Identifier')
        tbl.column('pkg',size=':20',name_long='Package')
        tbl.column('filename', size=':40', name_long='!!Filename')
        tbl.column('error', name_long='!!Upgrade error', name_short='!!Error')

    def upgradePath(self,codekey):
        pkg,filename = codekey.split('|')
        return os.path.join(self.db.application.packages[pkg].packageFolder,'lib','upgrades','%s.py' %filename)
        

    def runUpgrades(self):
        """Run all pending upgrades and return the failed ones as a list
        of ``(codekey, error)`` tuples (empty list if all succeeded)."""
        errors = []
        alreadyRun= self.query(where='$error IS NULL').fetchAsDict('codekey')
        for pkg,pkgobj in list(self.db.application.packages.items()):
            upgradefolder = os.path.join(pkgobj.packageFolder,'lib','upgrades') 
            if not os.path.isdir(upgradefolder):
                continue
            for f in sorted(os.listdir(upgradefolder)):
                filename,ext = os.path.splitext(f)
                if ext!='.py':
                    continue
                upgradekey = '%s|%s' %(pkg,filename)
                if upgradekey not in alreadyRun:
                    print('upgrade',upgradekey)
                    error = self.runUpgrade(upgradekey)
                    if error:
                        errors.append((upgradekey,error))
        return errors
    
    def runUpgrade(self,codekey):
        pkg,filename = codekey.split('|')
        filepath = self.upgradePath(codekey)
        error = None
        try:
            m = gnrImport(filepath)
            error = m.main(self.db)
            # commit inside the try: deferred constraints and writes queued
            # on other connections by triggers only surface here, and they
            # must be recorded as this upgrade's error, not kill the caller
            self.db.commit()
        except Exception as e:
            # rollbackAll, not rollback: triggers may have written to other
            # connections (e.g. the root store during a dbstore upgrade)
            self.db.rollbackAll()
            error = str(e)
        with self.recordToUpdate(codekey,insertMissing=True) as r:
            r['error'] = error
            r['pkg'] = pkg
            r['filename'] = filename
        if error:
            print('ERROR',codekey,error)
        self.db.commit()
        return error

    def use_dbstores(self,**kwargs):
        return True
