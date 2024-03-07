# encoding: utf-8
from past.builtins import basestring

from datetime import datetime

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('connection', pkey='id', name_long='!!Connection',
                        name_plural='!!Connections', 
                        checkpref='adm.dev.connection_log_enabled')
        tbl.column('id', size='22', name_long='!!Connection id')
        tbl.column('userid', size='22', name_long='!!Userid').relation('user.id')
        tbl.column('username', size=':32', name_long='!!Username')
        tbl.column('ip', size=':15', name_long='!!Ip number')
        tbl.column('start_ts', 'DH', name_long='!!Start TS')
        tbl.column('end_ts', 'DH', name_long='!!End TS')
        tbl.column('end_reason', size=':12', name_long='!!End reason')
        tbl.column('user_agent', name_long='!!User agent')
        tbl.aliasColumn('user_fullname', relation_path='@userid.fullname', name_long='!!User fullname')


    def trigger_onUpdating(self, record, old_record=None):
        if 'end_ts' in record and record['end_ts']:
            self.db.table('adm.served_page').closePendingPages(connection_id=record['id'],
                                                               end_ts=record['end_ts'],
                                                               end_reason=record['end_reason'])

    
    def dropExpiredConnections(self):
        live_connections = list(self.db.application.site.register.connections().keys())
        ts = datetime.now()
        with self.db.tempEnv(connectionName='system'):
            updatedKeys = self.batchUpdate(dict(end_ts=ts,end_reason='aborted'),
                            where="$id NOT IN :live_connections AND $end_ts IS NULL",
                            live_connections=live_connections)
            if updatedKeys:
                self.db.commit()


    def getPendingConnections(self, userid=None):
        where = '$end_ts IS NULL'
        if userid:
            where = '%s AND %s' % ('$userid=:userid', where)
        return self.query(where=where, userid=userid).fetch()

    def closePendingConnections(self, end_ts=None, end_reason=None):
        end_ts = end_ts or datetime.now()
        for conn in self.getPendingConnections():
            self.closeConnection(conn['id'], end_ts=end_ts, end_reason=end_reason)

    def connectionLog(self, event, connection_id=None):
        if event == 'open':
            self.openConnection()
        else:
            self.closeConnection(connection_id=connection_id, end_reason='logout')

    def closeConnection(self, connection_id=None, end_ts=None, end_reason=None):
        page = self.db.application.site.currentPage
        connection_id = connection_id or page.connection_id
        if isinstance(connection_id,basestring):
            connection_id = connection_id.split(',')
        with self.db.tempEnv(connectionName='system'):
            self.batchUpdate(dict(end_ts=end_ts or datetime.now(), end_reason=end_reason),
                             where='$id IN :connection_id', connection_id=connection_id)
            self.db.commit()


    def openConnection(self):
        page = self.db.application.site.currentPage
        avatar = page.avatar
        userid = avatar.user_id if avatar.user_id!=avatar.user else None
        username = None
        if userid:
            username = avatar.user
        new_connection_record = dict(id=page.connection_id, 
                                    username=username,userid=userid,
                                    start_ts=datetime.now(),
                                     ip=page.request.remote_addr,
                                     user_agent=page.request.get_header('User-Agent'))
        with self.db.tempEnv(connectionName='system'):
            self.insertOrUpdate(new_connection_record)
            self.db.commit()
