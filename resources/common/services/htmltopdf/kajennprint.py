"""htmltopdf implementation backed by a kajenn print server.

The html is rendered by a remote print server (``POST <url>/<mount>/pdf``)
instead of a renderer installed on the site host. The interface is the one of
the ``weasyprint`` implementation: same ``writePdf`` arguments and return
values, same page size and margin handling (sent to the server as user
stylesheets), same presentational hints.

A print server loads only ``data:`` urls by default and never local files,
while a local renderer reads the stylesheets and images the document points
to on disk or on the site. With ``inline_resources`` (the default) the
service embeds them before sending: ``<link rel="stylesheet">`` become
``<style>`` blocks, ``@import`` rules are expanded, and images, fonts and other
``url()``/``src`` references become ``data:`` urls. Relative references are
resolved like the local renderer does, against ``base_url`` or the current
working directory. A reference that cannot be read is left as it is.

Setting ``KAJENN_PRINT_URL`` to the print server url makes this the default
htmltopdf implementation, connecting to that server.

Service parameters: ``url`` (default ``$KAJENN_PRINT_URL`` or
``http://127.0.0.1:8000``), ``token`` (an api key carrying the ``print`` tag,
default ``$KAJENN_PRINT_TOKEN``), ``mount`` (default ``print``), ``timeout``
in seconds (default 120), ``base_url`` and ``inline_resources``.
"""

import base64
import html as html_lib
import logging
import mimetypes
import os
import re
import tempfile
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import pathname2url, url2pathname

import requests
from gnr.lib.services.htmltopdf import (
    KAJENN_PRINT_ENV,
    HtmlToPdfError,
    HtmlToPdfService,
)
from gnr.web.gnrbaseclasses import BaseComponent

logger = logging.getLogger('gnr.htmltopdf.kajennprint')

DEFAULT_URL = 'http://127.0.0.1:8000'
DEFAULT_MOUNT = 'print'
DEFAULT_TIMEOUT = 120

LINK_TAG_RE = re.compile(r'<link\b[^>]*>', re.IGNORECASE)
STYLE_BLOCK_RE = re.compile(r'(<style\b[^>]*>)(.*?)(</style\s*>)', re.IGNORECASE | re.DOTALL)
TAG_ATTR_RE = re.compile(r'''([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''')
SRC_ATTR_RE = re.compile(r'''(\s(?:src|xlink:href)\s*=\s*)(["'])(.*?)\2''', re.IGNORECASE | re.DOTALL)
STYLE_ATTR_RE = re.compile(r'''(\sstyle\s*=\s*)(["'])(.*?)\2''', re.IGNORECASE | re.DOTALL)
CSS_IMPORT_RE = re.compile(
    r'''@import\s+(?:url\(\s*(["']?)(.*?)\1\s*\)|(["'])(.*?)\3)\s*([^;]*);''', re.IGNORECASE)
CSS_URL_RE = re.compile(r'''url\(\s*(["']?)(.*?)\1\s*\)''', re.IGNORECASE)

MAX_IMPORT_DEPTH = 8


def is_inline_url(url):
    """True for references that need no fetching (embedded data, fragments)."""
    url = url.strip()
    return not url or url.startswith('#') or url.lower().startswith(('data:', 'about:'))


def print_error(message):
    """An HtmlToPdfError carrying ``message`` verbatim: GnrException %-formats its text."""
    return HtmlToPdfError(message.replace('%', '%%'))


def no_credentials(request):
    """A requests auth that adds nothing: only the headers the service sets are sent."""
    return request


class ResourceInliner:
    """Embeds in an html source the external resources it references.

    :param base_url: the url relative references resolve against
    :param timeout: seconds allowed to each http(s) fetch"""

    def __init__(self, base_url, timeout=DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self._cache = {}

    def fetch(self, url):
        """Returns ``(content bytes, mime type)`` for an absolute url, ``None`` when unreadable."""
        if url in self._cache:
            return self._cache[url]
        result = None
        parsed = urlparse(url)
        try:
            if parsed.scheme == 'file':
                path = url2pathname(unquote(parsed.path))
                with open(path, 'rb') as f:
                    result = (f.read(), mimetypes.guess_type(path)[0])
            elif parsed.scheme in ('http', 'https'):
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                mime = response.headers.get('Content-Type', '').split(';')[0].strip()
                result = (response.content, mime or mimetypes.guess_type(parsed.path)[0])
        except (OSError, requests.RequestException) as e:
            logger.warning('kajennprint: cannot embed %s: %s', url, e)
        self._cache[url] = result
        return result

    def data_url(self, ref, base):
        """The ``data:`` url embedding ``ref``, or ``ref`` itself when it cannot be read."""
        if is_inline_url(ref):
            return ref
        url = urljoin(base, ref.strip())
        fetched = self.fetch(url)
        if fetched is None:
            return ref
        content, mime = fetched
        mime = mime or 'application/octet-stream'
        if mime == 'text/css':
            css = self.inline_css(self.decode(content), url)
            content = css.encode('utf-8')
            mime = 'text/css;charset=utf-8'
        return 'data:{};base64,{}'.format(mime, base64.b64encode(content).decode('ascii'))

    def decode(self, content):
        try:
            return content.decode('utf-8-sig')
        except UnicodeDecodeError:
            return content.decode('latin-1')

    def stylesheet(self, ref, base, depth=0):
        """The css text of the stylesheet at ``ref`` with its own references embedded."""
        if is_inline_url(ref) or depth > MAX_IMPORT_DEPTH:
            return None
        url = urljoin(base, ref.strip())
        fetched = self.fetch(url)
        if fetched is None:
            return None
        return self.inline_css(self.decode(fetched[0]), url, depth=depth + 1)

    def inline_css(self, css, base, depth=0):
        """Expands ``@import`` rules and embeds ``url()`` references of a css source."""
        def expand_import(match):
            ref = match.group(2) if match.group(2) is not None else match.group(4)
            media = match.group(5).strip()
            imported = self.stylesheet(ref, base, depth=depth)
            if imported is None:
                return match.group(0)
            return f'@media {media} {{\n{imported}\n}}' if media else imported

        #@import rules must come first in a stylesheet: expanded in place they are
        #only valid there, which is where the css language already requires them
        css = CSS_IMPORT_RE.sub(expand_import, css)
        return CSS_URL_RE.sub(
            lambda m: 'url("{}")'.format(self.data_url(m.group(2), base).replace('"', '%22')), css)

    def inline_link(self, match):
        tag = match.group(0)
        attrs = {}
        for name, dq, sq, bare in TAG_ATTR_RE.findall(tag[5:]):
            value = dq if dq or not (sq or bare) else (sq or bare)
            attrs[name.lower()] = html_lib.unescape(value)
        if 'stylesheet' not in attrs.get('rel', '').lower().split() or not attrs.get('href'):
            return tag
        css = self.stylesheet(attrs['href'], self.base_url)
        if css is None:
            return tag
        media = attrs.get('media')
        media_attr = f' media="{html_lib.escape(media)}"' if media else ''
        return '<style{}>\n{}\n</style>'.format(media_attr, css.replace('</', '<\\/'))

    def inline_attr(self, match):
        prefix, quote, value = match.groups()
        embedded = self.data_url(html_lib.unescape(value), self.base_url)
        return f'{prefix}{quote}{html_lib.escape(embedded, quote=True)}{quote}'

    def inline_style_attr(self, match):
        prefix, quote, value = match.groups()
        css = self.inline_css(html_lib.unescape(value), self.base_url)
        return f'{prefix}{quote}{html_lib.escape(css, quote=True)}{quote}'

    def inline_html(self, html):
        """The html source with its stylesheets, images and fonts embedded."""
        html = LINK_TAG_RE.sub(self.inline_link, html)
        html = STYLE_BLOCK_RE.sub(lambda m: m.group(1) + self.inline_css(m.group(2), self.base_url)
                                  + m.group(3), html)
        html = SRC_ATTR_RE.sub(self.inline_attr, html)
        return STYLE_ATTR_RE.sub(self.inline_style_attr, html)


class Service(HtmlToPdfService):
    def __init__(self, parent, url=None, token=None, mount=None, timeout=None,
                 base_url=None, inline_resources=True, **kwargs):
        self.parent = parent
        self.url = (url or os.environ.get(KAJENN_PRINT_ENV, '').strip() or DEFAULT_URL).rstrip('/')
        self.token = token or os.environ.get('KAJENN_PRINT_TOKEN')
        self.mount = (mount or DEFAULT_MOUNT).strip('/')
        self.timeout = float(timeout or DEFAULT_TIMEOUT)
        self.base_url = base_url or None
        self.inline_resources = inline_resources not in (False, 'false', 'False', 0, '0')

    @property
    def endpoint(self):
        return f'{self.url}/{self.mount}/pdf'

    def resourceBaseUrl(self):
        """The url relative references resolve against: the local renderer uses the cwd."""
        if self.base_url:
            return self.base_url
        return urljoin('file:', pathname2url(os.getcwd()) + '/')

    def readHtml(self, srcPath):
        with srcPath.open('rb') as f:
            content = f.read()
        try:
            return content.decode('utf-8-sig')
        except UnicodeDecodeError:
            return content.decode('cp1252', errors='replace')

    def errorDetail(self, response):
        try:
            return response.json().get('error', response.text)
        except ValueError:
            return response.text.strip() or response.reason

    def requestPdf(self, html, stylesheets=None, filename=None):
        """Sends the html to the print server and returns the pdf bytes."""
        payload = {'html': html, 'stylesheets': stylesheets or [], 'presentational_hints': True}
        if filename:
            payload['filename'] = filename
        if self.base_url:
            payload['base_url'] = self.base_url
        headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
        try:
            #auth=no_credentials: without it requests adds ~/.netrc credentials on its own,
            #which the server rejects with a 401 even when its print routes are public
            response = requests.post(self.endpoint, json=payload, headers=headers,
                                     auth=no_credentials, timeout=self.timeout)
        except requests.RequestException as e:
            raise print_error(f'print server {self.endpoint} unreachable: {e}')
        if response.status_code == 401:
            #the server rejects an unknown token even when its print routes are public
            if self.token:
                raise print_error(f'print server {self.endpoint}: the token was rejected (401: '
                                     f'{self.errorDetail(response)}); check the service token or '
                                     'KAJENN_PRINT_TOKEN, or clear it if the server needs no '
                                     'authentication')
            raise print_error(f'print server {self.endpoint}: authentication required (401: '
                                 f'{self.errorDetail(response)}), set the service token or '
                                 'KAJENN_PRINT_TOKEN; is the url the server you expect?')
        if response.status_code == 403:
            raise print_error(f'print server {self.endpoint}: the token does not carry the print tag (403)')
        if response.status_code != 200:
            raise print_error(f'print server {self.endpoint} answered {response.status_code}: '
                                 f'{self.errorDetail(response)}')
        if response.headers.get('Content-Type', '').split(';')[0] != 'application/pdf':
            raise print_error(f'{self.endpoint} did not answer a pdf: check url and mount')
        return response.content

    def writePdf(self, srcPath, destPath, pageSize=None, pageMargin=None, stylesheets=None,
                 pdf_kwargs=None, **kwargs):
        srcPath = self.parent.storageNode(srcPath, parent=self.parent)
        stylesheets = self.pageStylesheets(pageSize=pageSize, pageMargin=pageMargin,
                                           pdf_kwargs=pdf_kwargs, stylesheets=stylesheets)
        html = self.readHtml(srcPath)
        baseName = os.path.splitext(srcPath.basename)[0]
        if self.inline_resources:
            inliner = ResourceInliner(self.resourceBaseUrl(), timeout=self.timeout)
            html = inliner.inline_html(html)
            stylesheets = [inliner.inline_css(css, inliner.base_url) for css in stylesheets]
        pdf = self.requestPdf(html, stylesheets=stylesheets, filename=f'{baseName}.pdf')
        if destPath is None:
            tmp = tempfile.NamedTemporaryFile(prefix='temp', suffix='.pdf', delete=False)  # noqa: SIM115 (the caller closes it)
            tmp.write(pdf)
            tmp.flush()
            tmp.seek(0)
            return tmp
        destPath = self.parent.storageNode(destPath, parent=self.parent)
        if destPath.isdir:
            destPath = destPath.child(f'{baseName}.pdf')
        with destPath.open('wb') as f:
            f.write(pdf)
        return destPath.fullpath.replace('_raw_:', '')


class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.url', lbl='Print server url', width='30em',
                   placeholder=DEFAULT_URL)
        fb.passwordTextBox(value='^.token', lbl='Api key', width='30em')
        fb.textbox(value='^.mount', lbl='Mount', placeholder=DEFAULT_MOUNT)
        fb.numberTextBox(value='^.timeout', lbl='Timeout (s)', width='5em', places=0,
                         placeholder=str(DEFAULT_TIMEOUT))
        fb.textbox(value='^.base_url', lbl='Base url', width='30em')
        fb.checkbox(value='^.inline_resources', label='Embed local resources')
