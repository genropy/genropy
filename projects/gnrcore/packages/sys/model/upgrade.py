# encoding: utf-8

import os
from gnr.app import pkglog as logger
from gnr.core.gnrlang import gnrImport

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('upgrade', pkey='codekey',pkey_columns='pkg,filename', pkey_columns_joiner='|',
                        name_long='!!Upgrade ', name_plural='!!Upgrades',caption_field='codekey')
        self.sysFields(tbl,id=False)
        #the filesystem ceiling on a name component is 255: sized for it, the
        #codekey can hold any upgrade a package can actually carry, and pkg
        #matches adm.pkginfo.pkgid rather than overflowing 20 chars sooner
        tbl.column('codekey',size=':306',name_long='Identifier')
        tbl.column('pkg',size=':50',name_long='Package')
        tbl.column('filename', size=':255', name_long='!!Filename')
        tbl.column('error', name_long='!!Upgrade error', name_short='!!Error')

    def upgradePath(self,codekey):
        pkg,filename = codekey.split('|')
        return os.path.join(self.db.application.packages[pkg].packageFolder,'lib','upgrades','%s.py' %filename)
        

    def runUpgrades(self):
        """Run all pending upgrades and return the failed ones as a list
        of ``(codekey, error)`` tuples (empty list if all succeeded).

        A candidate rejected by the codekey size pre-flight stops the whole run
        and is reported in the same list: running the rest would apply the stack
        with a hole in it."""
        errors = []
        alreadyRun= self.query(where='$error IS NULL').fetchAsDict('codekey')
        codekeyMaxSize = self.column('codekey').getAttr('size')
        if codekeyMaxSize and ':' in codekeyMaxSize:
            codekeyMaxSize = codekeyMaxSize.split(':')[1]
        codekeyMaxSize = int(codekeyMaxSize) if codekeyMaxSize else None
        candidates = []
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
                    candidates.append(upgradekey)
        #pre-flight: the codekey is sized for any name a filesystem can hold, so
        #this cannot fire in practice. If it ever does, nothing runs: an upgrade
        #skipped in the middle of the stack leaves the ones depending on it
        #working against a database that never got its change.
        oversized = [k for k in candidates if codekeyMaxSize and len(k) > codekeyMaxSize]
        if oversized:
            for upgradekey in oversized:
                error = 'filename too long for the codekey column (max %s chars)' %codekeyMaxSize
                logger.error('Upgrade %s rejected: %s', upgradekey, error)
                errors.append((upgradekey,error))
            logger.error('No upgrade was run: %i rejected candidate(s) would leave the '
                         'stack half applied', len(oversized))
            return errors
        for upgradekey in candidates:
            logger.info('Running upgrade %s', upgradekey)
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
            logger.error('Upgrade %s failed: %s', codekey, error)
        self.db.commit()
        return error

    def use_dbstores(self,**kwargs):
        return True
