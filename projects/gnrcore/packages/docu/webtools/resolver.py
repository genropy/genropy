# -*- coding: utf-8 -*-
"""Fallback resolver for the published handbooks site.

The web server serving the static handbooks proxies requests for missing
paths to ``/_tools/docuresolver/<original path>``: pages that moved answer
with a real HTTP 301 to their current absolute URL (the docs host may differ 
from the instance host), unknown paths get the standard framework 404 page
(``html_pages/missing_result.html``), overridable per instance through the
ordinary resource cascade.

Without that proxy rule nothing catches the old URLs and they simply 404, so
the web server publishing the handbooks needs the miss routed here, e.g. with
nginx::

    server {
        root /path/to/published/handbooks;

        location / {
            try_files $uri $uri/ $uri.html @docuresolver;
        }

        location @docuresolver {
            proxy_pass http://127.0.0.1:8080/_tools/docuresolver$uri;
            proxy_set_header Host $host;
        }
    }
"""

from urllib.parse import urlsplit

from werkzeug.utils import redirect
from werkzeug.wrappers import Response

from gnr.app.gnrlocalization import AppLocalizer
from gnr.web.gnrbaseclasses import BaseWebtool


class DocuResolver(BaseWebtool):

    def __call__(self, *args, **kwargs):
        path = '/'.join(args)
        location = self.site.db.table('docu.documentation').resolveRequestPath(path)
        if location:
            if not urlsplit(location).netloc:
                # the docs host differs from the instance host: the Location
                # header must be absolute, so a still-relative url (no
                # docu.sphinx_baseurl preference) falls back on the instance
                # host, the same base the sphinx export publishes with
                location = self.site.externalUrl(location)
            return redirect(location, code=301)
        return Response(self.notFoundPage(), status=404, mimetype='text/html')

    def notFoundPage(self):
        """Body of the framework 404 page, resolved through the resource cascade"""
        template_path = self.site.getResource('html_pages/missing_result.html',
                                              pkg='docu')
        if not template_path:
            # no framework page and no instance override: the route still has to
            # answer something readable rather than an empty 404 body
            translator = AppLocalizer(self.site.gnrapp)
            return translator.translate('!!Page not found') or 'Page not found'
        with open(template_path) as template_file:
            return template_file.read()
