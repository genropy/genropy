# encoding: utf-8

from datetime import datetime

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('connection', pkey='id', name_long='!!Connection',
                        name_plural='!!Connections',
                        checkpref='adm.dev.connection_log_enabled',
                        retention_policy=('start_ts', 365))
        tbl.column('id', size='22', name_long='!!Connection id')
        tbl.column('userid', size='22', name_long='!!Userid').relation('user.id')
        tbl.column('username', size=':32', name_long='!!Username')
        tbl.column('ip', size=':255', name_long='!!Ip address')
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
        """Close the connections left open that the register no longer knows.

        Their real end is lost with the register: each one is closed at the
        last moment the log itself has of it, the latest start or end of
        its pages, or its own start."""
        with self.db.tempEnv(connectionName='system'):
            pending = self.query(columns='$id,$start_ts', where='$end_ts IS NULL').fetch()
            # the register is read after the log: a connection opened in
            # between is in the register, never mistaken for a lost one
            live_connections = self.db.application.site.register.connections()
            last_seen = {r['id']: r['start_ts'] for r in pending if r['id'] not in live_connections}
            if last_seen:
                pages = self.db.table('adm.served_page').query(
                    columns='$connection_id,$start_ts,$end_ts',
                    where='$connection_id IN :connection_ids',
                    connection_ids=list(last_seen)).fetch()
                for page in pages:
                    seen = [ts for ts in (last_seen[page['connection_id']], page['start_ts'], page['end_ts']) if ts]
                    last_seen[page['connection_id']] = max(seen) if seen else None
            self.db.commit()
        for connection_id, end_ts in last_seen.items():
            self.closeConnection(connection_id, end_ts=end_ts, end_reason='aborted')

    def connectionLog(self, event, connection_id=None, end_ts=None):
        if event == 'open':
            self.openConnection()
        else:
            self.closeConnection(connection_id=connection_id, end_ts=end_ts,
                                 end_reason='expired' if event == 'expire' else 'logout')

    def closableWhere(self, end_reason):
        """The rows of the log, connections or pages, an end with `end_reason`
        may be written on: the first end holds, except that 'aborted' is only
        inferred by the recovery and gives way to the real event if it comes."""
        if end_reason == 'aborted':
            return '$end_ts IS NULL'
        return "($end_ts IS NULL OR $end_reason='aborted')"

    def endUpdater(self, end_ts, end_reason):
        """The batchUpdate callable that ends a row of the log, connection
        or page. The register knows them before the log does, so its last
        ping can precede the start the log has: the end never does."""
        end_ts = end_ts or datetime.now()
        def updater(record):
            record['end_ts'] = max(end_ts, record['start_ts'] or end_ts)
            record['end_reason'] = end_reason
        return updater

    def closeConnection(self, connection_id=None, end_ts=None, end_reason=None):
        connection_id = connection_id or self.db.application.site.currentPage.connection_id
        if isinstance(connection_id,str):
            connection_id = connection_id.split(',')
        with self.db.tempEnv(connectionName='system'):
            self.batchUpdate(self.endUpdater(end_ts, end_reason),
                             where='$id IN :connection_id AND %s' % self.closableWhere(end_reason),
                             connection_id=connection_id)
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
                                    end_ts=None, end_reason=None,
                                     ip=page.request.remote_addr,
                                     user_agent=page.request.get_header('User-Agent'))
        with self.db.tempEnv(connectionName='system'):
            self.insertOrUpdate(new_connection_record)
            self.db.commit()
