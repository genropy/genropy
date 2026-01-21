# encoding: utf-8
from gnr.lib.services.mail import MailService
from gnr.core.gnrdecorator import public_method
from gnr.app import logger as gnrlogger

class Table(object):

    def config_db(self, pkg):
        tbl =  pkg.table('account', rowcaption='$account_name', caption_field='account_name',
                            pkey='id', name_long='!!Account', name_plural='!!Account')
        self.sysFields(tbl)
        tbl.column('account_name',name_long='!!Account Name',unique=True)
        tbl.column('address',name_long='!!Address')
        tbl.column('full_name',size=':80',name_long='!!Full Name')
        tbl.column('host',size=':80',name_long='!!Host')
        tbl.column('port','L',name_long='!!Port')
        tbl.column('protocol_code',size=':10',name_long='!!TLS').relation('email.protocol.code', mode='foreignkey', relation_name='accounts')
        tbl.column('tls','B',name_long='!!TLS')
        tbl.column('ssl','B',name_long='!!SSL')
        tbl.column('username',size=':80',name_long='!!Username')
        tbl.column('password',size=':80',name_long='!!Password')
        tbl.column('last_uid',name_long='!!Last UID')
        tbl.column('smtp_host',name_long='!!SMTP host')
        tbl.column('smtp_from_address',name_long='!!From address')
        tbl.column('smtp_reply_to',name_long='!!Reply to', validate_email=True)
        tbl.column('smtp_username',name_long='!!Smtp username')
        tbl.column('smtp_password',name_long='!!Smtp password')
        tbl.column('smtp_port',name_long='!!Smtp port',dtype='L')
        tbl.column('smtp_timeout',name_long='!!Smtp timeout',dtype='L')
        tbl.column('smtp_tls',name_long='!!Smtp tls',dtype='B')
        tbl.column('smtp_ssl',name_long='!!Smtp ssl',dtype='B')
        tbl.column('send_limit', dtype='L', name_long='!!Sending limit')
        tbl.column('system_bcc',name_long='!!System bcc')
        tbl.column('use_mailproxy', dtype='B', name_long='!![en]Use mail proxy')
        tbl.column('proxy_ttl', dtype='L', name_long='!!Proxy connection TTL (seconds)', default=300)
        tbl.column('proxy_limit_per_minute', dtype='L', name_long='!!Proxy limit per minute')
        tbl.column('proxy_limit_per_hour', dtype='L', name_long='!!Proxy limit per hour')
        tbl.column('proxy_limit_per_day', dtype='L', name_long='!!Proxy limit per day')
        tbl.column('proxy_limit_behavior', size=':20', name_long='!!Proxy limit behavior', default='defer')
        tbl.column('proxy_batch_size', dtype='L', name_long='!!Proxy batch size')

        tbl.column('schedulable',dtype='B',name_long='!!Schedulable',name_short='Sched')
        tbl.column('save_output_message', dtype='B', name_long='!!Save output message')
        tbl.column('debug_address', name_long='!!Debug address')
    
    def getSmtpAccountPref(self,account=None,account_name=None):
        if account:
            account = self.recordAs(account,mode='dict')
        elif account_name:
            account = self.record(where='$account_name=:an',an=account_name).output('dict')
        mp = dict()
        mp['smtp_host'] = account['smtp_host']
        mp['from_address'] = account['smtp_from_address']
        mp['user'] = account['smtp_username']
        mp['reply_to'] = account['smtp_reply_to'] or self.db.application.getPreference('dflt_reply_to',pkg='email')
        mp['password'] = account['smtp_password']
        mp['port'] = account['smtp_port']
        mp['ssl'] = account['smtp_ssl']
        mp['tls'] = account['smtp_tls']
        mp['system_bcc'] = account['system_bcc']
        mp['system_debug_address'] = account['debug_address']
        mp['scheduler'] = account['save_output_message']
        return mp
        
    def standardMailboxes(self):
        return ('Inbox','Outbox','Draft','Trash')
        
    def trigger_onInserted(self, record_data):
        mboxtbl = self.db.table('email.mailbox')
        for i,mbox in enumerate(self.standardMailboxes()):
            mboxtbl.createMbox(mbox,record_data['id'],order=i+1)
        if record_data.get('use_mailproxy'):
            self._sync_account_to_mailproxy(record_data)

    def trigger_onUpdated(self, record_data, old_record=None):
        mboxtbl = self.db.table('email.mailbox')
        if mboxtbl.query(where='$account_id=:account_id',account_id=record_data['id']).count()==0:
            for i,mbox in enumerate(self.standardMailboxes()):
                mboxtbl.createMbox(mbox,record_data['id'],order=i+1)
        if self.fieldsChanged('use_mailproxy', record_data, old_record):
            if record_data.get('use_mailproxy'):
                self._sync_account_to_mailproxy(record_data)
            else:
                self._remove_account_from_mailproxy(record_data)

    def trigger_onDeleted(self, record_data):
        if record_data.get('use_mailproxy'):
            self._remove_account_from_mailproxy(record_data)

    def _get_mailproxy_service(self):
        """Get mailproxy service if configured and registered.

        Returns:
            service instance

        Raises:
            Exception: If service is not configured or not registered
        """
        service = self.db.application.site.getService('mailproxy')
        if not service or not service.proxy_url:
            raise self.exception('business_logic',
                msg='Mailproxy service is not configured')
        if not service.tenant_registered:
            raise self.exception('business_logic',
                msg='Mailproxy service is not activated')
        return service

    def _sync_account_to_mailproxy(self, record_data):
        """Sync account to mailproxy service."""
        service = self._get_mailproxy_service()
        try:
            service.add_account(record_data['id'])
        except Exception as e:
            gnrlogger.error(f'Failed to sync account to mailproxy: {e}')

    def _remove_account_from_mailproxy(self, record_data):
        """Remove account from mailproxy service."""
        service = self._get_mailproxy_service()
        try:
            service.delete_account(record_data['id'])
        except Exception as e:
            gnrlogger.error(f'Failed to remove account from mailproxy: {e}')


    def partitionioning_pkeys(self):
        where='@account_users.user_id=:env_user_id OR @account_users.id IS NULL'
        return [r['pkey'] for r in self.query(where=where,excludeLogicalDeleted=False).fetch()]

    @public_method
    def sendEmailFromParams(self, host=None, from_address=None, to_address=None, reply_to=None, subject=None, body=None,
                                username=None, password=None, tls=None, ssl=None, port=None, **kwargs):
        account_params = dict(smtp_host=host, port=port, user=username, password=password, ssl=ssl, tls=tls, **kwargs)
        mh = MailService()
        subject = subject or 'This is a test message'
        body = body or f'This is a test message from {from_address} to {to_address}'
        reply_to = reply_to or self.db.application.getPreference('dflt_reply_to',pkg='email')
        msg = mh.build_base_message(subject=subject, body=body)
        if reply_to:
            msg.add_header('reply-to', reply_to)
        try:
            smtp_connection = mh.get_smtp_connection(**account_params)
            smtp_connection.sendmail(from_address, to_address, msg.as_string())
            smtp_connection.close()
            gnrlogger.debug(f'Test message sent successfully')
        except Exception as e:
            gnrlogger.error(f'Error sending test message: {e}')
            raise

