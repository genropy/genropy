#!/usr/bin/env python
# encoding: utf-8
from builtins import object
import os
from gnr.core.gnrdecorator import metadata, public_method
from gnr.core.gnrlang import getUuid
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('user', pkey='id', name_long='!!User', rowcaption='username,email:%s (%s)',
            caption_field='username', tabletype='main')
        self.sysFields(tbl, ins=True, upd=True, md5=True)
        tbl.column('id', size='22', group='_', readOnly='y', name_long='Id')
        tbl.column('username', size=':32', name_long='!!Username', unique='y', _sendback=True,
                   indexed='y', validate_notnull=True, validate_notnull_error='!!Mandatory field',
                   unmodifiable=True)
        tbl.column('email', name_long='Email', validate_notnull=True,
                   validate_notnull_error='!!Mandatory field')

        tbl.column('mobile', name_long='Mobile')

        tbl.column('firstname', name_long='!!First name',
                   validate_notnull=True, validate_case='c', validate_notnull_error='!!Mandatory field')
        tbl.column('lastname', name_long='!!Last name',
                   validate_notnull=True, validate_case='c', validate_notnull_error='!!Mandatory field')
        tbl.column('registration_date', 'D', name_long='!!Registration Date')
        tbl.column('auth_tags', name_long='!!Authorization Tags')
        tbl.column('status', name_long='!!Status', size=':4',
                   values='new:New,wait:Waiting,conf:Confirmed,bann:Banned',_sendback=True)
        tbl.column('md5pwd', name_long='!!PasswordMD5', size=':65')
        tbl.column('locale', name_long='!!Default Language', size=':12')
        tbl.column('preferences', dtype='X', name_long='!!Preferences')
        tbl.column('menu_root_id' ,size='22')
        tbl.column('avatar_rootpage', name_long='!!Root Page')
        tbl.column('sms_login' ,dtype='B',name_long='!!Sms login')
        tbl.column('sms_number',name_long='!!Sms Number')
        tbl.column('group_code',size=':15',name_long='!!Group').relation('group.code',relation_name='users',mode='foreignkey')
         
        tbl.column('custom_menu', dtype='X', name_long='!!Custom menu')
        tbl.column('custom_fields', dtype='X', name_long='!!Custom fields')
        tbl.pyColumn('all_tags',name_long='All tags',dtype='A')

        tbl.formulaColumn('fullname', "$firstname||' '||$lastname", name_long=u'!!Name')


    def pyColumn_all_tags(self,record,**kwargs):
        return self.get_all_tags(record)

    
    def get_all_tags(self, record=None):
        alltags = self.db.table('adm.user_tag').query(where='$user_id=:uid OR $group_code=:gc',
                                                            uid=record['id'],
                                                            gc=record['group_code'],
                                                            columns='$tag_code',distinct=True).fetch()
        return ','.join([r['tag_code'] for r in alltags])
    
    
    def partitionioning_pkeys(self):
        return None
        
    def createPassword(self):
        password = getUuid()[0:6]
        return password

    def trigger_onUpdating(self, record, old_record=None):
        if record['username']!=old_record['username']:
            raise self.exception('protect_update',record=record,
                                 msg='!!Username is not modifiable %(username)s')
        self.passwordTrigger(record)
        if old_record.get('md5pwd') and not record['md5pwd']:
            raise self.exception('business_logic',msg='Missing password')

    def trigger_onInserted(self, record=None):
        if record['group_code']:
            self.checkExternalTable(record)

    def trigger_onUpdated(self,record=None,old_record=None):
        if self.fieldsChanged('preferences',record,old_record):
            self.db.application.pkgBroadcast('onSavedUserPreferences',preferences=record['preferences'])
            pref_key = '%s_preference' %record['username']
            self.db.application.cache.updatedItem(pref_key)
            site = getattr(self.db.application,'site',None)
            if site and site.currentPage:
                site.currentPage.setInClientData('gnr.serverEvent.refreshNode', value='gnr.user_preference', filters='*',
                             fired=True, public=True)
        if self.fieldsChanged('group_code,auth_tags', record, old_record):
            self.checkExternalTable(record)


    def checkExternalTable(self, record=None):
        all_tags = self.get_all_tags(record)
        
        linked_tables = self.db.table('adm.htag').query(where='$hierarchical_code IN :all_tags AND $linked_table IS NOT NULL', 
                                                        columns='$linked_table', addPkeyColumn=False, 
                                                        distinct=True, all_tags=all_tags.split(',')).fetch()
        
        for lt in linked_tables:
            handler = getattr(self.db.table(lt['linked_table']), 'onUserChanges', None)
            if handler:
                handler(record)


    def trigger_onInserting(self, record, **kwargs):
        self.passwordTrigger(record)

    def passwordTrigger(self, record):
        if record.get('md5pwd'):
            password = record['md5pwd']
            if len(password) < 32 and record['status']=='conf':
                record['md5pwd'] = self.db.application.changePassword(None, None, password, userid=record['username'])
                
    def populate(self, fromDump=None):
        if fromDump:
            dump_folder = os.path.join(self.db.application.instanceFolder, 'dumps')
            self.importFromXmlDump(dump_folder)

    def getPreference(self, path=None, pkg=None, dflt=None, username=None):
        pref_key = '%s_preference' %username
        result = self.db.application.cache.getItem(pref_key)
        if not result:
            result = self.loadRecord(username)['preferences']
            self.db.application.cache.setItem(pref_key, result)
        result = result.deepcopy() if result else Bag()
        if result and path != '*':
            result = result['%s.%s' % (pkg, path)]
        return result or dflt

    def setPreference(self, path='', data='', pkg='', username=''):
        with self.db.tempEnv(connectionName='system',storename=self.db.rootstore):
            with self.recordToUpdate(username=username) as rec:
                rec['preferences.%s.%s' % (pkg, path)] = data
            self.db.commit()

    def loadRecord(self, username, for_update=False):
        try:
            record = self.record(username=username, for_update=for_update).output('record')
        except:
            record = Bag()
        return record



    def syncExternalUser(self,externalUser):
        with self.db.tempEnv(connectionName='system',storename=self.db.rootstore):
            docommit = False
            user_record = self.record(username=externalUser['username'],ignoreMissing=True,for_update=True).output('dict')
            if user_record.get('id'):
                if self.fieldsChanged('firstname,lastname,email',externalUser,user_record):
                    old_record = dict(user_record)
                    user_record.update(externalUser)
                    self.update(user_record,old_record)
                    docommit = True
            else:
                user_record = dict(externalUser)
                self.insert(user_record)
                docommit = True
            if docommit:
                self.db.commit()


    def onChangedTags(self, user_id=None, **kwargs):
        rows = self.query(where='$user_id=:u_id', u_id=user_id, columns='$tag_code', addPkeyColumn=False).fetch()
        tags = ','.join([r['tag_code'] for r in rows])
        with self.recordToUpdate(user_id) as rec:
            rec['auth_tags']=tags

    def importerStructure(self):
        return dict(fields=dict(firstname='firstname',
                                lastname='lastname',
                                email='email',
                                username='username',
                                group_code='group_code',
                                extra_data='*'),
                    importer = 'importUsers',
                    mandatories='firstname,username,lastname,email')

   #modo alternativo riga per riga
   # def importerRecordFromRow(self,row):
   #     fields = self.importerStructure()['fields']
   #     row = dict(row)
   #     extra_data = Bag()
   #     for k,v in row.items():
   #         if k not in fields:
   #             extra_data[k]=v
   #     row['extra_data'] = extra_data
   #     return self.newrecord(**row)
#


    def importUsers(self, reader, **kwargs):
        fields = self.importerStructure()['fields']
        current_users = self.query().fetchAsDict('username')
        rows = list(reader())
        result=Bag()
        warnings=list()
        for r in self.db.quickThermo(rows, labelfield='Adding users'):
            extra_data = Bag()
            username=r['username']
            if not username:
                username=f"{r['firstname'][0]}{r['lastname']}"
            if username in current_users:
                warnings.append(f'Existing user: {username}')
                continue
            new_user = self.newrecord(username=username)
            for k,v in r.items():
                if k not in fields:
                    extra_data[k]=v
                else:
                    new_user[k]=v
            new_user['extra_data']=extra_data
            self.insert(new_user)
        if warnings:
            result['warnings']=','.join(warnings)
        self.db.commit()
        return result