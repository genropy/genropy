# -*- coding: utf-8 -*-
"""Fallback resolver for the published handbooks site.

The web server serving the static handbooks proxies requests for missing
paths to ``/_tools/docuresolver/<original path>``: pages that moved answer
with a real HTTP 301 to their current absolute URL (the docs host may differ
from the instance host), unknown paths get the same plain 404 page any
unresolvable url of an instance answers with, plus a link back to the index
of the handbook the request came from.

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

from html import escape
from urllib.parse import urlsplit

from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect
from werkzeug.wrappers import Response

from gnr.app.gnrlocalization import AppLocalizer
from gnr.web.gnrbaseclasses import BaseWebtool

BACK_LINK_STYLE = ('display:inline-block;padding:8px 16px;border:1px solid #bbb;'
                   'border-radius:4px;background:#f5f5f5;color:#333;'
                   'text-decoration:none;font-family:sans-serif')


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
        return Response(self.notFoundPage(path), status=404, mimetype='text/html')

    def notFoundPage(self, path):
        """The framework 404 page (werkzeug's, the one every unresolvable url of
        an instance answers with) with a link back to the index of the handbook
        publishing the requested path, so a reader landing on a dead url is one
        click away from the handbook instead of at a dead end"""
        body = NotFound().get_body()
        handbook_url = self.site.db.table('docu.handbook').indexUrlFromRequestPath(path)
        if not handbook_url:
            return body
        translator = AppLocalizer(self.site.gnrapp)
        label = translator.translate('!!Back to handbook') or 'Back to handbook'
        return '%s\n<p><a href="%s" style="%s">%s</a></p>\n' % (body, escape(handbook_url),
                                                                BACK_LINK_STYLE, escape(label))
