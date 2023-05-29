#!/usr/bin/env python
# encoding: utf-8

from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage
from gnr.core.gnrdict import dictExtract

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(sqlschema='adm',
                    comment='Admin',
                    name_short='Adm',
                    name_long='!!Administration',
                    name_full='!!Administration Tool')

    def config_db(self, pkg):
        pass

    def required_packages(self):
        return ['gnrcore:sys']

    def authenticate(self, username,group_code=None,**kwargs):
        tblobj = self.db.table('adm.user')
        def cb(cache=None,identifier=None,group_code=None,**kwargs):
            if identifier in cache:
                return cache[identifier],True
            with self.db.tempEnv(current_group_code=group_code):
                result = tblobj.query(columns="""*,$all_tags""",
                                  where='$username = :user',
                                  user=username, limit=1).fetch()
            kwargs = dict()
            if result:
                user_record = dict(result[0])
                group_code = group_code or user_record.get('group_code')
                group_rootpage,menubag = None,None
                if group_code:
                    group_rootpage,menubag = self.db.table('adm.group').readColumns(pkey=group_code,columns='$rootpage,$custom_menu')
                kwargs['tags'] = user_record.pop('all_tags')
                kwargs['pwd'] = user_record.pop('md5pwd')
                kwargs['status'] = user_record['status']
                kwargs['email'] = user_record['email']
                kwargs['firstname'] = user_record['firstname']
                kwargs['lastname'] = user_record['lastname']
                kwargs['user_id'] = user_record['id']
                kwargs['group_code'] = group_code
                kwargs['avatar_rootpage'] = user_record['avatar_rootpage']  or group_rootpage
                kwargs['locale'] = user_record['locale'] or self.application.config('default?client_locale')
                kwargs['user_name'] = '%s %s' % (user_record['firstname'], user_record['lastname'])
                kwargs['user_record'] = user_record
                kwargs['menubag'] = menubag
                kwargs.update(dictExtract(user_record, 'avatar_'))
                allowed_ip = self.db.table('adm.user_access_group').allowedUser(user_record['id'])
                if allowed_ip is not None:
                    kwargs['allowed_ip'] = allowed_ip
                cache[identifier] = kwargs
            return kwargs,False
        identifier = username
        if group_code:
            identifier = f'{username}_{group_code}'
        authkwargs = tblobj.tableCachedData('user_authenticate',cb,identifier=identifier,group_code=group_code)
        return authkwargs


        
    def onAuthentication(self, avatar):
        pass

    def onAuthenticated(self, avatar):
        pass

    def onExternalUser(self,externalUser=None):
        self.db.table('adm.user').syncExternalUser(externalUser)
        
    def newUserUrl(self):
        return 'adm/new_user'

    def modifyUserUrl(self):
        return 'adm/modify_user'

    def loginUrl(self):
        return 'adm/login'

    
class Table(GnrDboTable):
    def use_dbstores(self,forced_dbstore=None, env_forced_dbstore=None,**kwargs):
        return forced_dbstore or env_forced_dbstore or False

    def isInStartupData(self):
        return False
        
