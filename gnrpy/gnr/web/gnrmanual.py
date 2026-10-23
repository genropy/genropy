"""The published user manual of an application, linked to its UI elements.

The manual is a Sphinx site (myst-parser) published like readthedocs. A section
documents a UI element when a label made from the element's doc address sits
above it (gnr.web.gnrdocumentation for the addresses):

    field:invc.invoice:customer_id   ->   (help-field-invc-invoice-customer_id)=

One site may hold several profile manuals, and a label is unique in a site: a
variant suffix lets each of them document the same element,
`(help-field-invc-invoice-customer_id--operatore)=`. Sphinx writes the labels
to the site's objects.inv, the map read here; the section is cut from the
published page. The manual pages of a user are the adm.helpdoc urls of the
user's group: their sections come first, and the variant of another group's
manual is never shown. A page is an http(s) url, an absolute path, or
(sys/ep_doc) a path of a local storage of the site, e.g.
`site:manual/index.html`, for a manual the instance serves itself.

What a site publishes is not trusted: only urls under the site's own folder
are read, without redirects and up to MAX_BYTES, and a section keeps only the
tags and attributes of an allow list, its links http(s) or of the site.
"""

import copy
import os
import re
import threading
import time
import zlib
from collections import OrderedDict
from urllib.parse import urljoin, urlsplit

import requests
from lxml import etree
from lxml import html as lxml_html

LABEL_PREFIX = 'help-'
VARIANT = '--'
CACHE_TTL = 300
FAILURE_TTL = 30
CACHE_BYTES = 16 * 1024 * 1024
MAX_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT = (3, 10)
SITE_DEPTH = 4
INVENTORY_LINE = re.compile(r'(.+?)\s+(\S+?):(\S+)\s+(-?\d+)\s+(\S*)\s+(.*)')
ALLOWED_TAGS = frozenset((
    'section', 'div', 'p', 'span', 'a', 'em', 'strong', 'b', 'i', 'u', 's', 'code', 'pre', 'kbd',
    'samp', 'var', 'sub', 'sup', 'small', 'mark', 'abbr', 'cite', 'q', 'del', 'ins', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'dl', 'dt', 'dd', 'table', 'thead',
    'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'colgroup', 'col', 'blockquote', 'figure',
    'figcaption', 'img', 'details', 'summary', 'aside'))
ALLOWED_ATTRIBUTES = {'a': {'href', 'title'}, 'img': {'src', 'alt', 'title', 'width', 'height'},
                      'abbr': {'title'}, 'ol': {'start', 'type'},
                      'td': {'colspan', 'rowspan'}, 'th': {'colspan', 'rowspan', 'scope'},
                      'col': {'span'}, 'colgroup': {'span'}}
# dropped with what they hold; any other tag out of the allow list keeps its text
DROPPED = frozenset((
    'script', 'style', 'iframe', 'frame', 'frameset', 'object', 'embed', 'applet', 'form', 'input',
    'button', 'select', 'textarea', 'svg', 'math', 'template', 'noscript', 'base', 'meta', 'link',
    'title', 'head', 'audio', 'video', 'canvas', 'map'))


class ManualCache(object):
    """What the manuals' sites answered, shared by the requests of a site: a
    url for CACHE_TTL seconds, a failure for FAILURE_TTL, the least recently
    read out first past CACHE_BYTES; a host that did not answer is skipped for
    FAILURE_TTL"""

    def __init__(self, max_bytes=CACHE_BYTES):
        self.max_bytes = max_bytes
        self._urls = OrderedDict()
        self._bytes = 0
        self._down = {}
        self._lock = threading.Lock()

    def get(self, url):
        """(True, content) while url is cached, (False, None) otherwise"""
        with self._lock:
            item = self._urls.get(url)
            if not item or item[0] < time.time():
                return False, None
            self._urls.move_to_end(url)
            return True, item[1]

    def put(self, url, content):
        with self._lock:
            self._drop(url)
            self._urls[url] = (time.time() + (FAILURE_TTL if content is None else CACHE_TTL), content)
            self._bytes += len(content or b'')
            while self._bytes > self.max_bytes and len(self._urls) > 1:
                self._drop(next(iter(self._urls)))

    def _drop(self, url):
        item = self._urls.pop(url, None)
        if item:
            self._bytes -= len(item[1] or b'')

    def host_down(self, url):
        until = self._down.get(urlsplit(url).netloc)
        return bool(until and until > time.time())

    def set_host_down(self, url):
        self._down[urlsplit(url).netloc] = time.time() + FAILURE_TTL

    def clear(self):
        with self._lock:
            self._urls.clear()
            self._bytes = 0
            self._down.clear()


def address_label(address):
    """The label a manual section carries to document a doc address"""
    return LABEL_PREFIX + re.sub(r'[:./]+', '-', address).strip('-').lower()


def is_remote(url):
    parts = urlsplit(url)
    return parts.scheme in ('http', 'https') and bool(parts.netloc)


def is_readable(url):
    """A manual page this module reads: an http(s) url or an absolute path"""
    return bool(url) and (is_remote(url) or (not urlsplit(url).scheme and os.path.isabs(url)))


def is_under(root, url):
    """url is root's folder or below it, on root's own scheme and host"""
    root_parts, parts = urlsplit(root), urlsplit(url)
    return (parts.scheme, parts.netloc) == (root_parts.scheme, root_parts.netloc) and \
        parts.path.startswith(root_parts.path)


def is_public_link(url):
    """A link or an image a section may keep: http(s), or a path of the site"""
    parts = urlsplit(url)
    return is_remote(url) or (not parts.scheme and not parts.netloc and url.startswith('/'))


def parse_inventory(data):
    """{label: (uri, title)} of the help- labels of a Sphinx objects.inv (v2)"""
    parts = (data or b'').split(b'\n', 4)
    if len(parts) < 5 or not parts[0].startswith(b'# Sphinx inventory version 2'):
        raise ValueError('not a Sphinx v2 inventory')
    result = {}
    for line in zlib.decompress(parts[4]).decode('utf-8').splitlines():
        match = INVENTORY_LINE.match(line)
        if not match:
            continue
        name, domain, role, _, uri, title = match.groups()
        if (domain, role) != ('std', 'label') or not name.startswith(LABEL_PREFIX):
            continue
        if uri.endswith('$'):
            uri = uri[:-1] + name
        result[name] = (uri, name if title == '-' else title)
    return result


def _read_remote(url, cache):
    try:
        with requests.get(url, timeout=FETCH_TIMEOUT, allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                return None
            content = response.raw.read(MAX_BYTES + 1, decode_content=True)
    except requests.RequestException:
        cache.set_host_down(url)
        return None
    return content if len(content) <= MAX_BYTES else None


def _read_local(path):
    try:
        with open(path, 'rb') as f:
            content = f.read(MAX_BYTES + 1)
    except OSError:
        return None
    return content if len(content) <= MAX_BYTES else None


def fetch(url, cache):
    """The bytes of a readable url, up to MAX_BYTES, through the cache; None
    when it cannot be read"""
    found, content = cache.get(url)
    if found:
        return content
    if not is_readable(url) or (is_remote(url) and cache.host_down(url)):
        return None
    content = _read_remote(url, cache) if is_remote(url) else _read_local(url)
    cache.put(url, content)
    return content


def site_of(page_url, cache):
    """(root url, inventory) of the Sphinx site publishing a page: its folder,
    then the folders above it, up to a host that does not answer"""
    folder = urljoin(page_url, '.')
    for _ in range(SITE_DEPTH):
        data = fetch(urljoin(folder, 'objects.inv'), cache)
        if data:
            try:
                return folder, parse_inventory(data)
            except (ValueError, zlib.error):
                return None
        if is_remote(folder) and cache.host_down(folder):
            return None
        parent = urljoin(folder, '..')
        if parent == folder:
            break
        folder = parent
    return None


def _clean(section, page_url):
    """The section with only the allowed tags and attributes, its links and
    images made absolute and http(s) or of the site"""
    etree.strip_elements(section, etree.Comment, etree.ProcessingInstruction, with_tail=False)
    for element in list(section.iter()):
        if element is not section and element.tag not in ALLOWED_TAGS:
            if element.tag in DROPPED:
                element.drop_tree()
            else:
                element.drop_tag()
            continue
        allowed = ALLOWED_ATTRIBUTES.get(element.tag, ())
        for name in list(element.attrib):
            if name not in allowed:
                del element.attrib[name]
            elif name in ('href', 'src'):
                url = urljoin(page_url, element.get(name).strip())
                if is_public_link(url):
                    element.set(name, url)
                else:
                    del element.attrib[name]


def cut_section(page_html, page_url, anchor):
    """{title, html} of the section an anchor opens, made to stand alone: no
    header links, the allow list of _clean"""
    tree = lxml_html.fromstring(page_html)
    target = tree.get_element_by_id(anchor, None)
    if target is None:
        return None
    section = target if target.tag == 'section' else target.getnext()
    if section is None or section.tag != 'section':
        section = target.getparent() if target.getparent() is not None and \
            target.getparent().tag == 'section' else None
    if section is None:
        return None
    section = copy.deepcopy(section)
    for element in section.xpath('.//*[contains(concat(" ", @class, " "), " headerlink ")]'):
        element.drop_tree()
    for element in section.xpath('.//span[@id and not(node())]'):
        element.drop_tree()
    heading = next((e for e in section if e.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')), None)
    title = heading.text_content().strip() if heading is not None else ''
    if heading is not None:
        heading.drop_tree()
    _clean(section, page_url)
    body = ''.join(lxml_html.tostring(child, encoding='unicode') for child in section)
    return dict(title=title, html=body)


class Manual(object):
    """The manual sections a user reaches: the sites of the user's own pages
    (the adm.helpdoc urls of the user's group), whose sections come first, and
    of the other pages the user may read"""

    def __init__(self, own_pages, other_pages=(), public_url=None, cache=None):
        # the pages are read where given; public_url maps a read url to the one
        # the browser opens (a manual in a local storage of the site)
        self.public_url = public_url or (lambda url: url)
        self.cache = cache if cache is not None else ManualCache()
        own_pages = [p for p in own_pages if is_readable(p)]
        self.page_set = {p.split('#')[0] for p in own_pages}
        self.sites = []
        roots = set()
        for page in own_pages + [p for p in other_pages if is_readable(p)]:
            site = site_of(page, self.cache)
            if site and site[0] not in roots:
                roots.add(site[0])
                self.sites.append(site)

    def _find(self, address):
        base = address_label(address)
        found = []
        for root, inventory in self.sites:
            for label, (uri, title) in inventory.items():
                read_url = urljoin(root, uri)
                if (label == base or label.startswith(base + VARIANT)) and is_under(root, read_url):
                    found.append(dict(label=label, read_url=read_url, title=title))
        own = [f for f in found if f['read_url'].split('#')[0] in self.page_set]
        plain = [f for f in found if f['label'] == base]
        return (own or plain or [None])[0]

    def find(self, address):
        """{label, url, title} of the section documenting an address: one in the
        user's own pages first, then the one without variant"""
        found = self._find(address)
        if not found:
            return None
        return dict(label=found['label'], url=self.public_url(found['read_url']), title=found['title'])

    def section(self, address):
        """{label, url, title, html} of the section documenting an address"""
        found = self._find(address)
        if not found:
            return None
        page_url, _, anchor = found['read_url'].partition('#')
        page = fetch(page_url, self.cache)
        cut = cut_section(page, self.public_url(page_url), anchor) if page and anchor else None
        if not cut:
            return None
        return dict(label=found['label'], url=self.public_url(found['read_url']),
                    title=cut['title'] or found['title'], html=cut['html'])
