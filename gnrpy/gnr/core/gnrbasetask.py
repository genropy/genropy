#!/usr/bin/env python
# encoding: utf-8


class GnrBaseTask(object):
    def __init__(self, page):
        self.page = page
        
    def do(self, parameters = None):
        """ You should implement this"""
        pass
        

def testTask(site_name=None, table_name=None, command=None, parameters=None): # pragma: no cover
    # FIXME: this should be moved to gnr.web, outside
    # of gnr.core, due to its dependency on gnr.web
    from gnr.web.gnrwsgisite import GnrWsgiSite
    from webob import Request, Response
    
    site = GnrWsgiSite(site_name)
    request = Request.blank('/sys/heartbeat')
    response = Response()
    page = site.resource_loader(['sys','heartbeat'], request, response)
    site.db.table('sys.task').runTask(dict(table_name=table_name, command=command, parameters=parameters,log_result=None), page=page)
    site.cleanup()
