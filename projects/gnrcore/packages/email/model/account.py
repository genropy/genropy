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
        input = tbl.colgroup('input', name_long='!!Input parameters')
        input.column('address',name_long='!!Address')
        input.column('full_name',size=':80',name_long='!!Full Name')
        input.column('host',size=':80',name_long='!!Host')
        input.column('port','L',name_long='!!Port')
        input.column('protocol_code',size=':10',name_long='!!TLS').relation('email.protocol.code', mode='foreignkey', relation_name='accounts')
        input.column('tls','B',name_long='!!TLS')
        input.column('ssl','B',name_long='!!SSL')
        input.column('username',size=':80',name_long='!!Username')
        input.column('password',size=':80',name_long='!!Password')
        input.column('last_uid',name_long='!!Last UID')
        output = tbl.colgroup('output', name_long='!!Output parameters')
        output.column('smtp_host',name_long='!!SMTP host')
        output.column('smtp_from_address', name_long='!!From address')
        output.column('smtp_reply_to',name_long='!!Reply to')
        output.column('smtp_username',name_long='!!Smtp username')
        output.column('smtp_password',name_long='!!Smtp password')
        output.column('smtp_port',name_long='!!Smtp port',dtype='L')
        output.column('smtp_timeout',name_long='!!Smtp timeout',dtype='L')
        output.column('smtp_tls',name_long='!!Smtp tls',dtype='B')
        output.column('smtp_ssl',name_long='!!Smtp ssl',dtype='B')
        output.column('send_limit', dtype='L', name_long='!!Sending limit')
        output.column('system_bcc',name_long='!!System bcc')
        output.column('schedulable',dtype='B',name_long='!!Schedulable',name_short='Sched')
        output.column('save_output_message', dtype='B', name_long='!!Save output message')
        output.column('debug_address', name_long='!!Debug address')
    
    
    def getSmtpAccountPref(self,account=None,account_name=None):
        if account:
            account = self.recordAs(account,mode='dict')
        elif account_name:
            account = self.record(where='$account_name=:an',an=account_name).output('dict')
        mp = dict()
        mp['smtp_host'] = account['smtp_host']
        mp['from_address'] = account['smtp_from_address']  
        mp['user'] = account['smtp_username']
        mp['reply_to'] = account['smtp_reply_to'] or self.db.application.getPreference('dflt_noreply',pkg='email')
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

    def trigger_onUpdated(self, record_data,old_record=None):
        mboxtbl = self.db.table('email.mailbox')
        if mboxtbl.query(where='$account_id=:account_id',account_id=record_data['id']).count()==0:
            for i,mbox in enumerate(self.standardMailboxes()):
                mboxtbl.createMbox(mbox,record_data['id'],order=i+1)

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
        msg = mh.build_base_message(subject=subject, body=body)
        if reply_to:
            msg.add_header('reply-to', reply_to)
        try:
            with mh.get_smtp_connection(**account_params) as smtp_connection:
                smtp_connection.sendmail(from_address, to_address, msg.as_string())
                gnrlogger.debug(f'Test message sent successfully')
        except Exception as e:
            gnrlogger.error(f'Error sending test message: {e}')