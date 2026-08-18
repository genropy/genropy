# -*- coding: utf-8 -*-
"""Fallback resolver for the published handbooks site.

The web server serving the static handbooks proxies requests for missing
paths to ``/_tools/docuresolver/<original path>``: pages that moved answer
with a real HTTP 301 to their current URL, unknown paths get the standard
framework 404 page (``html_pages/missing_result.html``), overridable per
instance through the ordinary resource cascade.
"""

from werkzeug.utils import redirect
from werkzeug.wrappers import Response

from gnr.web.gnrbaseclasses import BaseWebtool


class DocuResolver(BaseWebtool):
    content_type = 'text/html'

    def __call__(self, *args, **kwargs):
        path = '/'.join(args)
        location = self.site.db.table('docu.documentation').resolveRequestPath(path)
        if location:
            return redirect(location, code=301)
        return Response(self.notFoundPage(), status=404, mimetype='text/html')

    def notFoundPage(self):
        """Body of the framework 404 page, resolved through the resource cascade"""
        template_path = self.site.resource_loader.getResource(
            'html_pages/missing_result.html', pkg='docu')
        if not template_path:
            return 'Page not found'
        with open(template_path) as template_file:
            return template_file.read()
