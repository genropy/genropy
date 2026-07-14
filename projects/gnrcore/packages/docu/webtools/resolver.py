# -*- coding: utf-8 -*-
"""Fallback resolver for the published handbooks site.

The web server serving the static handbooks proxies requests for missing
paths to ``/_tools/docuresolver/<original path>``: pages that moved answer
with a real HTTP 301 to their current URL, unknown paths get a branded 404
page consistent with the handbooks theme preferences.
"""

from html import escape

from werkzeug.utils import redirect
from werkzeug.wrappers import Response

from gnr.web.gnrbaseclasses import BaseWebtool

NOT_FOUND_TPL = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Page not found</title>
    <style>
        body{{font-family:'Lato','Helvetica Neue',Arial,sans-serif;
             background:#edf0f2;color:#404040;margin:0;}}
        .card{{max-width:560px;margin:12vh auto 0;padding:40px;
              background:#fff;border-top:3px solid #2980B9;
              box-shadow:0 1px 3px rgba(0,0,0,.15);text-align:center;}}
        .card img{{max-height:80px;margin-bottom:24px;}}
        h1{{font-size:1.6em;margin:0 0 12px;}}
        code{{background:#f3f6f6;padding:2px 6px;word-break:break-all;}}
        a{{color:#2980B9;text-decoration:none;}}
        .footer{{margin-top:32px;font-size:.8em;color:#9b9b9b;}}
    </style>
</head>
<body>
    <div class="card">
        {logo}
        <h1>Page not found</h1>
        <p>The page <code>/{path}</code> does not exist or has been removed.</p>
        <p><a href="{home_url}">Go to the documentation home</a></p>
        {footer}
    </div>
</body>
</html>"""


class DocuResolver(BaseWebtool):
    content_type = 'text/html'

    def __call__(self, *args, **kwargs):
        path = '/'.join(args)
        location = self.site.db.table('docu.documentation').resolveRequestPath(path)
        if location:
            return redirect(location, code=301)
        return Response(self.notFoundPage(path), status=404, mimetype='text/html')

    def notFoundPage(self, path):
        """Branded 404 page built from the docu package preferences"""
        getPreference = self.site.db.application.getPreference
        theme = getPreference('.handbooks_theme', pkg='docu') or {}
        home_url = getPreference('.sphinx_baseurl', pkg='docu') or '/'
        logo = theme.get('logo')
        logo_chunk = ''
        if logo:
            logo_chunk = '<img src="%s" alt="logo"/>' % escape(self.site.externalUrl(logo), quote=True)
        footer_chunk = ''
        if theme.get('copyright'):
            footer_chunk = '<div class="footer">&copy; %s</div>' % escape(theme['copyright'])
        return NOT_FOUND_TPL.format(logo=logo_chunk,
                                    path=escape(path),
                                    home_url=escape(home_url, quote=True),
                                    footer=footer_chunk)
