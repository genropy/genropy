# encoding: utf-8
from builtins import object

import pytz
from datetime import datetime as dt
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('external_token', pkey='id', name_long='!!External Token',
                        name_plural='!!External Tokens')
        tbl.column('id', size='22', name_long='!!id')
        tbl.column('datetime', 'DHZ', name_long='!!Date and Time')
        tbl.column('expiry', 'DHZ', name_long='!!Expiry')
        tbl.column('allowed_user', size=':32', name_long='!!Destination user')
        tbl.column('connection_id', size='22', name_long='!!Connection Id', indexed=True).relation('adm.connection.id')
        tbl.column('max_usages', 'I', name_long='!!Max uses')
        tbl.column('allowed_host', name_long='!!Allowed host')
        tbl.column('page_path', name_long='!!Page path')
        tbl.column('method', name_long='!!Method')
        tbl.column('assigned_user_id',size='22', group='_', name_long='Assigned user id'
                    ).relation('adm.user.id', relation_name='assigned_tokens', mode='foreignkey',
                                onDelete='cascade',deferred=True)
        tbl.column('parameters', dtype='X', name_long='!!Parameters')
        tbl.column('exec_user', size=':32', name_long='!!Execute as user').relation('adm.user.username')
        tbl.column('userobject_id',size='22', group='_', name_long='Userobject'
                    ).relation('adm.userobject.id', relation_name='tokens', mode='foreignkey', onDelete='cascade')
        tbl.pyColumn('external_url',)

    def pyColumn_external_url(self,record=None,**kwargs):
        return self.db.currentPage.externalUrl(record['page_path'], gnrtoken=record['id'])

    def create_token(self, page_path=None, expiry=None, allowed_host=None, 
                        allowed_user=None,connection_id=None, 
                        max_usages=None, method=None, datetime=None,
                        parameters=None, exec_user=None,userobject_id=None,assigned_user_id=None):
        record = self.newrecord(
                page_path=page_path,
                datetime= datetime or dt.now(pytz.utc),
                expiry=expiry,
                allowed_host=allowed_host,
                allowed_user=allowed_user,
                connection_id=connection_id,
                max_usages=max_usages,
                method=method,
                exec_user=exec_user,
                userobject_id=userobject_id,
                assigned_user_id=assigned_user_id,
                parameters=Bag(parameters))
        self.insert(record)
        return record['id']

    def use_token(self, token, host=None):
        with self.db.tempEnv(connectionName='system',storename=self.db.rootstore):
            record = self.record(id=token, ignoreMissing=True).output('bag')
            record = self.check_token(record, host)
            if record:
                if record['max_usages']:
                    self.db.table('sys.external_token_use').insert(
                            dict(external_token_id=record['id'], host=host, datetime=dt.now(pytz.utc)))
                    self.db.commit()
                user = record['exec_user']
                return record['method'], [], dict(record['parameters'] or {}), user
        return None, None, None, None

    def check_token(self, record, host=None):
        record = self.recordAs(record,'dict')
        if not record:
            return False
        if host:
            pass
        if record['expiry'] and record['expiry'] < dt.now(pytz.utc):
            return False
        if record['max_usages']:
            uses = self.db.table('sys.external_token_use').query(where='$external_token_id =:cid',
                                                                 cid=record['id']).count()
            if uses >= record['max_usages']:
                return False
        return record
        

    def expand_token_url(self,gnrtoken):
        valid_token_record = self.check_token(gnrtoken)
        if not valid_token_record:
            raise self.exception('business_logic',msg='Invalid token')

    def authenticatedUser(self,token):
        token_record = self.check_token(token)
        if token_record and token_record.get('exec_user'):
            user = token_record.get('exec_user')
            if not user:
                return None
            if token_record['max_usages']:
                self.use_token(token_record['id'])
            return user