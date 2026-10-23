"""htmltopdf implementation backed by a kajenn print server.

The html is rendered by a remote print server (``POST <url>/<mount>/pdf``)
instead of a renderer installed on the site host. The interface is the one of
the ``weasyprint`` implementation: same ``writePdf`` arguments and return
values, same page size and margin handling (sent to the server as user
stylesheets), same presentational hints.

A print server loads only ``data:`` urls by default and never local files,
while a local renderer reads the stylesheets and images the document points
to on disk or on the site. Unless ``no_inline_resources`` is set the
service embeds them before sending: ``<link rel="stylesheet">`` become
``<style>`` blocks, ``@import`` rules are expanded, and images, fonts and other
``url()``/``src`` references become ``data:`` urls. Relative references are
resolved like the local renderer does, against ``base_url`` or the current
working directory. A reference that cannot be read is left as it is.

Only stylesheets, images and fonts are embedded, and local files only when they
lie in the site, instance, resource or package folders (or in ``local_roots``):
the html may carry user-entered content, and whatever is embedded is sent to
the print server. Resource requests carry no credentials, and a host that does
not answer within ``resource_timeout`` is not asked again for the same document.

``<experimental><htmltopdf kajenn_print_url="..."/></experimental>`` in
instanceconfig.xml makes this the default htmltopdf implementation, connecting
to that server.

Service parameters: ``url`` (default ``$KAJENN_PRINT_URL`` or
``http://127.0.0.1:8000``), ``token`` (an api key carrying the ``print`` tag,
default ``$KAJENN_PRINT_TOKEN``), ``mount`` (default ``print``), ``timeout``
of the render request in seconds (default 120), ``resource_timeout`` of each
resource fetch in seconds (default 10), ``base_url``, ``local_roots`` (extra
comma-separated folders local resources may be read from) and
``no_inline_resources`` (send the references as they are).
"""

import base64
import html as html_lib
import logging
import mimetypes
import os
import re
import tempfile
import time
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import pathname2url, url2pathname

import requests
from gnr.core.gnrstring import boolean, splitAndStrip
from gnr.lib.services.htmltopdf import HtmlToPdfError, HtmlToPdfService
from gnr.web.gnrbaseclasses import BaseComponent

logger = logging.getLogger('gnr.htmltopdf.kajennprint')

DEFAULT_URL = 'http://127.0.0.1:8000'
DEFAULT_MOUNT = 'print'
DEFAULT_TIMEOUT = 120
DEFAULT_RESOURCE_TIMEOUT = 10
MAX_RESOURCE_SIZE = 20 * 1024 * 1024
MAX_RESOURCE_REDIRECTS = 5
KAJENN_PRINT_ENV = 'KAJENN_PRINT_URL'

#the resource types the inliner embeds: anything else is left as a reference
EMBEDDED_MIME_PREFIXES = ('image/', 'font/')
EMBEDDED_MIMES = {'text/css', 'application/vnd.ms-fontobject', 'application/font-woff',
                  'application/x-font-woff', 'application/x-font-ttf', 'application/x-font-otf'}

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


class NoCredentialsSession(requests.Session):
    """A session that never sends credentials of its own.

    requests reads ~/.netrc for every request without auth and again for the
    target of every redirect: the site host's credentials would reach any host
    an html reference points to, or redirects to."""

    def __init__(self):
        super().__init__()
        self.auth = no_credentials
        self.max_redirects = MAX_RESOURCE_REDIRECTS

    def rebuild_auth(self, prepared_request, response):
        prepared_request.headers.pop('Authorization', None)


def is_embeddable(mime):
    """True for the stylesheet, image and font types the inliner embeds."""
    return bool(mime) and (mime in EMBEDDED_MIMES or mime.startswith(EMBEDDED_MIME_PREFIXES))


def is_inside(path, roots):
    """True when the real ``path`` lies in one of the real folders ``roots``."""
    path = os.path.realpath(path)
    return any(os.path.commonpath([path, root]) == root for root in roots)


class ResourceInliner:
    """Embeds in an html source the external resources it references.

    :param base_url: the url relative references resolve against
    :param timeout: seconds allowed to each http(s) fetch, body included
    :param local_roots: the folders local files may be read from, none when empty"""

    def __init__(self, base_url, timeout=DEFAULT_RESOURCE_TIMEOUT, local_roots=None):
        self.base_url = base_url
        self.timeout = timeout
        self.local_roots = [os.path.realpath(root) for root in local_roots or []]
        self._cache = {}
        self._unreachable_hosts = set()
        self.session = NoCredentialsSession()

    def close(self):
        self.session.close()

    def fetch(self, url):
        """Returns ``(content bytes, mime type)`` for an absolute url, ``None`` when unreadable."""
        if url not in self._cache:
            parsed = urlparse(url)
            if parsed.scheme == 'file':
                self._cache[url] = self.fetch_file(url2pathname(unquote(parsed.path)))
            elif parsed.scheme in ('http', 'https'):
                self._cache[url] = self.fetch_http(url, parsed)
            else:
                self._cache[url] = None
        return self._cache[url]

    def fetch_file(self, path):
        try:
            #type and folder are checked on the target of any symlink, which is what is read
            path = os.path.realpath(path)
            mime = mimetypes.guess_type(path)[0]
            if not is_embeddable(mime):
                logger.warning('kajennprint: %s is not a stylesheet, image or font, not embedded',
                               path)
                return None
            if not is_inside(path, self.local_roots):
                logger.warning('kajennprint: %s is outside the site folders, not embedded', path)
                return None
            with open(path, 'rb') as f:
                return (f.read(), mime)
        except (OSError, ValueError) as e:
            logger.warning('kajennprint: cannot embed %r: %s', path, e)
            return None

    def fetch_http(self, url, parsed):
        if parsed.netloc in self._unreachable_hosts:
            return None
        deadline = time.monotonic() + self.timeout
        try:
            with self.session.get(url, timeout=self.timeout, stream=True) as response:
                response.raise_for_status()
                mime = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
                if mime in ('', 'application/octet-stream'):
                    #the path of the answering url: a redirect may lead anywhere
                    mime = mimetypes.guess_type(urlparse(response.url).path)[0]
                if not is_embeddable(mime):
                    logger.warning('kajennprint: %s is not a stylesheet, image or font (%s), '
                                   'not embedded', url, mime)
                    return None
                content = self.read_body(response, deadline)
        except (requests.ConnectionError, requests.Timeout) as e:
            #one wait per host: its other resources would time out the same way
            self._unreachable_hosts.add(parsed.netloc)
            logger.warning('kajennprint: cannot embed %s: %s', url, e)
            return None
        except requests.RequestException as e:
            logger.warning('kajennprint: cannot embed %s: %s', url, e)
            return None
        if content is None:
            logger.warning('kajennprint: %s exceeds %s bytes, not embedded', url, MAX_RESOURCE_SIZE)
            return None
        return (content, mime)

    def read_body(self, response, deadline):
        """The response body, ``None`` beyond ``MAX_RESOURCE_SIZE``.

        The read timeout bounds each socket read only; the deadline, checked
        between chunks, bounds a large body arriving slowly."""
        chunks = []
        size = 0
        for chunk in response.iter_content(64 * 1024):
            size += len(chunk)
            if size > MAX_RESOURCE_SIZE:
                return None
            if time.monotonic() > deadline:
                raise requests.Timeout(f'body not received within {self.timeout} s')
            chunks.append(chunk)
        return b''.join(chunks)

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
                 resource_timeout=None, base_url=None, local_roots=None,
                 no_inline_resources=False, **kwargs):
        self.parent = parent
        self.url = (url or os.environ.get(KAJENN_PRINT_ENV, '').strip() or DEFAULT_URL).rstrip('/')
        self.token = token or os.environ.get('KAJENN_PRINT_TOKEN')
        self.mount = (mount or DEFAULT_MOUNT).strip('/')
        self.timeout = float(timeout or DEFAULT_TIMEOUT)
        self.resource_timeout = float(resource_timeout or DEFAULT_RESOURCE_TIMEOUT)
        self.base_url = base_url or None
        self.local_roots = local_roots
        #an opt-out: an unset value in the service record, like an unchecked box, embeds
        self.inline_resources = not boolean(no_inline_resources)

    @property
    def endpoint(self):
        return f'{self.url}/{self.mount}/pdf'

    def resourceBaseUrl(self):
        """The url relative references resolve against: the local renderer uses the cwd."""
        if self.base_url:
            return self.base_url
        return urljoin('file:', pathname2url(os.getcwd()) + '/')

    def resourceRoots(self):
        """The folders local resources may be read from: site, instance, resources,
        packages and the ``local_roots`` parameter."""
        site = self.parent
        roots = [getattr(site, 'site_path', None), getattr(site, 'instance_path', None),
                 getattr(site, 'site_static_dir', None)]
        roots.extend(getattr(site, 'resources_dirs', None) or [])
        gnrapp = getattr(site, 'gnrapp', None)
        if gnrapp is not None:
            roots.extend(getattr(pkg, 'packageFolder', None) for pkg in gnrapp.packages.values())
        roots.extend(splitAndStrip(self.local_roots, ',') if isinstance(self.local_roots, str)
                     else self.local_roots or [])
        return [root for root in roots if root]

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
            inliner = ResourceInliner(self.resourceBaseUrl(), timeout=self.resource_timeout,
                                      local_roots=self.resourceRoots())
            try:
                html = inliner.inline_html(html)
                stylesheets = [inliner.inline_css(css, inliner.base_url) for css in stylesheets]
            finally:
                inliner.close()
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
        fb.numberTextBox(value='^.resource_timeout', lbl='Resource timeout (s)', width='5em',
                         places=0, placeholder=str(DEFAULT_RESOURCE_TIMEOUT))
        fb.textbox(value='^.base_url', lbl='Base url', width='30em')
        fb.textbox(value='^.local_roots', lbl='Resource folders', width='30em',
                   placeholder='extra folders, comma separated')
        fb.checkbox(value='^.no_inline_resources', label='Do not embed resources')
