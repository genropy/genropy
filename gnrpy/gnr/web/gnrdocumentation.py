"""Documentation kept as MyST Markdown files in the `inlinedoc` storage.

A doc is addressed `<kind>:<target>:<name>`, the context-sensitive help ID of a
package, table, field, grouplet or page, and lives in one folder per address,
one file per language, its images beside it:

    <pkg>/_package/<lang>.md                         package:<pkg>:
    <pkg>/<table>/_table/<lang>.md                   table:<pkg.table>:
    <pkg>/<table>/fields/<column>/<lang>.md          field:<pkg.table>:<column>
    <pkg>/<table>/grouplets/<resource>/<lang>.md     grouplet:<pkg.table>:<resource>
    <pkg>/_grouplets/<resource>/<lang>.md            grouplet:<pkg>:<resource>
    <pkg>/_pages/<page>/<helpcode>/<lang>.md         page:<pkg>/<page>:<helpcode>
    <folder>/assets/<file>

Each file opens with a YAML front matter (`id`, `title`, `type`, `updated`,
`author`), so the same files build the Sphinx reference through myst-parser.
As attachments do, the docs go in `home:inlinedoc/` unless a storage service
named `inlinedoc` is configured (siteconfig or sys.service), e.g. an S3 bucket.
"""

import base64
import html
import re
import time
import uuid
from datetime import datetime, timezone

import yaml
from markdown_it import MarkdownIt

DOC_SERVICE = 'inlinedoc'
LISTING_TTL = 30
SEGMENT = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.-]*$')
LANGUAGE = re.compile(r'^[a-z]{2}(-[A-Za-z]{2})?$')
FRONT_MATTER = re.compile(r'\A---\n(.*?)\n---\n?', re.S)
ASSET_LINK = re.compile(r'(src|href)="assets/([^"]+)"')
ASSET_TYPES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/gif': 'gif', 'image/webp': 'webp'}

_markdown = MarkdownIt('commonmark', {'html': False}).enable(['table', 'strikethrough'])
_listings = {}


class DocumentationConflict(Exception):
    """The doc changed since the editor loaded it"""

    def __init__(self, mtime):
        super().__init__(mtime)
        self.mtime = mtime


def _path(*parts):
    path = '/'.join(parts)
    if not all(SEGMENT.match(segment) for segment in path.split('/')):
        raise ValueError(f'not a documentation path: {path}')
    return path


def doc_folder(address):
    """The folder of a doc address; ValueError for anything else"""
    parts = (address or '').split(':', 2)
    if len(parts) != 3:
        raise ValueError(f'not a doc address: {address}')
    kind, target, name = parts
    if kind == 'package' and target and not name:
        return _path(target, '_package')
    if kind == 'page' and '/' in target and name:
        pkg, page = target.split('/', 1)
        return _path(pkg, '_pages', page, name)
    pkg, _, table = target.partition('.')
    if kind == 'table' and table and not name:
        return _path(pkg, table, '_table')
    if kind == 'field' and table and name and '/' not in name:
        return _path(pkg, table, 'fields', name)
    if kind == 'grouplet' and pkg and name:
        return _path(pkg, table, 'grouplets', name) if table else _path(pkg, '_grouplets', name)
    raise ValueError(f'not a doc address: {address}')


def split_front_matter(text):
    match = FRONT_MATTER.match(text or '')
    if not match:
        return {}, text or ''
    return yaml.safe_load(match.group(1)) or {}, text[match.end():].lstrip('\n')


def join_front_matter(meta, body):
    return '---\n%s---\n\n%s' % (yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
                                 (body or '').lstrip('\n'))


def render_markdown(body, asset_url=None):
    """CommonMark with tables, raw HTML escaped: a doc cannot inject markup"""
    result = _markdown.render(body or '')
    if asset_url:
        result = ASSET_LINK.sub(lambda m: '%s="%s"' % (m.group(1), html.escape(asset_url(m.group(2)))),
                                result)
    return result


def _same_mtime(current, base):
    if current is None or base is None:
        return current is None and base is None
    return abs(float(current) - float(base)) < 0.001


class DocumentationStore(object):
    """The docs of a site: the `inlinedoc` storage service when configured,
    else the `inlinedoc` folder of `home`"""

    def __init__(self, site, service=DOC_SERVICE):
        self.site = site
        self.service = service

    @property
    def root(self):
        if self.site.storage_handler.getStorageParameters(self.service):
            return f'{self.service}:'
        return f'home:{self.service}/'

    def node(self, path, **kwargs):
        return self.site.storageNode(f'{self.root}{path}', **kwargs)

    def _prefix(self, folder):
        return '/'.join(folder.split('/')[:2])

    def _cache_key(self, prefix):
        return (self.site.site_path, self.service, prefix)

    def _listing(self, prefix):
        """{relative path: mtime} under a package or table, listed once for all
        its docs and kept for LISTING_TTL seconds"""
        key = self._cache_key(prefix)
        cached = _listings.get(key)
        if cached and time.time() - cached[0] < LISTING_TTL:
            return cached[1]
        node = self.node(prefix)
        listing = node.file_mtimes() if node.exists else {}
        _listings[key] = (time.time(), listing)
        return listing

    def forget(self, folder):
        _listings.pop(self._cache_key(self._prefix(folder)), None)

    def languages(self, folder):
        """{language: mtime} of the files of a doc"""
        prefix = self._prefix(folder)
        start = folder[len(prefix):].strip('/')
        start = f'{start}/' if start else ''
        result = {}
        for path, mtime in self._listing(prefix).items():
            name = path[len(start):] if path.startswith(start) else None
            if name and '/' not in name and name.endswith('.md'):
                result[name[:-3]] = mtime
        return result

    @staticmethod
    def pick_language(available, languages):
        for language in languages:
            if language in available:
                return language
        return sorted(available)[0] if available else None

    def index(self, addresses, languages):
        """{address: {language, mtime}} of the addresses that have a doc"""
        result = {}
        for address in addresses:
            try:
                folder = doc_folder(address)
            except ValueError:
                continue
            available = self.languages(folder)
            language = self.pick_language(available, languages)
            if language:
                result[address] = dict(language=language, mtime=available[language])
        return result

    def read(self, address, languages):
        """{language, mtime, meta, markdown} of a doc, None when it has none"""
        folder = doc_folder(address)
        language = self.pick_language(self.languages(folder), languages)
        node = self.node(f'{folder}/{language}.md') if language else None
        if not (node and node.exists):
            return None
        with node.open('rb') as f:
            meta, body = split_front_matter(f.read().decode('utf-8'))
        return dict(language=language, mtime=node.mtime, meta=meta, markdown=body)

    def save(self, address, language, markdown, title=None, author=None, base_mtime=None, force=False):
        """Writes a doc, refusing it when it changed since base_mtime; returns
        its new mtime. The front matter keeps what it held and updates the rest"""
        folder = doc_folder(address)
        if not LANGUAGE.match(language or ''):
            raise ValueError(f'not a language: {language}')
        node = self.node(f'{folder}/{language}.md', autocreate=-1)
        current = node.mtime if node.exists else None
        if not force and not _same_mtime(current, base_mtime):
            raise DocumentationConflict(current)
        meta = {}
        if current is not None:
            with node.open('rb') as f:
                meta = split_front_matter(f.read().decode('utf-8'))[0]
        meta.update(id=address, title=title or meta.get('title') or address.split(':')[-1] or address,
                    updated=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        meta.setdefault('type', 'reference')
        if author:
            meta['author'] = author
        with node.open('wb') as f:
            f.write(join_front_matter(meta, markdown).encode('utf-8'))
        self.forget(folder)
        return node.mtime

    def asset_node(self, address, name):
        return self.node(_path(doc_folder(address), 'assets', name))

    def save_asset(self, address, data_url):
        """Stores an image given as a data url next to the doc; returns the
        relative link the Markdown keeps"""
        header, _, payload = (data_url or '').partition(',')
        mimetype = header[len('data:'):].split(';')[0] if header.startswith('data:') else None
        if mimetype not in ASSET_TYPES or ';base64' not in header:
            raise ValueError(f'not an image data url: {header}')
        name = f'{uuid.uuid4().hex}.{ASSET_TYPES[mimetype]}'
        node = self.node(_path(doc_folder(address), 'assets', name), autocreate=-1)
        with node.open('wb') as f:
            f.write(base64.b64decode(payload))
        return f'assets/{name}'
