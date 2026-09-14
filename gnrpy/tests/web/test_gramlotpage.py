"""Exercise the optional adapter through real Werkzeug requests and TYTX."""
from types import SimpleNamespace

import pytest
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

pytest.importorskip('gramlot')
from gramlot.page import endpoint, source
from gramlot.transport import to_tytx
from genro_tytx import from_tytx
from gnr.web.gramlotpage import GramlotPage


class PublicPage(GramlotPage):
    public = True

    def main(self, root):
        root.h2('Hello World')

    @endpoint
    def echo(self, value):
        return value

    @source
    def detail(self, root):
        root.p('Remote Source')


def dispatch(path='', method='GET', data=None, origin=None, page_class=PublicPage):
    headers = {'Content-Type': 'application/vnd.tytx+json'}
    if origin:
        headers['Origin'] = origin
    env = EnvironBuilder(path='/demo' + path, method=method, data=data,
                         headers=headers).get_environ()
    page = page_class(SimpleNamespace(db=object()), path.strip('/').split('/') if path else ())
    return page.serve(Request(env), Response())


def test_single_bundle_document():
    response = dispatch()
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert text.count(' src=') == 1
    assert '/demo/_assets/gramlot.min.js' in text
    assert 'importmap' not in text
    assert dispatch('/_assets/gramlot.min.js').status_code == 200


def test_explicit_public_opt_in():
    assert dispatch(page_class=GramlotPage).status_code == 403


def test_endpoint_and_source():
    response = dispatch('/_rpc/data/echo', 'POST', to_tytx({'value': 42}, 'json'))
    assert from_tytx(response.get_data(as_text=True), transport='json')['result'] == 42
    response = dispatch('/_rpc/source/detail', 'POST', to_tytx({}, 'json'))
    assert response.status_code == 200
    assert 'Remote Source' in response.get_data(as_text=True)


@pytest.mark.parametrize('path,method,data,origin,status', [
    ('/_rpc/data/serve', 'POST', '{}', None, 404),
    ('/_rpc/data/echo', 'GET', None, None, 405),
    ('/_rpc/data/echo', 'POST', '{}', 'https://other.test', 403),
    ('/_rpc/data/echo', 'POST', 'invalid', None, 400),
    ('/_rpc/data/echo', 'POST', to_tytx({}, 'json'), None, 422),
    ('/_rpc/source/echo', 'POST', '{}', None, 404),
])
def test_dispatch_boundary(path, method, data, origin, status):
    assert dispatch(path, method, data, origin).status_code == status
