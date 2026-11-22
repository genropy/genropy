#!/usr/bin/env python
# -*- coding: utf-8 -*-

from werkzeug.wrappers import Response

from gnr.web.gnrbaseclasses import BaseWebtool


class Connector(BaseWebtool):
    """Serve the signed site connector that opens this site in GenroApp.

    The file is issued by Softwell and placed in the site at
    ``genroapp/connector.site``; this tool never signs anything."""

    content_type = 'application/vnd.softwell.connection+json'

    def __call__(self, **kwargs):
        path = self.site.get_genroapp_connector_path()
        if not path:
            return Response('No GenroApp site connector for this site',
                            status=404, mimetype='text/plain')
        self.download_name = f'{self.site.site_name}.site'
        with open(path, 'rb') as f:
            return f.read()
