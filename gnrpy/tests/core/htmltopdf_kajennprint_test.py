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
import time
from types import MethodType

import pytest
import requests

from core.pdfsite import make_pdf_site
from gnr.app.gnrapp import GnrApp
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


def htmltopdf_service_type(tmp_path, kajenn_print_url=None):
    """The htmltopdf service type on a site with no service configured.

    :param kajenn_print_url: the ``<experimental><htmltopdf kajenn_print_url/>`` value"""
    site = make_pdf_site(tmp_path)
    site.config = Bag()
    site.getPreference = lambda path, pkg=None: None
    app_config = Bag()
    if kajenn_print_url is not None:
        app_config.setItem('experimental.htmltopdf', None, kajenn_print_url=kajenn_print_url)
    site.gnrapp.config = app_config
    site.gnrapp.experimentalValue = MethodType(GnrApp.experimentalValue, site.gnrapp)
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
    """A local http server answering files from a dict ``{path: (bytes, mime)}``;
    ``(location, 'redirect')`` answers a 302 to ``location``."""
    class Files(dict):
        """The served files, with the Authorization header of each request."""

    files = Files()
    files.authorizations = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            files.authorizations.append(self.headers.get('Authorization'))
            if self.path not in files:
                self.send_error(404)
                return
            body, mime = files[self.path]
            if mime == 'redirect':
                self.send_response(302)
                self.send_header('Location', body)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
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


def test_experimental_switch_selects_the_kajennprint_implementation(tmp_path, monkeypatch,
                                                                    print_server):
    monkeypatch.delenv('KAJENN_PRINT_URL', raising=False)
    service_type = htmltopdf_service_type(tmp_path, kajenn_print_url=' http://kajenn.test:8000/ ')
    assert service_type.conf_htmltopdf() == dict(implementation='kajennprint',
                                                 url='http://kajenn.test:8000/')
    service = service_type.addService('htmltopdf')
    assert service.service_implementation == 'kajennprint'
    (tmp_path / 'src.html').write_text('<p>hello</p>')
    service.writePdf('src.html', 'doc.pdf')
    assert print_server[0]['url'] == 'http://kajenn.test:8000/print/pdf'


@pytest.mark.parametrize('value', [None, '', '  '])
def test_without_experimental_switch_the_default_is_unchanged(tmp_path, monkeypatch, value):
    service_type = htmltopdf_service_type(tmp_path, kajenn_print_url=value)
    assert service_type.conf_htmltopdf()['implementation'] in ('weasyprint', 'wk')


def test_env_variable_alone_does_not_switch_the_default(tmp_path, monkeypatch):
    """The environment only provides the url default of a configured kajennprint service."""
    monkeypatch.setenv('KAJENN_PRINT_URL', 'http://kajenn.test:8000')
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


@pytest.mark.parametrize('value', [True, 'true', '1'])
def test_embedding_can_be_turned_off(tmp_path, print_server, monkeypatch, value):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'logo.png').write_bytes(PNG)
    source = '<link rel="stylesheet" href="a.css"><img src="logo.png">'
    (tmp_path / 'src.html').write_text(source)
    get_service(tmp_path, no_inline_resources=value).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == source


@pytest.mark.parametrize('value', [None, '', False])
def test_an_unset_checkbox_embeds(tmp_path, print_server, monkeypatch, value):
    """An unchecked box and a value missing from the service record both embed."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'logo.png').write_bytes(PNG)
    (tmp_path / 'src.html').write_text('<img src="logo.png">')
    get_service(tmp_path, no_inline_resources=value).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == '<img src="%s">' % data_url(PNG, 'image/png')


def test_local_files_outside_the_site_folders_are_not_read(tmp_path, print_server, monkeypatch):
    site_dir = tmp_path / 'site'
    outside = tmp_path / 'outside'
    site_dir.mkdir()
    outside.mkdir()
    (outside / 'private.png').write_bytes(PNG)
    (site_dir / 'link.png').symlink_to(outside / 'private.png')
    monkeypatch.chdir(site_dir)
    source = ('<img src="%s"><img src="link.png"><img src="../outside/private.png">'
              % (outside / 'private.png'))
    (site_dir / 'src.html').write_text(source)
    get_service(site_dir).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == source


def test_local_roots_extend_the_readable_folders(tmp_path, print_server, monkeypatch):
    site_dir = tmp_path / 'site'
    shared = tmp_path / 'shared'
    site_dir.mkdir()
    shared.mkdir()
    (shared / 'logo.png').write_bytes(PNG)
    monkeypatch.chdir(site_dir)
    (site_dir / 'src.html').write_text('<img src="%s">' % (shared / 'logo.png'))
    get_service(site_dir, local_roots='/nonexistent, %s' % shared).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == '<img src="%s">' % data_url(PNG, 'image/png')


def test_only_stylesheets_images_and_fonts_are_read(tmp_path, print_server, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'secret.txt').write_text('password')
    (tmp_path / 'instanceconfig.xml').write_text('<db password="x"/>')
    (tmp_path / 'font.woff2').write_bytes(b'woff2')
    source = ('<img src="secret.txt"><img src="instanceconfig.xml">'
              '<style>a { background: url("secret.txt") }</style>')
    (tmp_path / 'src.html').write_text(source + '<img src="font.woff2">')
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    html = print_server[0]['json']['html']
    assert html == source + '<img src="%s">' % data_url(b'woff2', 'font/woff2')


def test_http_resources_of_other_types_are_not_embedded(tmp_path, print_server, http_files):
    base, files = http_files
    files['/meta'] = (b'secret', 'text/plain')
    files['/logo'] = (PNG, 'image/png')
    files['/fonts/a.woff2'] = (b'woff2', 'application/octet-stream')
    source = '<img src="%s/meta">' % base
    (tmp_path / 'src.html').write_text(
        source + '<img src="%s/logo"><img src="%s/fonts/a.woff2">' % (base, base))
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == source + '<img src="%s"><img src="%s">' % (
        data_url(PNG, 'image/png'), data_url(b'woff2', 'font/woff2'))


def test_netrc_credentials_are_not_sent_to_resource_hosts(tmp_path, print_server, monkeypatch,
                                                          http_files):
    netrc = tmp_path / 'netrc'
    netrc.write_text('default login someone password secret\n')
    netrc.chmod(0o600)
    monkeypatch.setenv('NETRC', str(netrc))
    base, files = http_files
    files['/logo.png'] = (PNG, 'image/png')
    (tmp_path / 'src.html').write_text('<img src="%s/logo.png">' % base)
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    assert files.authorizations == [None]


def test_netrc_credentials_are_not_sent_after_a_redirect(tmp_path, print_server, monkeypatch,
                                                         http_files):
    """requests reads ~/.netrc again for the target of every redirect."""
    netrc = tmp_path / 'netrc'
    netrc.write_text('default login someone password secret\n')
    netrc.chmod(0o600)
    monkeypatch.setenv('NETRC', str(netrc))
    base, files = http_files
    other_host = base.replace('127.0.0.1', 'localhost')
    files['/redirect.png'] = (other_host + '/logo.png', 'redirect')
    files['/logo.png'] = (PNG, 'image/png')
    (tmp_path / 'src.html').write_text('<img src="%s/redirect.png">' % base)
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    assert files.authorizations == [None, None]
    assert print_server[0]['json']['html'] == '<img src="%s">' % data_url(PNG, 'image/png')


def test_a_redirect_does_not_borrow_the_type_of_the_first_url(tmp_path, print_server,
                                                              http_files):
    base, files = http_files
    files['/x.png'] = (base + '/internal/secret', 'redirect')
    files['/internal/secret'] = (b'secret', 'application/octet-stream')
    source = '<img src="%s/x.png">' % base
    (tmp_path / 'src.html').write_text(source)
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == source


def test_a_null_byte_in_a_path_leaves_the_reference(tmp_path, print_server, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = '<img src="x.png%00.css">'
    (tmp_path / 'src.html').write_text(source)
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == source


def test_oversized_resources_are_not_embedded(tmp_path, print_server, monkeypatch, http_files):
    monkeypatch.setattr(service_module(tmp_path), 'MAX_RESOURCE_SIZE', 100)
    base, files = http_files
    files['/big.png'] = (b'x' * 101, 'image/png')
    files['/small.png'] = (PNG, 'image/png')
    source = '<img src="%s/big.png">' % base
    (tmp_path / 'src.html').write_text(source + '<img src="%s/small.png">' % base)
    get_service(tmp_path).writePdf('src.html', 'doc.pdf')
    assert print_server[0]['json']['html'] == source + '<img src="%s">' % data_url(
        PNG, 'image/png')


def test_a_large_slow_body_is_bounded_by_the_resource_timeout(tmp_path, print_server):
    """The read timeout bounds each read: a body whose chunks keep arriving within
    it, but whose whole transfer exceeds the resource timeout, must stop there."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.end_headers()
            try:
                for _ in range(20):
                    self.wfile.write(b'x' * 64 * 1024)
                    self.wfile.flush()
                    time.sleep(0.3)
            except OSError:
                pass

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        source = '<img src="http://127.0.0.1:%s/slow.png">' % server.server_address[1]
        (tmp_path / 'src.html').write_text(source)
        start = time.monotonic()
        get_service(tmp_path, resource_timeout=1).writePdf('src.html', 'doc.pdf')
        assert time.monotonic() - start < 3
    finally:
        server.shutdown()
        server.server_close()
    assert print_server[0]['json']['html'] == source


def test_an_unreachable_host_is_asked_once(tmp_path, print_server, monkeypatch):
    session_class = service_module(tmp_path).NoCredentialsSession
    real_get = session_class.get
    calls = []

    def get(session, url, **kwargs):
        calls.append((url, kwargs['timeout']))
        return real_get(session, url, **kwargs)

    monkeypatch.setattr(session_class, 'get', get)
    dead = 'http://127.0.0.1:9'
    source = ''.join('<img src="%s/%s.png">' % (dead, n) for n in range(3))
    (tmp_path / 'src.html').write_text(source)
    get_service(tmp_path, timeout=300).writePdf('src.html', 'doc.pdf')
    assert calls == [(dead + '/0.png', 10.0)]
    assert print_server[0]['json']['html'] == source
    assert print_server[0]['timeout'] == 300.0


def test_resource_timeout_is_a_service_parameter(tmp_path):
    assert get_service(tmp_path, resource_timeout='3').resource_timeout == 3.0


def test_import_cycles_stop(tmp_path):
    (tmp_path / 'a.css').write_text('@import "b.css";\na { color: red }')
    (tmp_path / 'b.css').write_text('@import "a.css";\nb { color: blue }')
    inliner = service_module(tmp_path).ResourceInliner(tmp_path.as_uri() + '/',
                                                       local_roots=[tmp_path])
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
