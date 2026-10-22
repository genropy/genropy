"""gnr.web.gnrmanual: the published manual's sections of the app's doc addresses.

A small manual is built with Sphinx and myst-parser, as the applications'
manuals are, and read from the build folder and over a real local HTTP server.
"""

import base64
import functools
import http.server
import shutil
import threading
import time

import pytest

from gnr.web import gnrmanual
from gnr.web.gnrmanual import Manual, address_label, cut_section, fetch, parse_inventory, site_of

sphinx = pytest.importorskip('sphinx.cmd.build')
pytest.importorskip('myst_parser')

PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
PAGES = {
    'index.md': '# Probe manual\n\n```{toctree}\nguide/operatore\nguide/backoffice\n```\n',
    'guide/operatore.md': '# Operator manual\n\n'
                          '(help-field-adm-user-email--operatore)=\n'
                          '## The email address\n\n'
                          'Write **the email** <script>alert(1)</script> ![map](map.png).\n\n'
                          '### Below\n\nA subsection.\n\n'
                          '## Another chapter\n\nNot this one.\n',
    'guide/backoffice.md': '# Backoffice manual\n\n'
                           '(help-field-adm-user-email)=\n'
                           '(help-field-adm-user-first_name)=\n'
                           '## Email and name\n\nFor the backoffice.\n\n'
                           '(plain-label)=\n'
                           '## Not a help section\n\nNo help- prefix.\n',
}


@pytest.fixture(scope='module')
def site(tmp_path_factory):
    source = tmp_path_factory.mktemp('manual_src')
    (source / 'conf.py').write_text("project = 'Probe'\nextensions = ['myst_parser']\nmyst_heading_anchors = 3\n")
    (source / 'guide').mkdir()
    (source / 'guide' / 'map.png').write_bytes(base64.b64decode(PNG))
    for name, text in PAGES.items():
        (source / name).parent.mkdir(parents=True, exist_ok=True)
        (source / name).write_text(text)
    build = tmp_path_factory.mktemp('manual_build')
    assert sphinx.build_main(['-q', '-b', 'html', str(source), str(build)]) == 0
    return build


@pytest.fixture(scope='module')
def served(site):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    handler.log_message = lambda *args: None
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_address[1]}/'
    server.shutdown()


@pytest.fixture(autouse=True)
def fresh_cache():
    gnrmanual._cache.clear()
    yield
    gnrmanual._cache.clear()


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


def test_the_site_of_a_page_is_found_above_it(site):
    root, labels = site_of(str(site / 'guide' / 'operatore.html'))
    assert root == str(site) + '/'
    assert 'help-field-adm-user-email' in labels
    assert site_of(str(site.parent / 'nowhere' / 'page.html')) is None


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


def test_the_section_stands_alone(site):
    section = Manual([str(site / 'guide' / 'operatore.html')]).section('field:adm.user:email')
    assert section['title'] == 'The email address'
    html = section['html']
    assert '<strong>the email</strong>' in html and 'A subsection' in html
    assert 'Not this one' not in html, 'the next chapter is not part of it'
    assert '<script' not in html and 'headerlink' not in html and 'help-field' not in html
    assert f'src="{site}/_images/map.png"' in html, 'images made absolute'


def test_a_section_is_cut_where_its_label_sits():
    page = ('<html><body><section id="a"><h2>A</h2><p onclick="x()">one '
            '<a href="javascript:alert(1)">bad</a> <a href="b.html">ok</a></p></section></body></html>')
    cut = cut_section(page, 'https://docs.example.org/guide/', 'a')
    assert cut['title'] == 'A'
    assert 'onclick' not in cut['html'] and 'javascript' not in cut['html']
    assert 'href="https://docs.example.org/guide/b.html"' in cut['html']
    assert cut_section(page, 'https://docs.example.org/', 'missing') is None


def test_the_manual_is_read_over_http_and_cached(served, site):
    page = served + 'guide/operatore.html'
    section = Manual([page]).section('field:adm.user:email')
    assert section['url'] == served + 'guide/operatore.html#help-field-adm-user-email-operatore'
    assert f'src="{served}_images/map.png"' in section['html']
    shutil.move(str(site / 'objects.inv'), str(site / 'objects.moved'))
    try:
        assert Manual([page]).find('field:adm.user:email'), 'the inventory comes from the cache'
        gnrmanual._cache.clear()
        assert Manual([page]).find('field:adm.user:email') is None
    finally:
        shutil.move(str(site / 'objects.moved'), str(site / 'objects.inv'))


def test_a_fetch_expires(site, monkeypatch):
    url = str(site / 'objects.inv')
    assert fetch(url)
    now = time.time()
    monkeypatch.setattr(gnrmanual.time, 'time', lambda: now + gnrmanual.CACHE_TTL + 1)
    shutil.move(url, url + '.moved')
    try:
        assert fetch(url) is None
    finally:
        shutil.move(url + '.moved', url)
