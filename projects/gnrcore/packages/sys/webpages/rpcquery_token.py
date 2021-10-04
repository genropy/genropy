#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
from gnr.core.gnrbag import Bag
from gnr.web.gnrheadlesspage import GnrHeadlessPage as page_factory

class GnrCustomWebPage(object):    
    skip_connection=True
    def rootPage(self,*args,**kwargs):
        gnrtoken = kwargs['gnrtoken']
        external_token_tbl = self.db.table('sys.external_token')
        userobject_id = external_token_tbl.readColumns(pkey=gnrtoken,columns='$userobject_id')
        if userobject_id:
            method,args,tokekwargs,user_id = external_token_tbl.use_token(gnrtoken)
            tokekwargs.update(kwargs)
            return getattr(self,method)(userobject_id=userobject_id,**tokekwargs)


    def execute(self,userobject_id=None,output='html',**kwargs):
        userobject = self.db.table('adm.userobject').record(userobject_id).output('record')
        data = userobject['data']
        table = userobject['tbl']
        tblobj = self.db.table(table)
        query_pars = data['query_pars'].asDict()
        editable_pars = data['editable_pars']
        query_pars.update(editable_pars.getAttr('where_pars'))
        query_pars.update(editable_pars.getAttr('condition_pars'))
        query_pars.update(editable_pars.getAttr('other_pars'))
        query_pars.update(kwargs)
        env_pars = editable_pars['env_pars'] or {}
        query_where = data['query_where']
        def fillWherePars(n):
            parname = n.attr.get('parname')
            if parname and parname in query_pars:
                n.value = query_pars[parname]
        query_where.walk(fillWherePars)
        query_condition = data['query_condition']
        query_where, query_pars = self.app._decodeWhereBag(tblobj, query_where, query_pars)
        query_where = '{} AND {}'.format(query_where,query_condition) if query_condition else query_where
        with self.db.tempEnv(**env_pars):
            q = tblobj.query(where=query_where,**query_pars)
            s = q.selection(_aggregateRows=True)
        return s.output(output)
    
