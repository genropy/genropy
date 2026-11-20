#!/usr/bin/env python
# -*- coding: utf-8 -*-

from werkzeug.wrappers import Response

from gnr.web.gnrbaseclasses import BaseWebtool


class Rundoc(BaseWebtool):
    """Serve the signed RunDoc that opens this site in GenroApp.

    The file is issued by Softwell and placed in the site at
    ``genroapp/connection.rundoc``; this tool never signs anything."""

    content_type = 'application/vnd.softwell.connection+json'

    def __call__(self, **kwargs):
        path = self.site.get_genroapp_rundoc_path()
        if not path:
            return Response('No GenroApp connection file for this site',
                            status=404, mimetype='text/plain')
        self.download_name = f'{self.site.site_name}.rundoc'
        with open(path, 'rb') as f:
            return f.read()
