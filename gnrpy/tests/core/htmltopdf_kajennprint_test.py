"""Tests for the ``kajennprint`` htmltopdf implementation (a kajenn print server backend).

The service is resolved from ``resources/common/services`` like the weasyprint
one (see ``pdfsite``). The print server is replaced by a fake ``requests.post``
recording what the service sends, so the tests check the contract: the same
page stylesheets as the weasyprint implementation, presentational hints, the
bearer token, local resources embedded, and the pdf written where weasyprint
would write it.

``test_live_server_matches_weasyprint`` renders through a real print server and
compares the text position with the weasyprint implementation; it runs only
when ``KAJENN_PRINT_TEST_URL`` points to a server with public access (or
``KAJENN_PRINT_TEST_TOKEN`` holds an api key carrying the ``print`` tag).
"""

import base64
import http.server
import os
import threading

import pytest

from core.pdfsite import make_pdf_site
from gnr.core.gnrbag import Bag
from gnr.lib.services import BaseServiceType
from gnr.lib.services.htmltopdf import HtmlToPdfError, HtmlToPdfService, ServiceType

PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
FAKE_PDF = b'%PDF-1.7 fake'


def get_service(tmp_path, implementation='kajennprint', **parameters):
    site = make_pdf_site(tmp_path)
    factory = BaseServiceType(site=site, service_type='htmltopdf').getServiceFactory(implementation)
    return factory(site, **parameters)


def htmltopdf_service_type(tmp_path):
    """The htmltopdf service type on a site with no service configured."""
    site = make_pdf_site(tmp_path)
    site.config = Bag()
    site.getPreference = lambda path, pkg=None: None
    return ServiceType(site=site, service_type='htmltopdf')


def service_module(tmp_path):
    return __import__(type(get_service(tmp_path)).__module__, fromlist=['ResourceInliner'])


class FakeResponse(object):
    def __init__(self, status_code=200, content=FAKE_PDF, content_type='application/pdf', json=None):
        self.status_code = status_code
        self.content = content
        self.text = content.decode('latin-1')
        self.reason = 'reason'
        self.headers = {'Content-Type': content_type}
        self._json = json

    def json(self):
        if self._json is None:
            raise ValueError('no json')
        return self._json


@pytest.fixture
def print_server(monkeypatch):
    """A fake print server: records the requests, answers ``calls.response``."""
    import requests

    class Calls(list):
        response = FakeResponse()

    calls = Calls()

    def post(url, json=None, headers=None, timeout=None, **kwargs):
        calls.append(dict(url=url, json=json, headers=headers, timeout=timeout))
        return calls.response

    monkeypatch.setattr(requests, 'post', post)
    return calls


@pytest.fixture
def http_files():
    """A local http server answering files from a dict ``{path: (bytes, mime)}``."""
    files = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in files:
                self.send_error(404)
                return
            body, mime = files[self.path]
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield 'http://127.0.0.1:%s' % server.server_address[1], files
    server.shutdown()
    server.server_close()


# --- request contract ---------------------------------------------------------

def test_writes_the_server_pdf_to_a_temp_file(tmp_path, print_server):
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    service = get_service(tmp_path, url='http://print.test/', token='gak_x')
    pdf_file = service.writePdf('src.html', None)
    try:
        assert pdf_file.read() == FAKE_PDF
    finally:
        pdf_file.close()
        os.unlink(pdf_file.name)
    call, = print_server
    assert call['url'] == 'http://print.test/print/pdf'
    assert call['headers'] == {'Authorization': 'Bearer gak_x'}
    assert call['json']['html'] == '<p>hello</p>'
    assert call['json']['presentational_hints'] is True
    assert call['json']['filename'] == 'src.pdf'
    assert call['json']['stylesheets'] == []


def test_writes_into_a_destination_folder(tmp_path, print_server):
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    (tmp_path / 'out').mkdir()
    result = get_service(tmp_path).writePdf('src.html', 'out')
    assert result.endswith('out/src.pdf')
    assert (tmp_path / 'out' / 'src.pdf').read_bytes() == FAKE_PDF


def test_writes_a_destination_file(tmp_path, print_server):
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    assert (tmp_path / 'doc.pdf').read_bytes() == FAKE_PDF


@pytest.mark.parametrize('write_kwargs', [
    dict(),
    dict(pageSize='A5'),
    dict(pageSize='A4 landscape', pageMargin='10mm 5mm'),
    dict(pdf_kwargs=dict(margin_top=30, margin_left='2cm')),
    dict(pageMargin=0, pdf_kwargs=dict(margin_top=30)),
    dict(stylesheets=['body { color: red }'], pageSize='A3'),
])
def test_page_stylesheets_match_the_weasyprint_implementation(tmp_path, print_server,
                                                              write_kwargs):
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    get_service(tmp_path).writePdf('src.html', 'doc.pdf', **write_kwargs)
    expected = HtmlToPdfService(parent=None).pageStylesheets(
        pageSize=write_kwargs.get('pageSize'), pageMargin=write_kwargs.get('pageMargin'),
        pdf_kwargs=write_kwargs.get('pdf_kwargs'), stylesheets=write_kwargs.get('stylesheets'))
    assert print_server[0]['json']['stylesheets'] == expected


def test_caller_stylesheets_are_not_modified(tmp_path, print_server):
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    stylesheets = ['body { color: red }']
    get_service(tmp_path).writePdf('src.html', 'doc.pdf', stylesheets=stylesheets, pageSize='A5')
    assert stylesheets == ['body { color: red }']


def test_htmltopdf_accepts_an_html_string(tmp_path, print_server):
    service = get_service(tmp_path)
    service.parent.getPreference = lambda path, pkg=None: None
    service.htmlToPdf('<p>inline</p>', 'doc.pdf')
    assert '<p>inline</p>' in print_server[0]['json']['html']
    assert (tmp_path / 'doc.pdf').read_bytes() == FAKE_PDF


def test_parameters_default_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('KAJENN_PRINT_URL', 'http://env.test:9000')
    monkeypatch.setenv('KAJENN_PRINT_TOKEN', 'gak_env')
    service = get_service(tmp_path, mount='/printing/')
    assert service.endpoint == 'http://env.test:9000/printing/pdf'
    assert service.token == 'gak_env'


@pytest.mark.parametrize(('response', 'message'), [
    (FakeResponse(status_code=401), 'authentication required'),
    (FakeResponse(status_code=403), 'print tag'),
    (FakeResponse(status_code=400, json={'error': 'an HTML source is required'}),
     'an HTML source is required'),
    (FakeResponse(content=b'<html>', content_type='text/html'), 'did not answer a pdf'),
])
def test_server_errors_raise_htmltopdf_errors(tmp_path, print_server, response, message):
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    print_server.response = response
    with pytest.raises(HtmlToPdfError, match=message):
        get_service(tmp_path).writePdf('src.html', 'doc.pdf')


@pytest.mark.parametrize(('token', 'message'), [
    (None, 'authentication required'),
    ('gak_stale', 'the token was rejected'),
])
def test_401_tells_a_missing_token_from_a_rejected_one(tmp_path, print_server, monkeypatch,
                                                       token, message):
    monkeypatch.delenv('KAJENN_PRINT_TOKEN', raising=False)
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    print_server.response = FakeResponse(status_code=401)
    with pytest.raises(HtmlToPdfError, match=message):
        get_service(tmp_path, token=token).writePdf('src.html', 'doc.pdf')


def test_netrc_credentials_are_never_sent(tmp_path, monkeypatch):
    """requests reads ~/.netrc when a request carries no auth: the server would
    answer those credentials with a 401 even on a public mount."""
    netrc = tmp_path / 'netrc'
    netrc.write_text('default login someone password secret\n')
    netrc.chmod(0o600)
    monkeypatch.setenv('NETRC', str(netrc))
    monkeypatch.delenv('KAJENN_PRINT_TOKEN', raising=False)
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(self.headers.get('Authorization'))
            self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', str(len(FAKE_PDF)))
            self.end_headers()
            self.wfile.write(FAKE_PDF)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = 'http://127.0.0.1:%s' % server.server_address[1]
        (tmp_path / 'src.html').write_text('<p>hello</p>')
        get_service(tmp_path, url=url).writePdf('src.html', 'doc.pdf')
        get_service(tmp_path, url=url, token='gak_x').writePdf('src.html', 'doc.pdf')
    finally:
        server.shutdown()
        server.server_close()
    assert seen == [None, 'Bearer gak_x']


def test_unreachable_server_raises(tmp_path):
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    service = get_service(tmp_path, url='http://127.0.0.1:9', timeout=2)
    with pytest.raises(HtmlToPdfError, match='unreachable'):
        service.writePdf('src.html', 'doc.pdf')


def test_env_variable_selects_the_kajennprint_implementation(tmp_path, monkeypatch, print_server):
    monkeypatch.setenv('KAJENN_PRINT_URL', ' http://kajenn.test:8000/ ')
    service_type = htmltopdf_service_type(tmp_path)
    assert service_type.conf_htmltopdf() == dict(implementation='kajennprint',
                                                 url='http://kajenn.test:8000/')
    service = service_type.addService('htmltopdf')
    assert service.service_implementation == 'kajennprint'
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    service.writePdf('src.html', 'doc.pdf')
    assert print_server[0]['url'] == 'http://kajenn.test:8000/print/pdf'


@pytest.mark.parametrize('value', [None, '', '  '])
def test_without_env_variable_the_default_is_unchanged(tmp_path, monkeypatch, value):
    if value is None:
        monkeypatch.delenv('KAJENN_PRINT_URL', raising=False)
    else:
        monkeypatch.setenv('KAJENN_PRINT_URL', value)
    service_type = htmltopdf_service_type(tmp_path)
    assert service_type.conf_htmltopdf()['implementation'] in ('weasyprint', 'wk')


# --- embedded resources -------------------------------------------------------

def data_url(content, mime):
    return 'data:%s;base64,%s' % (mime, base64.b64encode(content).decode('ascii'))


def test_local_resources_are_embedded(tmp_path, print_server, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'img').mkdir()
    (tmp_path / 'img' / 'logo.png').write_bytes(PNG)
    (tmp_path / 'css').mkdir()
    (tmp_path / 'css' / 'base.css').write_text('p { background: url(../img/logo.png) }')
    (tmp_path / 'css' / 'print.css').write_text('@import "base.css" print;\nh1 { color: red }')
    (tmp_path / 'src.html').write_text(
        '<html><head><link rel="stylesheet" type="text/css" href="css/print.css" media="all">'
        '<style>div { background-image: url("img/logo.png") }</style></head>'
        '<body><img src="img/logo.png"><img src="%s">'
        '<span style="background: url(\'img/logo.png\')">x</span>'
        '<img src="data:image/png;base64,AAAA"><img src="missing.png"></body></html>'
        % (tmp_path / 'img' / 'logo.png'))
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    html = print_server[0]['json']['html']
    png = data_url(PNG, 'image/png')
    assert '<link' not in html
    assert '<style media="all">' in html
    assert '@media print {\np { background: url("%s") }\n}' % png in html
    assert 'h1 { color: red }' in html
    assert 'div { background-image: url("%s") }' % png in html
    assert html.count('<img src="%s">' % png) == 2
    assert 'style="background: url(&quot;%s&quot;)"' % png in html
    assert '<img src="data:image/png;base64,AAAA">' in html
    assert '<img src="missing.png">' in html


def test_site_resources_are_fetched_over_http(tmp_path, print_server, http_files):
    base, files = http_files
    files['/_rsrc/print.css'] = (b'@font-face { src: url(fonts/a.woff2) }', 'text/css')
    files['/_rsrc/fonts/a.woff2'] = (b'woff2', 'font/woff2')
    files['/_storage/logo.png'] = (PNG, 'image/png')
    (tmp_path / 'src.html').write_text(
        '<link href="%s/_rsrc/print.css" rel="stylesheet"><img src="/_storage/logo.png">'
        '<img src="%s/_storage/missing.png">' % (base, base))
    get_service(tmp_path, base_url=base + '/').writePdf('src.html', 'doc.pdf')
    sent = print_server[0]['json']
    assert sent['base_url'] == base + '/'
    assert 'url("%s")' % data_url(b'woff2', 'font/woff2') in sent['html']
    assert '<img src="%s">' % data_url(PNG, 'image/png') in sent['html']
    assert '<img src="%s/_storage/missing.png">' % base in sent['html']


def test_stylesheet_urls_are_embedded_too(tmp_path, print_server, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'bg.png').write_bytes(PNG)
    (tmp_path / 'src.html').write_text('<p>x</p>')
    get_service(tmp_path).writePdf('src.html', 'doc.pdf',
                                   stylesheets=['body { background: url(bg.png) }'])
    assert print_server[0]['json']['stylesheets'] == [
        'body { background: url("%s") }' % data_url(PNG, 'image/png')]


def test_embedding_can_be_turned_off(tmp_path, print_server, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'logo.png').write_bytes(PNG)
    source = '<link rel="stylesheet" href="a.css"><img src="logo.png">'
    (tmp_path / 'src.html').write_text(source)
    get_service(tmp_path, inline_resources=False).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == source


def test_import_cycles_stop(tmp_path):
    (tmp_path / 'a.css').write_text('@import "b.css";\na { color: red }')
    (tmp_path / 'b.css').write_text('@import "a.css";\nb { color: blue }')
    inliner = service_module(tmp_path).ResourceInliner(tmp_path.as_uri() + '/')
    css = inliner.inline_css('@import "a.css";', tmp_path.as_uri() + '/')
    assert 'a { color: red }' in css and 'b { color: blue }' in css


# --- live print server --------------------------------------------------------

LIVE_URL = os.environ.get('KAJENN_PRINT_TEST_URL')


@pytest.mark.skipif(not LIVE_URL, reason='KAJENN_PRINT_TEST_URL not set')
@pytest.mark.parametrize('write_kwargs', [
    dict(pdf_kwargs=dict(margin_top=30, margin_left=20)),
    dict(pageSize='A5', pageMargin='25mm'),
    dict(pdf_kwargs={}),
])
def test_live_server_matches_weasyprint(tmp_path, monkeypatch, write_kwargs):
    pytest.importorskip('weasyprint')
    fitz = pytest.importorskip('fitz')
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'logo.png').write_bytes(PNG)
    (tmp_path / 'print.css').write_text('div { font-size: 14pt }')
    (tmp_path / 'src.html').write_text(
        '<html><head><link rel="stylesheet" href="print.css"><style>'
        '@page { size: A4; margin: 0; } body { margin: 0; padding: 0; }</style></head>'
        '<body><table width="400"><tr><td align="right"><div>MARKER</div></td></tr></table>'
        '<img src="logo.png" width="20"></body></html>')

    def layout(implementation, **parameters):
        service = get_service(tmp_path, implementation, **parameters)
        pdf_file = service.writePdf('src.html', None, **write_kwargs)
        try:
            with fitz.open(pdf_file.name) as doc:
                page = doc[0]
                marker = [w for w in page.get_text('words') if w[4] == 'MARKER'][0]
                return (tuple(round(v) for v in page.rect), tuple(round(v) for v in marker[:4]),
                        len(page.get_images()))
        finally:
            pdf_file.close()
            os.unlink(pdf_file.name)

    remote = layout('kajennprint', url=LIVE_URL, token=os.environ.get('KAJENN_PRINT_TEST_TOKEN'))
    assert remote == layout('weasyprint')
    assert remote[2] == 1
