"""gnr.web.gnrmanual: the published manual's sections of the app's doc addresses.

A small manual is written in the shape Sphinx publishes it (objects.inv and
the html of its pages), read from its folder and over a real local HTTP
server; the last test builds the same manual with Sphinx and myst-parser, as
the applications' manuals are, where they are installed.
"""

import base64
import functools
import http.server
import shutil
import threading
import time
import zlib

import pytest
import requests

from gnr.web import gnrmanual
from gnr.web.gnrmanual import (Manual, ManualCache, address_label, cut_section, fetch,
                               is_storage_path, parse_inventory, site_of)

PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
INVENTORY_HEADER = (b'# Sphinx inventory version 2\n# Project: Probe\n# Version: \n'
                    b'# The remainder of this file is compressed using zlib.\n')
OPERATORE = '''<section id="operator-manual">
<h1>Operator manual<a class="headerlink" href="#operator-manual" title="Link to this heading">¶</a></h1>
<section id="the-email-address">
<span id="help-field-adm-user-email-operatore"></span><h2>The email address<a class="headerlink"
 href="#the-email-address" title="Link to this heading">¶</a></h2>
<p>Write <strong>the email</strong> <script>alert(1)</script> <img alt="map" src="../_images/map.png" />.</p>
<section id="below">
<h3>Below<a class="headerlink" href="#below" title="Link to this heading">¶</a></h3>
<p>A subsection.</p>
</section>
</section>
<section id="another-chapter">
<h2>Another chapter<a class="headerlink" href="#another-chapter" title="Link to this heading">¶</a></h2>
<p>Not this one.</p>
</section>
</section>'''
BACKOFFICE = '''<section id="backoffice-manual">
<h1>Backoffice manual<a class="headerlink" href="#backoffice-manual" title="Link to this heading">¶</a></h1>
<section id="email-and-name">
<span id="help-field-adm-user-first-name"></span><span id="help-field-adm-user-email"></span>
<h2>Email and name<a class="headerlink" href="#email-and-name" title="Link to this heading">¶</a></h2>
<p>For the backoffice.</p>
</section>
<section id="not-a-help-section">
<span id="plain-label"></span><h2>Not a help section<a class="headerlink" href="#not-a-help-section">¶</a></h2>
<p>No help- prefix.</p>
</section>
</section>'''
LABELS = {
    'help-field-adm-user-email--operatore': 'guide/operatore.html#help-field-adm-user-email-operatore '
                                            'The email address',
    'help-field-adm-user-email': 'guide/backoffice.html#help-field-adm-user-email Email and name',
    'help-field-adm-user-first_name': 'guide/backoffice.html#help-field-adm-user-first-name Email and name',
    'plain-label': 'guide/backoffice.html#plain-label Not a help section',
}


def write_site(folder, pages, labels, extra_lines=''):
    """A manual in the shape Sphinx publishes it: objects.inv and the pages,
    labels = {label: 'uri title'}"""
    lines = ''.join(f'{label} std:label -1 {entry}\n' for label, entry in labels.items()) + extra_lines
    (folder / 'objects.inv').write_bytes(INVENTORY_HEADER + zlib.compress(lines.encode('utf-8')))
    for name, body in pages.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text('<html><body><div class="body">%s</div></body></html>' % body)


def serve(folder, handler_class=http.server.SimpleHTTPRequestHandler):
    handler = functools.partial(handler_class, directory=str(folder))
    handler_class.log_message = lambda *args: None
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_address[1]}/'


@pytest.fixture(scope='module')
def site(tmp_path_factory):
    folder = tmp_path_factory.mktemp('manual')
    write_site(folder, {'guide/operatore.html': OPERATORE, 'guide/backoffice.html': BACKOFFICE,
                        'index.html': '<section id="probe"><h1>Probe</h1></section>'},
               LABELS, extra_lines='gnr.web.gnrmanual py:module 0 api.html#module-gnr.web.gnrmanual -\n')
    (folder / '_images').mkdir()
    (folder / '_images' / 'map.png').write_bytes(base64.b64decode(PNG))
    return folder


@pytest.fixture(scope='module')
def served(site):
    server, url = serve(site)
    yield url
    server.shutdown()


@pytest.fixture
def cache():
    return ManualCache()


@pytest.mark.parametrize('address, label', [
    ('field:invc.invoice:customer_id', 'help-field-invc-invoice-customer_id'),
    ('table:invc.invoice:', 'help-table-invc-invoice'),
    ('grouplet:test:card_profile', 'help-grouplet-test-card_profile'),
    ('page:demetra/agenda:giornata', 'help-page-demetra-agenda-giornata'),
    ('package:Demetra:', 'help-package-demetra'),
])
def test_an_address_has_one_label(address, label):
    assert address_label(address) == label


def test_the_inventory_gives_the_help_labels_only(site):
    labels = parse_inventory((site / 'objects.inv').read_bytes())
    assert set(labels) == {'help-field-adm-user-email', 'help-field-adm-user-email--operatore',
                           'help-field-adm-user-first_name'}
    uri, title = labels['help-field-adm-user-first_name']
    assert uri == 'guide/backoffice.html#help-field-adm-user-first-name', 'the html anchor Sphinx made'
    assert title == 'Email and name'
    with pytest.raises(ValueError):
        parse_inventory(b'not an inventory')


def test_the_site_of_a_page_is_found_above_it(site, cache):
    root, labels = site_of(str(site / 'guide' / 'operatore.html'), cache)
    assert root == str(site) + '/'
    assert 'help-field-adm-user-email' in labels
    assert site_of(str(site.parent / 'nowhere' / 'page.html'), cache) is None


def test_the_users_own_manual_wins_then_the_plain_label(site):
    operatore = str(site / 'guide' / 'operatore.html')
    backoffice = str(site / 'guide' / 'backoffice.html')
    assert Manual([operatore]).find('field:adm.user:email')['label'] == 'help-field-adm-user-email--operatore'
    assert Manual([backoffice]).find('field:adm.user:email')['label'] == 'help-field-adm-user-email'
    assert Manual([str(site / 'index.html')]).find('field:adm.user:email')['label'] == \
        'help-field-adm-user-email', 'outside both manuals the label without variant'
    assert Manual([], [operatore, backoffice]).find('field:adm.user:email')['label'] == \
        'help-field-adm-user-email', 'pages that are not the user\'s own decide nothing'
    assert Manual([operatore]).find('field:adm.user:first_name')['url'].endswith(
        'guide/backoffice.html#help-field-adm-user-first-name')
    assert Manual([operatore]).find('field:adm.user:username') is None
    assert Manual([]).find('field:adm.user:email') is None


def test_the_variant_of_another_groups_manual_is_never_shown(tmp_path):
    write_site(tmp_path, {'operatore.html': OPERATORE, 'backoffice.html': BACKOFFICE},
               {'help-field-adm-user-phone--operatore': 'operatore.html#help-field-adm-user-email-operatore Phone'})
    assert Manual([str(tmp_path / 'operatore.html')]).find('field:adm.user:phone')['label'] == \
        'help-field-adm-user-phone--operatore'
    assert Manual([str(tmp_path / 'backoffice.html')]).find('field:adm.user:phone') is None
    assert Manual([], [str(tmp_path / 'operatore.html')]).find('field:adm.user:phone') is None


def test_the_section_stands_alone(site):
    section = Manual([str(site / 'guide' / 'operatore.html')]).section('field:adm.user:email')
    assert section['title'] == 'The email address'
    html = section['html']
    assert '<strong>the email</strong>' in html and 'A subsection' in html
    assert 'Not this one' not in html, 'the next chapter is not part of it'
    assert '<script' not in html and 'headerlink' not in html and 'help-field' not in html
    assert f'src="{site}/_images/map.png"' in html, 'images made absolute'
    two_labels = Manual([str(site / 'guide' / 'backoffice.html')]).section('field:adm.user:first_name')
    assert (two_labels['title'], two_labels['html'].strip()) == ('Email and name', '<p>For the backoffice.</p>'), \
        'a section with two labels'


def test_a_section_is_cut_where_its_label_sits():
    page = ('<html><body><section id="a"><h2>A</h2><p onclick="x()">one '
            '<a href="javascript:alert(1)">bad</a> <a href="b.html">ok</a></p></section></body></html>')
    cut = cut_section(page, 'https://docs.example.org/guide/', 'a')
    assert cut['title'] == 'A'
    assert 'onclick' not in cut['html'] and 'javascript' not in cut['html']
    assert 'href="https://docs.example.org/guide/b.html"' in cut['html']
    assert cut_section(page, 'https://docs.example.org/', 'missing') is None


@pytest.mark.parametrize('markup, kept', [
    ('<svg><a xlink:href="javascript:alert(1)"><text>x</text></a></svg>', ''),
    ('<math><mtext><a href="javascript:alert(1)">m</a></mtext></math>', ''),
    ('<base href="https://evil.example.org/">', ''),
    ('<meta http-equiv="refresh" content="0;url=https://evil.example.org/">', ''),
    ('<link rel="stylesheet" href="https://evil.example.org/x.css">', ''),
    ('<iframe src="https://evil.example.org/"></iframe>', ''),
    ('<form action="/x"><button formaction="javascript:alert(1)">go</button></form>', ''),
    ('<p style="position:fixed;inset:0" class="dijitDialogUnderlay" id="mainWindow">covered</p>',
     '<p>covered</p>'),
    ('<a href="data:text/html,&lt;script&gt;alert(1)&lt;/script&gt;">data</a>', '<a>data</a>'),
    ('<a href="  JaVaScRiPt:alert(1)">mixed case</a>', '<a>mixed case</a>'),
    ('<a href="//evil.example.org/x">other host</a>', '<a href="https://evil.example.org/x">other host</a>'),
    ('<img src="x.png" onerror="alert(1)" srcset="javascript:alert(1)">',
     '<img src="https://docs.example.org/guide/x.png">'),
    ('<p>a<!-- <script>alert(1)</script> -->b</p>', '<p>ab</p>'),
    ('<details><summary>More</summary><nav>inside <em>nav</em></nav></details>',
     '<details><summary>More</summary>inside <em>nav</em></details>'),
    ('<table><tr><td colspan="2" onclick="x()">c</td></tr></table>',
     '<table><tr><td colspan="2">c</td></tr></table>'),
])
def test_a_section_keeps_only_the_allow_list(markup, kept):
    page = '<html><body><section id="a"><h2>A</h2>%s</section></body></html>' % markup
    html = cut_section(page, 'https://docs.example.org/guide/', 'a')['html']
    assert html == kept


def test_a_manual_served_by_the_site_keeps_the_links_of_the_site():
    page = '<html><body><section id="a"><h2>A</h2><img src="map.png"><a href="//x/y">y</a></section></body></html>'
    assert cut_section(page, '/_storage/site/manual/guide/', 'a')['html'] == \
        '<img src="/_storage/site/manual/guide/map.png"><a>y</a>'


def test_the_inventory_cannot_send_the_server_out_of_the_site(tmp_path, monkeypatch):
    entries = {'help-table-a-a': 'javascript:alert(1)#x A',
               'help-table-a-b': 'http://169.254.169.254/latest/meta-data#x B',
               'help-table-a-c': '../../outside.html#x C',
               'help-table-a-d': 'file:///etc/passwd#x D',
               'help-table-a-e': '//intranet.example.org/x.html#x E',
               'help-table-a-ok': 'guide/ok.html#ok OK'}
    write_site(tmp_path, {'guide/ok.html': '<section id="ok"><h2>OK</h2><p>fine</p></section>'}, entries)
    (tmp_path.parent / 'outside.html').write_text('<section id="x"><h2>Out</h2></section>')
    asked = []
    monkeypatch.setattr(gnrmanual.requests, 'get', lambda url, **kw: asked.append(url))
    manual = Manual([str(tmp_path / 'guide' / 'ok.html')])
    for code in 'abcde':
        assert manual.find(f'table:a.{code}:') is None, code
        assert manual.section(f'table:a.{code}:') is None, code
    assert manual.section('table:a.ok:')['html'] == '<p>fine</p>'
    assert asked == [], 'nothing is asked off the site'


def test_a_remote_site_is_read_without_redirects_and_up_to_a_size(tmp_path, monkeypatch):
    write_site(tmp_path, {'big.html': '<section id="big"><h2>Big</h2><p>%s</p></section>' % ('x' * 2000),
                          'ok.html': '<section id="ok"><h2>OK</h2><p>fine</p></section>'},
               {'help-table-a-big': 'big.html#big Big', 'help-table-a-ok': 'ok.html#ok OK',
                'help-table-a-moved': 'moved.html#ok Moved'})

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/moved.html'):
                self.send_response(302)
                self.send_header('Location', 'http://169.254.169.254/latest/meta-data')
                self.end_headers()
                return
            super().do_GET()

    server, url = serve(tmp_path, Handler)
    asked = []
    get = requests.get
    monkeypatch.setattr(gnrmanual.requests, 'get', lambda target, **kw: asked.append(target) or get(target, **kw))
    monkeypatch.setattr(gnrmanual, 'MAX_BYTES', 1000)
    try:
        manual = Manual([url + 'ok.html'])
        assert manual.section('table:a.ok:')['html'] == '<p>fine</p>'
        assert manual.section('table:a.moved:') is None
        assert manual.section('table:a.big:') is None, 'a page past MAX_BYTES is not read'
        assert all(target.startswith(url) for target in asked), asked
    finally:
        server.shutdown()


def test_the_manual_is_read_over_http_and_cached(served, site, cache):
    page = served + 'guide/operatore.html'
    section = Manual([page], cache=cache).section('field:adm.user:email')
    assert section['url'] == served + 'guide/operatore.html#help-field-adm-user-email-operatore'
    assert f'src="{served}_images/map.png"' in section['html']
    shutil.move(str(site / 'objects.inv'), str(site / 'objects.moved'))
    try:
        assert Manual([page], cache=cache).find('field:adm.user:email'), 'the inventory comes from the cache'
        assert Manual([page]).find('field:adm.user:email') is None, 'a cache of its own reads it again'
    finally:
        shutil.move(str(site / 'objects.moved'), str(site / 'objects.inv'))


def test_a_fetch_expires_a_failure_sooner(site, cache, monkeypatch):
    url = str(site / 'objects.inv')
    missing = str(site / 'missing.inv')
    assert fetch(url, cache) and fetch(missing, cache) is None
    now = time.time()
    (site / 'missing.inv').write_bytes(b'now here')
    try:
        monkeypatch.setattr(gnrmanual.time, 'time', lambda: now + gnrmanual.FAILURE_TTL + 1)
        assert fetch(missing, cache) == b'now here', 'a failure is kept FAILURE_TTL seconds'
        shutil.move(url, url + '.moved')
        assert fetch(url, cache), 'a page CACHE_TTL'
        monkeypatch.setattr(gnrmanual.time, 'time', lambda: now + gnrmanual.CACHE_TTL + 1)
        assert fetch(url, cache) is None
    finally:
        shutil.move(url + '.moved', url)
        (site / 'missing.inv').unlink()


def test_the_cache_holds_up_to_its_bytes(tmp_path):
    cache = ManualCache(max_bytes=10)
    for name in 'abc':
        (tmp_path / name).write_bytes(b'12345')
        fetch(str(tmp_path / name), cache)
    assert [cache.get(str(tmp_path / name))[0] for name in 'abc'] == [False, True, True]
    assert cache.get(str(tmp_path / 'b')) == (True, b'12345')


def test_a_host_that_does_not_answer_is_asked_once(monkeypatch, cache):
    asked = []

    def unreachable(url, **kwargs):
        asked.append(url)
        raise requests.ConnectionError('no route to host')

    monkeypatch.setattr(gnrmanual.requests, 'get', unreachable)
    pages = ['https://docs.down.example/a/b/c/one.html', 'https://docs.down.example/two.html']
    manual = Manual(pages, cache=cache)
    assert manual.sites == [] and manual.find('field:adm.user:email') is None
    assert asked == ['https://docs.down.example/a/b/c/objects.inv'], 'not the folders above, not the second page'
    now = time.time()
    monkeypatch.setattr(gnrmanual.time, 'time', lambda: now + gnrmanual.FAILURE_TTL + 1)
    Manual(pages[:1], cache=cache)
    assert len(asked) == 2, 'asked again after FAILURE_TTL'


def test_only_http_urls_and_absolute_paths_are_manual_pages(monkeypatch):
    monkeypatch.setattr(gnrmanual.requests, 'get', lambda url, **kw: pytest.fail(url))
    for page in ('ftp://docs.example.org/manual/index.html', 'manual/index.html', 'file:///etc/index.html',
                 'javascript:alert(1)', None, ''):
        assert Manual([page]).sites == [], page


@pytest.mark.parametrize('url, storage', [
    ('site:manual/index.html', True),
    ('home:docs/users.html', True),
    ('https://docs.example.org/manual/index.html', False),
    ('/var/www/manual/index.html', False),
    ('manual/index.html', False),
    ('', False),
    (None, False),
])
def test_a_storage_path_names_a_storage_of_the_site(url, storage):
    assert is_storage_path(url) is storage


def test_a_manual_built_by_sphinx(tmp_path):
    sphinx = pytest.importorskip('sphinx.cmd.build')
    pytest.importorskip('myst_parser')
    pages = {'index.md': '# Probe manual\n\n```{toctree}\nguide/operatore\nguide/backoffice\n```\n',
             'guide/operatore.md': '# Operator manual\n\n(help-field-adm-user-email--operatore)=\n'
                                   '## The email address\n\nWrite **the email** <script>alert(1)</script> '
                                   '![map](map.png).\n\n### Below\n\nA subsection.\n\n'
                                   '## Another chapter\n\nNot this one.\n',
             'guide/backoffice.md': '# Backoffice manual\n\n(help-field-adm-user-email)=\n'
                                    '(help-field-adm-user-first_name)=\n## Email and name\n\nFor the backoffice.\n'}
    source = tmp_path / 'src'
    (source / 'guide').mkdir(parents=True)
    (source / 'conf.py').write_text("project = 'Probe'\nextensions = ['myst_parser']\nmyst_heading_anchors = 3\n")
    (source / 'guide' / 'map.png').write_bytes(base64.b64decode(PNG))
    for name, text in pages.items():
        (source / name).write_text(text)
    build = tmp_path / 'build'
    assert sphinx.build_main(['-q', '-b', 'html', str(source), str(build)]) == 0
    operatore = str(build / 'guide' / 'operatore.html')
    section = Manual([operatore]).section('field:adm.user:email')
    assert section['title'] == 'The email address'
    assert '<strong>the email</strong>' in section['html'] and 'Not this one' not in section['html']
    assert '<script' not in section['html'] and f'src="{build}/_images/map.png"' in section['html']
    assert Manual([operatore]).find('field:adm.user:first_name')['url'].endswith(
        'guide/backoffice.html#help-field-adm-user-first-name')
