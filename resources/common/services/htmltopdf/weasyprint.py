# -*- coding: utf-8 -*-

import functools
import logging
import os
import subprocess
import tempfile
import threading
from urllib.parse import urlsplit
from weasyprint import CSS, HTML, default_url_fetcher

from gnr.lib.services.htmltopdf import HtmlToPdfService

logger = logging.getLogger('gnr.htmltopdf.weasyprint')

#metric-compatible with Arial Narrow, as fontconfig's 30-metric-aliases.conf pairs them
NARROW_FAMILIES = ('arial narrow', 'liberation sans narrow', 'helvetica narrow',
                   'nimbus sans narrow', 'tex gyre heros cn')
FC_MATCH_TIMEOUT = 5

_narrow_font_lock = threading.Lock()


@functools.cache
def _warn_narrow_font_fallback():
    try:
        result = subprocess.run(['fc-match', '--format=%{family}', 'Arial Narrow'],
                                capture_output=True, encoding='utf-8', errors='replace',
                                timeout=FC_MATCH_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return
    families = [family.strip() for family in result.stdout.split(',') if family.strip()]
    if result.returncode or not families or \
            any(family.lower() in NARROW_FAMILIES for family in families):
        return
    logger.warning('Arial Narrow, the default print font, is not installed: fontconfig '
                   'replaces it with %s, which is wider, so print text overflows its boxes. '
                   'Install fonts-liberation-sans-narrow, as the genropy Docker image does.',
                   families[0])


def warn_narrow_font_fallback():
    """Log once per process when fontconfig renders "Arial Narrow" with a font that is
    not narrow. Without the fontconfig tools nothing is logged."""
    with _narrow_font_lock:
        _warn_narrow_font_fallback()


class Service(HtmlToPdfService):
    def urlFetcher(self, url, **kwargs):
        """Reads the resources the site serves itself from their storage instead of
           requesting them to its public host"""
        node = self.parent.storageNodeFromUrl(url) if urlsplit(url).scheme in ('http', 'https') else None
        if node is None or not node.exists:
            return default_url_fetcher(url, **kwargs)
        with node.open('rb') as f:
            return dict(string=f.read(), mime_type=node.mimetype, redirected_url=url)

    def writePdf(self,srcPath, destPath,pageSize=None,pageMargin=None,stylesheets=None,
                pdf_kwargs=None, **kwargs):

        warn_narrow_font_fallback()
        srcPath = self.parent.storageNode(srcPath, parent=self.parent)
        stylesheets = self.pageStylesheets(pageSize=pageSize, pageMargin=pageMargin,
                                           pdf_kwargs=pdf_kwargs, stylesheets=stylesheets)
        stylesheets = [CSS(string=css) for css in stylesheets]
        if destPath is None:
            tmp = tempfile.NamedTemporaryFile(prefix='temp', suffix='.pdf',delete=False)
            with srcPath.local_path() as in_path:
                html_doc = HTML(in_path,base_url='.',url_fetcher=self.urlFetcher)
                html_doc.write_pdf(target=tmp,stylesheets=stylesheets,presentational_hints=True)
            tmp.seek(0)
            return tmp
        destPath = self.parent.storageNode(destPath, parent=self.parent)
        if destPath.isdir:
            baseName = os.path.splitext(srcPath.basename)[0]
            destPath = destPath.child(f'{baseName}.pdf')
        with srcPath.local_path() as in_path, destPath.local_path() as out_path:
            html_doc = HTML(in_path,base_url='.',url_fetcher=self.urlFetcher)
            html_doc.write_pdf(target=out_path,stylesheets=stylesheets,presentational_hints=True)
        return destPath.fullpath.replace('_raw_:', '')
