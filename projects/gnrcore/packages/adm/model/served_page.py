# encoding: utf-8

from datetime import datetime

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('served_page', pkey='page_id', name_long='!!Served page',
                        name_plural='!!Served pages',
                        checkpref='adm.dev.connection_log_enabled',
                        retention_policy=('start_ts', 365))
        tbl.column('page_id', size='22', name_long='!!Page id')
        tbl.column('pagename', name_long='!!Page name')
        tbl.column('page_url', name_long='!!Page url')
        tbl.column('parent_page_id', size='22', group='_', name_long='!!Parent page id')
        tbl.column('root_page_id', size='22', group='_', name_long='!!Root page id')
        tbl.column('connection_id', size='22', group='_').relation('connection.id', mode='foreignkey',relation_name='pages',
                                                                   onDelete='cascade')
        tbl.column('start_ts', 'DH', name_long='!!Start ts')
        tbl.column('end_ts', 'DH', name_long='!!End ts')
        tbl.column('end_reason', size=':12', name_long='!!End Reason')

    def getLivePages(self, connection_id=None, current_page_id=None):
        where = ['$end_ts is null']
        if connection_id:
            where.append('$connection_id=:connection_id')
        if current_page_id:
            where.append('$page_id!=:current_page_id')
        return self.query(where=' AND '.join(where),
                          connection_id=connection_id,
                          current_page_id=current_page_id).fetch()


    def pageLog(self, event, page_id=None, end_ts=None):
        if event == 'open':
            self.openServedPage()
        else:
            self.closeServedPage(page_id=page_id, end_ts=end_ts,
                                 end_reason='expired' if event == 'expire' else 'unload')

    def closePendingPages(self, connection_id=None, end_ts=None, end_reason=None):
        """Close the pages of a connection being closed, in its transaction:
        a commit here would release the lock on the connection before its
        own end is written."""
        connection_tbl = self.db.table('adm.connection')
        self.batchUpdate(connection_tbl.endUpdater(end_ts, end_reason),
                         where='$connection_id=:connection_id AND %s' % connection_tbl.closableWhere(end_reason),
                         connection_id=connection_id)

    def openServedPage(self):
        page = self.db.application.site.currentPage
        record_served_page = dict(page_id=page.page_id, end_reason=None, end_ts=None,
                                  connection_id=page.connection_id,
                                  start_ts=datetime.now(), pagename=page.basename,
                                  page_url=page.request.path_info,
                                  parent_page_id=page.parent_page_id,
                                  root_page_id=page.root_page_id)
        with self.db.tempEnv(connectionName='system'):
            self.insertOrUpdate(record_served_page)
            self.db.commit()

    def closeServedPage(self, page_id=None, end_ts=None, end_reason=None):
        page_id = page_id or self.db.application.site.currentPage.page_id
        connection_tbl = self.db.table('adm.connection')
        with self.db.tempEnv(connectionName='system'):
            self.batchUpdate(connection_tbl.endUpdater(end_ts, end_reason),
                             where='$page_id=:page_id AND %s' % connection_tbl.closableWhere(end_reason),
                             page_id=page_id)
            self.db.commit()
