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
user's group: their sections come first. A page is an http(s) url, a file, or
(sys/ep_doc) a path of a local storage of the site, e.g. `site:manual/index.html`,
for a manual the instance serves itself.
"""

import copy
import re
import time
import zlib
from urllib.parse import urljoin, urlsplit
from urllib.request import url2pathname

import requests
from lxml import html as lxml_html

LABEL_PREFIX = 'help-'
VARIANT = '--'
CACHE_TTL = 300
FETCH_TIMEOUT = 10
SITE_DEPTH = 4
DROPPED = ('script', 'style', 'iframe', 'object', 'embed', 'form')
INVENTORY_LINE = re.compile(r'(.+?)\s+(\S+?):(\S+)\s+(-?\d+)\s+(\S*)\s+(.*)')

_cache = {}


def address_label(address):
    """The label a manual section carries to document a doc address"""
    return LABEL_PREFIX + re.sub(r'[:./]+', '-', address).strip('-').lower()


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


def fetch(url):
    """The bytes at an http(s) url, a file:// url or a local path, cached for
    CACHE_TTL seconds; None when it cannot be read"""
    cached = _cache.get(url)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]
    parts = urlsplit(url)
    content = None
    if parts.scheme in ('http', 'https'):
        try:
            response = requests.get(url, timeout=FETCH_TIMEOUT)
            content = response.content if response.ok else None
        except requests.RequestException:
            content = None
    else:
        try:
            with open(url2pathname(parts.path) if parts.scheme == 'file' else url, 'rb') as f:
                content = f.read()
        except OSError:
            content = None
    _cache[url] = (time.time(), content)
    return content


def site_of(page_url):
    """(root url, inventory) of the Sphinx site publishing a page: its folder,
    then the folders above it"""
    folder = urljoin(page_url, '.')
    for _ in range(SITE_DEPTH):
        data = fetch(urljoin(folder, 'objects.inv'))
        if data:
            try:
                return folder, parse_inventory(data)
            except (ValueError, zlib.error):
                return None
        parent = urljoin(folder, '..')
        if parent == folder:
            break
        folder = parent
    return None


def cut_section(page_html, page_url, anchor):
    """{title, html} of the section an anchor opens, made to stand alone: its
    links and images absolute, no scripts, no header links"""
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
    for element in [e for e in section.iter() if e.tag in DROPPED]:
        element.drop_tree()
    for element in section.xpath('.//span[@id and not(node())]'):
        element.drop_tree()
    for element in section.iter():
        for name in list(element.attrib):
            if name.lower().startswith('on'):
                del element.attrib[name]
        for name in ('href', 'src'):
            value = element.get(name)
            if value is None:
                continue
            if value.strip().lower().startswith('javascript:'):
                del element.attrib[name]
            else:
                element.set(name, urljoin(page_url, value))
    heading = next((e for e in section if e.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')), None)
    title = heading.text_content().strip() if heading is not None else ''
    if heading is not None:
        heading.drop_tree()
    body = ''.join(lxml_html.tostring(child, encoding='unicode') for child in section)
    return dict(title=title, html=body)


class Manual(object):
    """The manual sections a user reaches: the sites of the user's own pages
    (the adm.helpdoc urls of the user's group), whose sections come first, and
    of the other pages the user may read"""

    def __init__(self, own_pages, other_pages=(), public_url=None):
        # the pages are read where given; public_url maps a read url to the one
        # the browser opens (a manual in a local storage of the site)
        self.public_url = public_url or (lambda url: url)
        own_pages = [p for p in own_pages if p]
        self.page_set = {p.split('#')[0] for p in own_pages}
        self.sites = []
        roots = set()
        for page in own_pages + [p for p in other_pages if p]:
            site = site_of(page)
            if site and site[0] not in roots:
                roots.add(site[0])
                self.sites.append(site)

    def _find(self, address):
        base = address_label(address)
        found = []
        for root, inventory in self.sites:
            for label, (uri, title) in inventory.items():
                if label == base or label.startswith(base + VARIANT):
                    found.append(dict(label=label, read_url=urljoin(root, uri), title=title))
        if not found:
            return None
        own = [f for f in found if f['read_url'].split('#')[0] in self.page_set]
        plain = [f for f in found if f['label'] == base]
        return (own or plain or found)[0]

    def find(self, address):
        """{label, url, title} of the section documenting an address: one in the
        user's own pages first, then the one without variant, then any"""
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
        page = fetch(page_url)
        cut = cut_section(page, self.public_url(page_url), anchor) if page and anchor else None
        if not cut:
            return None
        return dict(label=found['label'], url=self.public_url(found['read_url']),
                    title=cut['title'] or found['title'], html=cut['html'])
