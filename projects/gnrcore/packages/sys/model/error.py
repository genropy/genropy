#!/usr/bin/env python
# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('error', pkey='id', name_long='Debug Error',
                        name_plural='!!Errors', caption_field='description',
                        rowcaption='$error_type,$description',
                        retention_policy=('__ins_ts', 60)
                        )
        self.sysFields(tbl)
        tbl.column('description',name_long='!!Description')
        tbl.column('error_data',dtype='X',name_long='!!Traceback')

        tbl.column('username',name_long='User')
        tbl.column('user_ip',name_long='User ip')

        tbl.column('user_agent',name_long='User agent')

        tbl.column('fixed',name_long='Fixed')
        tbl.column('notes',name_long='Notes')
        tbl.column('error_type',name_long='!!Error type')
        tbl.column('error_code',name_long='!!Error code',indexed=True)


    def errorHandler(self, error_id=None, description=None, traceback=None,
                     error_type=None, user=None, user_ip=None,
                     user_agent=None):
        rec = dict(error_code=error_id, description=description,
                   error_data=traceback, error_type=error_type,
                   username=user, user_ip=user_ip,
                   user_agent=user_agent)
        with self.db.tempEnv(connectionName='system',
                             storename=self.db.rootstore):
            self.insert(rec)
            self.db.commit()
        return rec

