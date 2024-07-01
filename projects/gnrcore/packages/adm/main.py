#!/usr/bin/env python
# encoding: utf-8

from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrbag import Bag

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(sqlschema='adm',
                    comment='Admin',
                    name_short='Adm',
                    name_long='!!Administration',
                    name_full='!!Administration Tool',
                    )

    def config_db(self, pkg):
        pass

    def required_packages(self):
        return ['gnrcore:sys']

    def authenticate(self, username,group_code=None,**kwargs):
        tblobj = self.db.table('adm.user')
        login_group_code = group_code
        def cb(cache=None,identifier=None,group_code=None,**kwargs):
            if identifier in cache:
                return cache[identifier],True
            with self.db.tempEnv(current_group_code=group_code):
                result = tblobj.query(columns="""*,$fullname,$all_tags,$all_groups""",
                                  where='$username = :user',
                                  user=username, limit=1).fetch()
            kwargs = dict()
            if result:
                user_record = dict(result[0])
                all_groups = user_record['all_groups']
                all_groups = all_groups.split(',') if all_groups else []
                if group_code and (group_code not in all_groups):
                    group_code = None
                group_code = group_code or user_record.get('group_code')
                group_record = dict()
                if group_code:
                    group_record = self.db.table('adm.group').cachedRecord(pkey=group_code)
                if group_record.get('require_2fa') and group_record.get('no2fa_alternative_group') \
                    and not user_record.get('avatar_secret_2fa'):
                    group_code =  group_record.get('no2fa_alternative_group')
                    group_record = self.db.table('adm.group').cachedRecord(pkey=group_code)
                    with self.db.tempEnv(current_group_code=group_code):
                        user_record = dict(tblobj.query(where='$id=:uid',uid=user_record['id'],
                                                        columns='*,$all_tags').fetch()[0])
                kwargs['tags'] = user_record.pop('all_tags')
                kwargs['pwd'] = user_record.pop('md5pwd')
                kwargs['status'] = user_record['status']
                kwargs['email'] = user_record['email']
                kwargs['firstname'] = user_record['firstname']
                kwargs['lastname'] = user_record['lastname']
                kwargs['user_id'] = user_record['id']
                kwargs['multi_group'] = all_groups and (len(all_groups)>1 or user_record['group_code'] is None)
                if kwargs['multi_group'] and login_group_code is None:
                    kwargs['group_code'] = None
                else:
                    kwargs['group_code'] = group_code
                kwargs['main_group_code'] = user_record['group_code']
                kwargs['avatar_rootpage'] = user_record['avatar_rootpage'] or group_record.get('rootpage')
                kwargs['locale'] = user_record['locale'] or self.application.config('default?client_locale')
                kwargs['user_name'] = user_record['fullname'] or user_record['username']
                kwargs['user_record'] = user_record
                kwargs['menubag'] = Bag(group_record['custom_menu']).toXml() if group_record else None
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
        
    def useFormlet(self):
        return True
