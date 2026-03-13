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
        tbl.formulaColumn('detail_url',
                          """(CASE WHEN $request_host IS NULL THEN '/sys/ep_error?error_id=' || $id 
                                ELSE $request_host || '/sys/ep_error?error_id=' || $id
                             END)
                            """,
                          name_long='!!Detail')
        tbl.column('request_uri',name_long='!!Request URI')
        tbl.column('request_host',name_long='!!Request Host')

        tbl.column('rpc_method',name_long='!!RPC Method')
        tbl.column('rpc_kwargs',dtype='X',name_long='!!RPC kwargs')
        tbl.column('page_id',name_long='!!Page ID',size='22')
        tbl.column('current_domain',name_long='!!Current domain')


    def errorHandler(self, error_id=None, description=None, traceback=None,
                     error_type=None, user=None, user_ip=None,
                     user_agent=None, request_uri=None,
                     rpc_method=None, page_id=None, domain=None, **kwargs):
        rec = dict(error_code=error_id, description=description,
                   error_data=traceback, error_type=error_type,
                   username=user, user_ip=user_ip,
                   user_agent=user_agent, request_uri=request_uri,
                   rpc_method=rpc_method, page_id=page_id,
                   domain=domain)
        with self.db.tempEnv(connectionName='system',
                             storename=self.db.rootstore):
            self.insert(rec)
            self.db.commit()
        return rec

