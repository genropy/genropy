"""Uploaded files live through response streaming and close at the WSGI boundary."""
import io

import pytest
from werkzeug.datastructures import MultiDict
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Response

from gnr.web.gnrwsgisite import GnrWsgiSite
from gnrwsgisite_dispatcher_cleanup_test import _FakeSite, _start_response


@pytest.fixture
def multipart():
    builder = EnvironBuilder(method='POST', data=MultiDict([
        ('file', (io.BytesIO(b'first upload'), 'first.xml')),
        ('file', (io.BytesIO(b'second upload'), 'second.xml')),
    ]))
    environ = builder.get_environ()
    streams = []
    yield environ, streams
    request = environ.get('werkzeug.request')
    if request is not None:
        request.close()
    for stream in streams:
        stream.close()
    builder.close()


@pytest.mark.parametrize('streaming', [False, True])
def test_uploads_close_after_response_and_preserve_streaming(multipart, streaming):
    environ, streams = multipart
    site = _FakeSite()
    observed_close = []

    def dispatch(environ, start_response):
        streams.extend(f.stream for f in site.currentRequest.files.getlist('file'))

        def generate():
            try:
                yield streams[0].read()
                yield streams[1].read()
            finally:
                observed_close.append(all(not s.closed for s in streams))

        return Response(generate() if streaming else b'normal')(environ, start_response)

    site._dispatcher = dispatch
    result = GnrWsgiSite.dispatcher(site, environ, _start_response)
    assert site._currentRequests._data == {}
    assert site._currentDomains._data == {}
    assert len(streams) == 2 and all(not s.closed for s in streams)
    assert b''.join(result) == (b'first uploadsecond upload' if streaming else b'normal')
    result.close()
    assert all(s.closed for s in streams)
    if streaming:
        assert observed_close == [True]


def test_early_response_close_releases_generator_before_uploads(multipart):
    environ, streams = multipart
    site = _FakeSite()
    finalized = []

    def dispatch(environ, start_response):
        streams.extend(f.stream for f in site.currentRequest.files.getlist('file'))

        def generate():
            try:
                yield streams[0].read(1)
                yield streams[1].read()
            finally:
                finalized.append(not streams[0].closed)

        return Response(generate())(environ, start_response)

    site._dispatcher = dispatch
    result = GnrWsgiSite.dispatcher(site, environ, _start_response)
    assert next(iter(result)) == b'f'
    result.close()
    assert finalized == [True] and all(s.closed for s in streams)


@pytest.mark.parametrize('developer', [False, True])
def test_dispatch_exception_releases_uploads(multipart, developer):
    environ, streams = multipart
    site = _FakeSite()
    site.debug = developer

    def dispatch(environ, start_response):
        streams.extend(f.stream for f in site.currentRequest.files.getlist('file'))
        if developer:
            site.currentPage = type('Page', (), {'isDeveloper': lambda self: True})()
        raise RuntimeError('application error')

    site._dispatcher = dispatch
    if developer:
        with pytest.raises(RuntimeError, match='application error'):
            GnrWsgiSite.dispatcher(site, environ, _start_response)
    else:
        result = GnrWsgiSite.dispatcher(site, environ, _start_response)
        assert b'Internal Server Error' in b''.join(result)
        result.close()
    assert all(s.closed for s in streams)
    assert site._currentRequests._data == {}


def test_cleanup_failure_releases_uploads(multipart):
    environ, streams = multipart
    site = _FakeSite()

    def dispatch(environ, start_response):
        streams.extend(f.stream for f in site.currentRequest.files.getlist('file'))
        return [b'ok']

    def cleanup():
        GnrWsgiSite.cleanup(site)
        raise RuntimeError('cleanup error')

    site._dispatcher = dispatch
    site.cleanup = cleanup
    with pytest.raises(RuntimeError, match='cleanup error'):
        GnrWsgiSite.dispatcher(site, environ, _start_response)
    assert all(s.closed for s in streams)


def test_non_file_request_is_not_parsed_by_close(monkeypatch):
    builder = EnvironBuilder(method='POST', data=b'not multipart')
    environ = builder.get_environ()
    site = _FakeSite()

    def unexpected_parse(self):
        pytest.fail('Closing must not parse an unread request body')

    monkeypatch.setattr('gnr.web.gnrwsgisite.Request._load_form_data', unexpected_parse)
    result = GnrWsgiSite.dispatcher(site, environ, _start_response)
    assert b''.join(result) == b'ok'
    result.close()
    builder.close()


@pytest.mark.parametrize('failure', ['iterate', 'close'])
def test_response_protocol_failure_still_closes_uploads(multipart, failure):
    environ, streams = multipart
    site = _FakeSite()

    class BrokenResponse:
        def __iter__(self):
            if failure == 'iterate':
                raise RuntimeError('iterate failure')
            return iter([b'ok'])

        def close(self):
            assert all(not s.closed for s in streams)
            raise RuntimeError('close failure')

    def dispatch(environ, start_response):
        streams.extend(f.stream for f in site.currentRequest.files.getlist('file'))
        return BrokenResponse()

    site._dispatcher = dispatch
    if failure == 'iterate':
        with pytest.raises(RuntimeError, match='iterate failure'):
            GnrWsgiSite.dispatcher(site, environ, _start_response)
    else:
        result = GnrWsgiSite.dispatcher(site, environ, _start_response)
        assert b''.join(result) == b'ok'
        with pytest.raises(RuntimeError, match='close failure'):
            result.close()
    assert all(s.closed for s in streams)
    assert site._currentRequests._data == {}
