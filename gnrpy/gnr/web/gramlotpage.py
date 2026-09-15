"""Minimal Gramlot page hosting for the legacy WSGI site.

This adapter serves explicitly public, Python-authored pages and services.
It does not inherit the legacy page's authentication and mixin machinery.
"""
from base64 import b64encode
from pathlib import Path
import json
from html import escape
import inspect

from gramlot.page import WebPage, page_methods
from gramlot.transport import to_tytx
from genro_tytx import from_tytx


class GramlotPage(WebPage):
    """An ordinary Python page with explicit access to its host and database."""

    __gramlot_page__ = True
    title = 'Gramlot'
    public = False

    def __init__(self, site, request_args=None):
        self.site = site
        self.request_args = tuple(request_args or ())

    @property
    def db(self):
        return self.site.db

    def serve(self, request, response):
        """Serve the initial Source through the shared Gramlot bootstrap."""
        if self.public is not True:
            response.status_code = 403
            response.set_data('This adapter requires an explicitly public page.')
            return response
        if self.request_args == ('_assets', 'gramlot.min.js'):
            response.content_type = 'text/javascript'
            response.set_data(Path(__file__).with_name('gramlot_assets')
                              .joinpath('gramlot.min.js').read_bytes())
            return response
        if self.request_args:
            return self.serve_rpc(request, response)
        allowed_args = {'windowTitle', '_parent_page_id', '_calling_page_id'}
        if (request.method not in ('GET', 'HEAD')
                or set(request.args) - allowed_args):
            response.status = 400
            response.set_data('This prototype accepts initial page requests only.')
            return response
        builder = self.source_builder('main')
        self.main(builder.root)
        encoded = b64encode(to_tytx(builder.source, 'json').encode()).decode('ascii')
        startup = {
            'recipe': 'data:application/vnd.tytx+json;base64,' + encoded,
            'inspector': False,
            'rpc': request.path.rstrip('/') + '/_rpc',
        }
        response.content_type = 'text/html'
        response.charset = 'utf-8'
        response.headers['Cache-Control'] = 'no-store'
        asset_url = escape(request.path.rstrip('/') + '/_assets/gramlot.min.js', quote=True)
        startup_json = json.dumps(startup).replace('<', '\\u003c')
        document = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{escape(self.title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body {{margin:0; font-family:system-ui}} #root {{padding:16px}}</style>
</head><body><div id="root"></div><pre id="error" hidden></pre>
<script id="startup" type="application/json">{startup_json}</script>
<script type="module" src="{asset_url}"></script></body></html>"""
        response.set_data(document)
        return response

    def serve_rpc(self, request, response):
        """Dispatch explicitly decorated Gramlot services in the WSGI thread."""
        def reply(value, status=200):
            response.status_code = status
            response.content_type = 'application/vnd.tytx+json'
            response.headers['Cache-Control'] = 'no-store'
            response.set_data(to_tytx(value, 'json'))
            return response

        def error(message, status):
            return reply({'ok': False, 'error': {'kind': 'request', 'message': message}}, status)

        if len(self.request_args) != 3 or self.request_args[0] != '_rpc':
            return error('Unknown route', 404)
        if request.method != 'POST':
            return error('RPC requires POST', 405)
        if request.headers.get('Origin') not in (None, request.host_url.rstrip('/')):
            return error('Origin mismatch', 403)
        if request.mimetype != 'application/vnd.tytx+json':
            return error('Expected TYTX JSON', 415)
        _, role, name = self.request_args
        method = page_methods(type(self)).get(name)
        if method is None or method.role != role:
            return error('Service not found', 404)
        try:
            params = from_tytx(request.get_data(as_text=True), transport='json')
        except Exception:
            return error('Invalid TYTX', 400)
        if not isinstance(params, dict):
            return error('Parameters must be a mapping', 400)
        handler = method.function.__get__(self, type(self))
        builder = self.source_builder('main') if role == 'source' else None
        args = (builder.root,) if builder else ()
        try:
            inspect.signature(handler).bind(*args, **params)
        except TypeError:
            return error('Invalid service parameters', 422)
        if inspect.iscoroutinefunction(handler):
            return error('Async services are not supported by this adapter', 422)
        result = handler(*args, **params)
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise TypeError('This synchronous adapter requires synchronous endpoints')
        if builder:
            if result is not None:
                raise TypeError('Source methods must return None')
            result = builder.source
        return reply({'ok': True, 'result': result})
