#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
from gnr.core.gnrbag import Bag
from gnr.web.gnrheadlesspage import GnrHeadlessPage as page_factory

class GnrCustomWebPage(object):    
    skip_connection=True
    def rootPage(self,*args,**kwargs):
        gnrtoken = kwargs['gnrtoken']
        method,args,tokekwargs,user_id = self.db.table('sys.external_token').use_token(gnrtoken)
        tokekwargs.update(kwargs)
        return getattr(self,method)(**tokekwargs)


    def execute(self,query_table=None,query_where=None,
                    query_condition=None,query_columns=None,query_pars=None,
                    query_envpars=None,
                    name=None,output=None,**kwargs):
        tblobj = self.db.table(query_table)
        query_pars = query_pars.asDict()
        env_pars = query_envpars.asDict()
        if isinstance(query_where, Bag):
            query_pars.pop('where_attr',None)
            query_where, query_pars = self.app._decodeWhereBag(tblobj, query_where, query_pars)
        query_where = '{} AND {}'.format(query_where,query_condition) if query_condition else query_where
        with self.db.tempEnv(**env_pars):
            q = tblobj.query(where=query_where,columns=query_columns,**query_pars)
            s = q.selection()
        return s.output(output)
    
