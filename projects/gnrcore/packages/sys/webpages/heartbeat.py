#!/usr/bin/env python
# encoding: utf-8

class GnrCustomWebPage(object):
    is_heartbeat=True
    system_page=True

    def rootPage(self,*args, **kwargs):
        self.response.content_type = 'application/xml'
        request_method = self.request.method
        self.db.table('sys.task').runScheduled(self)

