#!/usr/bin/env python
# encoding: utf-8

import os
import re
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
                    indexed='y', validate_notnull=True, validate_notnull_error='!!Mandatory field')
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
                    values='invt:Invited,new:New,wait:Waiting,conf:Confirmed,bann:Banned',_sendback=True)
        tbl.column('md5pwd', name_long='!!PasswordMD5', size=':65')
        tbl.column('locale', name_long='!![it]Default locale', size=':12')
        tbl.column('language', size=':2', name_long='!![it]Language').relation('adm.language.code')
        tbl.column('preferences', dtype='X', name_long='!!Preferences')
        tbl.column('menu_root_id' ,size='22')
        tbl.column('avatar_rootpage', name_long='!!Root Page')
        tbl.column('sms_login' ,dtype='B',name_long='!!Sms login')
        tbl.column('sms_number',name_long='!!Sms Number')
        tbl.column('photo',dtype='P', name_long='!![en]Photo')
        tbl.column('group_code',size=':15',name_long='!!Group').relation('group.code',relation_name='users',mode='foreignkey')
        tbl.column('custom_menu', dtype='X', name_long='!!Custom menu')
        tbl.column('custom_fields', dtype='X', name_long='!!Custom fields')
        tbl.column('avatar_secret_2fa', dtype='T',name_long='!![en]Secret 2fa')
        tbl.column('avatar_last_2fa_otp', name_long='Last 2fa')
        tbl.pyColumn('all_tags',name_long='All tags',dtype='A')
        tbl.pyColumn('cover_logo',name_long='Cover logo',dtype='A')
        tbl.pyColumn('square_logo',name_long='Square logo',dtype='A')

        tbl.formulaColumn('other_groups',"array_to_string(ARRAY(#ogr),',')",
                                                select_ogr=dict(columns='$group_code',where='$user_id=#THIS.id',
                                                table='adm.user_group'))
        tbl.formulaColumn('all_groups',"array_to_string(ARRAY(#allgroups),',')",
                                                select_allgroups=dict(columns='$code',
                                                                      where='(@users.id=#THIS.id OR @user_groups.user_id=#THIS.id)',
                                                table='adm.group'))

        tbl.formulaColumn('fullname', """CASE 
                                                WHEN $firstname IS NOT NULL AND $lastname IS NOT NULL THEN $firstname||' '||$lastname
                                                WHEN $lastname IS NOT NULL THEN $lastname
                                        ELSE $username END
                                        """, name_long=u'!!Name',static=True)


    def pyColumn_all_tags(self,record,**kwargs):
        return self.get_all_tags(record)

    def pyColumn_cover_logo(self,record,**kwargs):
        return self.db.application.getPreference('gui_customization.owner.cover_logo',pkg='adm')
    
    def pyColumn_square_logo(self,record,**kwargs):
        return self.db.application.getPreference('gui_customization.owner.square_logo',pkg='adm')
    

    def get_all_tags(self, record=None):
        group_code = self.db.currentEnv.get('current_group_code') or record['group_code']
        alltags = self.db.table('adm.user_tag').query(where='($user_id=:uid OR $group_code=:gc) AND ($require_2fa IS NOT TRUE OR :secret_2fa IS NOT NULL) ',
                                                            uid=record['id'],
                                                            secret_2fa=record['avatar_secret_2fa'],
                                                            gc=group_code,
                                                            columns='$tag_code',distinct=True).fetch()
        tag_list = [r['tag_code'] for r in alltags]
        if group_code:
            tag_list.append(f'grp_{group_code}')
        return ','.join(tag_list)
    
    
    def partitionioning_pkeys(self):
        return None
        
    def createPassword(self):
        password = getUuid()[0:6]
        return password

    def trigger_onUpdating(self, record, old_record=None):
        if old_record['username'] and record['username']!=old_record['username']:
            if not record['username']:
                raise self.exception('protect_update',record=record,
                                message='!!Username cannot be set to null %(username)s')
        if record['md5pwd'] and self.fieldsChanged('md5pwd',record,old_record):
            record['md5pwd'] = self.db.application.changePassword(None, None, record['md5pwd'], userid=record['username'])
        if old_record.get('md5pwd') and not record['md5pwd']:
            raise self.exception('business_logic',msg='Missing password')

    def trigger_onInserted(self, record=None):
        if record.get('group_code'):
            self.checkExternalTable(record)
        if record['status'] == 'invt':
            self.sendInvitationEmail(record)

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
        if record['md5pwd']:
            record['md5pwd'] = self.db.application.changePassword(None, None, record['md5pwd'], userid=record['username'])
 
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
        rows = self.db.table('adm.user_tag').query(where='$user_id=:u_id', u_id=user_id, columns='$tag_code', addPkeyColumn=False).fetch()
        tags = ','.join([r['tag_code'] for r in rows])
        with self.recordToUpdate(user_id) as rec:
            rec['auth_tags']=tags

    def importerStructure(self):
        return dict(fields=dict(firstname='firstname',
                                lastname='lastname',
                                email='email',
                                username='username',
                                group_code='group_code',
                                custom_fields='*'),
                    importer = 'importUsers',
                    mandatories='firstname,username,lastname,email')

   #modo alternativo riga per riga
   # def importerRecordFromRow(self,row):
   #     fields = self.importerStructure()['fields']
   #     row = dict(row)
   #     custom_fields = Bag()
   #     for k,v in row.items():
   #         if k not in fields:
   #             custom_fields[k]=v
   #     row['custom_fields'] = custom_fields
   #     return self.newrecord(**row)
#


    def importUsers(self, rows, **kwargs):
        fields = self.importerStructure()['fields']
        current_users = self.query().fetchAsDict('username')
        rows = list(rows)
        result=Bag()
        warnings=list()
        for r in self.db.quickThermo(rows, labelfield='Adding users'):
            custom_fields = Bag()
            username=r['username']
            if not username:
                username=f"{r['firstname'][0]}{r['lastname']}"
            if username in current_users:
                warnings.append(f'Existing user: {username}')
                continue
            new_user = self.newrecord(username=username)
            for k,v in r.items():
                if k not in fields:
                    custom_fields[k]=v
                else:
                    new_user[k]=v
            new_user['custom_fields']=custom_fields
            self.insert(new_user)
        if warnings:
            result['warnings']=','.join(warnings)
        self.db.commit()
        return result

    @public_method
    def validateNewPassword(self,value,**kwargs):
        if not value:
            return Bag(dict(errorcode='Empty password'))
        password_regex = self.db.application.getPreference('general.password_regex',pkg='adm')
        if password_regex and not re.match(password_regex,value):
            return Bag(dict(errorcode='Invalid new password'))
        return True

    
    def sendInvitationEmail(self,user_record=None,template=None,origin=None,**mailkwargs):
        data = Bag(user_record)
        loginPreference = self.loginPreference()
        tpl_userconfirm_id = loginPreference['tpl_userconfirm_id']
        site = self.db.application.site
        mailservice = site.getService('mail')
        data['link'] = self.db.currentPage.externalUrlToken(origin or site.homepage, 
                                                            assigned_user_id=user_record['id'],
                                                            userid=user_record['id'],max_usages=1)
        data['greetings'] = data['firstname'] or data['lastname']
        email = data['email']
        if template or tpl_userconfirm_id:
            return mailservice.sendUserTemplateMail(record_id=data,template=template,template_id=tpl_userconfirm_id,**mailkwargs)
        else:
            body = loginPreference['confirm_user_tpl'] or 'Dear $greetings to confirm click $link'
            return mailservice.sendmail_template(data,to_address=email,
                                body=body, subject=loginPreference['subject'] or 'Confirm user',
                                **mailkwargs)

    def loginPreference(self):
        loginPreference = Bag(self.db.application.getPreference('general',pkg='adm'))
        custom = self.db.application.getPreference('gui_customization.login',pkg='adm')
        if custom:
            loginPreference.update(custom,ignoreNone=True)
        return loginPreference

    @public_method
    def inviteUser(self, username=None, email=None, group_code=None, 
                            inviting_table=None, inviting_id=None, **kwargs):
        new_user = self.newrecord(username=username, email=email, group_code=group_code, status='invt', **kwargs)
        self.insert(new_user)
        if inviting_table:
            with self.db.table(inviting_table).recordToUpdate(inviting_id) as inviting_rec:
                inviting_rec['user_id'] = new_user['id']
        self.db.commit()
