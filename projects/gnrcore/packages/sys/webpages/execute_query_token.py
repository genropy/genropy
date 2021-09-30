#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.web.gnrheadlesspage import GnrHeadlessPage as page_factory

class GnrCustomWebPage(object):    
    skip_connection=True
    def rootPage(self,*args,**kwargs):
        gnrtoken = kwargs['gnrtoken']
        method,args,tokekwargs,user_id = self.db.table('sys.external_token').use_token(gnrtoken)
        tokekwargs.update(kwargs)
        return getattr(self,method)(**tokekwargs)


    def execute(self,query_table=None,query_pars=None,name=None,output=None,**kwargs):
        q = self.db.table(query_table).query(**query_pars.asDict())
        s = q.selection()
        print(x)
        return s.output(output)
    
