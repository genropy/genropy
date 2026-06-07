# -*- coding: utf-8 -*-
"""REST read-only endpoint over the GenroPy DB, with auto-generated
OpenAPI 3.1 spec and inline Swagger UI.

URL surface (all under ``/sys/ep_openapi/``):

    GET  /openapi.json                       OpenAPI 3.1 spec
    GET  /docs                               Swagger UI page (CDN)
    GET  /{pkg}/{table}                      list (limit, offset, where, ...)
    GET  /{pkg}/{table}/{pkey}               single record
    POST /{pkg}/{table}/_search              complex query in JSON body

Auth: Authorization: Bearer <token>. The token lives in the ``openapi``
service of the instanceconfig (transitional fallback to the
``sourcerer`` service while the dedicated token is provisioned).

This endpoint is a transitional layer over the legacy WSGI stack. The
production-grade REST API will live on genro-asgi.

Exposure boundary (read carefully before flipping flags)
--------------------------------------------------------
A table appears in the surface iff its model declares ``openapi=True``
(and its package is not ``openapi=False``). Per-column ``openapi=False``
hides individual columns. Beyond that, two important caveats hold for
the current implementation:

1. **Foreign-key traversal is not gated.** GenroPy expressions of the
   form ``$@<fkey>.<col>`` are accepted verbatim in ``columns``,
   ``where``, ``order_by``, ``group_by`` and ``having``. They make any
   table reachable via fkey queryable, even when the target table is
   ``openapi=False``. Both direct exfiltration (selecting traversed
   columns) and boolean-blind probing (filtering on traversed columns
   and reading rowcount) are possible. A traversal guard inside
   ``ApiEngine`` is planned; until it ships, treat ``openapi=True`` as
   exposing the **entire fkey-reachable subgraph** of the table.

2. **GenroPy ``auth_tags`` are not enforced.** A column with
   ``auth_tags='hr_only'`` and ``openapi=True`` is visible to anyone
   holding the bearer. There is no end-user identity propagation
   (``acting_user``) on the path yet; audit attribution lives at the
   service level. On-behalf-of identity flow will land with the ASGI
   rewrite.

Practical rule: only mark a table ``openapi=True`` when its entire
fkey-reachable subgraph is intended to be readable by every holder of
the service bearer, and when no auth-tag-gated column needs to remain
private from those same holders.
"""

import hmac
import json

from gnr.app.api_engine import ApiEngine, ApiEngineError


MAX_ROWS = 1000
DEFAULT_LIMIT = 100


_SWAGGER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GenroPy API — Swagger UI</title>
  <link rel="stylesheet" type="text/css"
        href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: "./openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis],
      });
    };
  </script>
</body>
</html>
"""


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/externalcall:BaseRpc'
    convert_result = False
    skip_connection = False

    # ── Dispatch ─────────────────────────────────────────────────────

    def rootPage(self, *args, **kwargs):
        """Custom dispatcher: parse path segments after ``ep_openapi`` and
        select the handler based on HTTP method. Bypasses the standard
        ``BaseRpc`` "first segment == method name" rule so URLs are
        clean REST paths like ``/sys/ep_openapi/{pkg}/{table}/{pkey}``.
        """
        kwargs.pop('pagetemplate', None)

        if self.request.method == 'OPTIONS':
            return self._cors_preflight()

        if not self._check_bearer():
            return self._error(401, 'unauthorized',
                               'Missing or invalid bearer token')

        # Special paths first
        if args == ('openapi.json',):
            return self._openapi_json()
        if args == ('docs',):
            return self._swagger_ui()

        # Resource paths: /{pkg}/{table}[/{pkey_or_action}]
        method = self.request.method
        if len(args) == 2:
            pkg, table = args
            if method == 'GET':
                return self._list(pkg, table, **kwargs)
            return self._error(405, 'method_not_allowed',
                               'Method %s not allowed on collection' % method)
        if len(args) == 3:
            pkg, table, tail = args
            if tail == '_search' and method == 'POST':
                return self._search(pkg, table)
            if method == 'GET':
                return self._get_record(pkg, table, tail)
            return self._error(405, 'method_not_allowed',
                               'Method %s not allowed' % method)

        return self._error(404, 'not_found',
                           'Unknown path: /%s' % '/'.join(args or ()))

    # ── Auth & CORS ──────────────────────────────────────────────────

    def _check_bearer(self):
        # The endpoint trusts a dedicated 'openapi' service when present;
        # for the legacy transition phase it falls back to the bearer of
        # the 'sourcerer' service so integrators can start consuming the
        # REST surface without provisioning a second token. The fallback
        # will be removed once 'openapi' is provisioned everywhere.
        service = self.getService('openapi') or self.getService('sourcerer')
        if not service:
            return False
        expected = getattr(service, 'token', None)
        if not expected:
            return False
        auth = self.request.headers.get('Authorization') or ''
        if not auth.startswith('Bearer '):
            auth = self.request.headers.get('X-GNR-Authorization') or ''
        if not auth.startswith('Bearer '):
            return False
        return hmac.compare_digest(auth[len('Bearer '):].strip(), expected)

    def _cors_preflight(self):
        self._set_cors_headers()
        self.response._response.status_code = 204
        return ''

    def _set_cors_headers(self):
        self.response.headers.add('Access-Control-Allow-Origin', '*')
        self.response.headers.add('Access-Control-Allow-Methods',
                                  'GET, POST, OPTIONS')
        self.response.headers.add('Access-Control-Allow-Headers',
                                  'Authorization, Content-Type')

    # ── Schema builder (public method, reusable) ─────────────────────

    def schema(self, target=None, readonly=True):
        """Build the OpenAPI 3.1 document for ``target`` (None = all
        tables exposed via ``openapi=True``).

        This is the extension point for the future package broadcast:
        ``pkgBroadcast('openapi_schema', ...)`` will let each package
        contribute its own sub-spec instead of having ``sys.ep_openapi``
        build everything itself.
        """
        engine = ApiEngine(self.app)
        component_schemas = engine.openapi_schema(target=target,
                                                  readonly=readonly)
        write_schemas = engine.openapi_schema(target=target,
                                              readonly=False)

        paths = {}
        tags = []
        for fullname, table_schema in component_schemas.items():
            pkg, tname = fullname.split('.', 1)
            tag = fullname
            tags.append({'name': tag,
                         'description': 'Records of table %s' % fullname})
            paths.update(self._paths_for_table(pkg, tname, fullname, tag,
                                                write_schemas.get(fullname)))

        components = {
            'schemas': component_schemas,
            'securitySchemes': {
                'bearerAuth': {'type': 'http', 'scheme': 'bearer'},
            },
            'parameters': self._common_parameters(),
            'responses': self._common_responses(),
        }
        return {
            'openapi': '3.1.0',
            'info': {
                'title': 'GenroPy API (legacy)',
                'version': '1.0.0',
                'description': (
                    'Read-only REST surface auto-generated from the '
                    'GenroPy data model. Tables are exposed when their '
                    'model declares openapi=True.'),
            },
            'servers': [{'url': self._server_url()}],
            'security': [{'bearerAuth': []}],
            'tags': tags,
            'paths': paths,
            'components': components,
        }

    # ── Handlers ─────────────────────────────────────────────────────

    def _default_columns(self, engine, full):
        """Build a GenroPy ``columns`` expression that restricts the
        runtime payload to the columns published in the OpenAPI spec.
        Without this, columns with unknown dtypes (e.g. pgvector VEC)
        would leak into responses even though the spec hides them.
        """
        cols = engine.exposed_column_names(full)
        return ','.join('$%s' % c for c in cols) if cols else None

    def _list(self, pkg, table, **kwargs):
        full = '%s.%s' % (pkg, table)
        if not self._is_exposed(full):
            return self._error(404, 'not_found',
                               'Table %r not exposed' % full)

        try:
            limit = int(kwargs.pop('limit', DEFAULT_LIMIT))
        except (TypeError, ValueError):
            return self._error(400, 'bad_param', 'limit must be integer')
        try:
            offset = int(kwargs.pop('offset', 0))
        except (TypeError, ValueError):
            return self._error(400, 'bad_param', 'offset must be integer')
        limit = max(1, min(limit, MAX_ROWS))
        offset = max(0, offset)

        sqlparams = kwargs.pop('sqlparams', None)
        if isinstance(sqlparams, str) and sqlparams:
            try:
                sqlparams = json.loads(sqlparams)
            except json.JSONDecodeError:
                return self._error(400, 'bad_param',
                                   'sqlparams must be valid JSON')

        run_kwargs = {'limit': limit, 'offset': offset}
        for k in ('columns', 'where', 'order_by', 'group_by', 'having',
                  'distinct'):
            v = kwargs.get(k)
            if v is not None:
                run_kwargs[k] = v
        if sqlparams:
            run_kwargs['sqlparams'] = sqlparams

        engine = ApiEngine(self.app, max_rows=MAX_ROWS)
        if 'columns' not in run_kwargs:
            default_cols = self._default_columns(engine, full)
            if default_cols:
                run_kwargs['columns'] = default_cols
        try:
            result = engine.run_query(full, **run_kwargs)
        except (ApiEngineError, ValueError) as e:
            return self._error(422, 'invalid_query', str(e))
        if result['error']:
            return self._error(500, 'query_error', result['error'])

        return self._ok({
            'data': result['rows'],
            'pagination': {
                'limit': limit,
                'offset': offset,
                'returned': result['rowcount'],
                'truncated': result['truncated'],
            },
        })

    def _get_record(self, pkg, table, pkey):
        full = '%s.%s' % (pkg, table)
        if not self._is_exposed(full):
            return self._error(404, 'not_found',
                               'Table %r not exposed' % full)

        engine = ApiEngine(self.app, max_rows=MAX_ROWS)
        run_kwargs = dict(
            where='$pkey = :_pkey',
            sqlparams={'_pkey': pkey},
            limit=1,
        )
        default_cols = self._default_columns(engine, full)
        if default_cols:
            run_kwargs['columns'] = default_cols
        try:
            result = engine.run_query(full, **run_kwargs)
        except (ApiEngineError, ValueError) as e:
            return self._error(422, 'invalid_query', str(e))
        if result['error']:
            return self._error(500, 'query_error', result['error'])

        if not result['rows']:
            return self._error(404, 'not_found',
                               'Record %r not found in %s' % (pkey, full))
        return self._ok({'data': result['rows'][0]})

    def _search(self, pkg, table):
        full = '%s.%s' % (pkg, table)
        if not self._is_exposed(full):
            return self._error(404, 'not_found',
                               'Table %r not exposed' % full)

        body = self._read_json_body()
        if isinstance(body, dict) and body.get('__error__'):
            return body['__error__']
        body = body or {}

        try:
            limit = int(body.get('limit', DEFAULT_LIMIT))
            offset = int(body.get('offset', 0))
        except (TypeError, ValueError):
            return self._error(400, 'bad_param',
                               'limit/offset must be integer')
        limit = max(1, min(limit, MAX_ROWS))
        offset = max(0, offset)

        run_kwargs = {'limit': limit, 'offset': offset}
        for k in ('columns', 'where', 'sqlparams', 'order_by',
                  'group_by', 'having', 'distinct'):
            v = body.get(k)
            if v is not None:
                run_kwargs[k] = v

        engine = ApiEngine(self.app, max_rows=MAX_ROWS)
        if 'columns' not in run_kwargs:
            default_cols = self._default_columns(engine, full)
            if default_cols:
                run_kwargs['columns'] = default_cols
        try:
            result = engine.run_query(full, **run_kwargs)
        except (ApiEngineError, ValueError) as e:
            return self._error(422, 'invalid_query', str(e))
        if result['error']:
            return self._error(500, 'query_error', result['error'])

        return self._ok({
            'data': result['rows'],
            'pagination': {
                'limit': limit,
                'offset': offset,
                'returned': result['rowcount'],
                'truncated': result['truncated'],
            },
        })

    def _openapi_json(self):
        self._set_cors_headers()
        self.response.content_type = 'application/json'
        return json.dumps(self.schema(), default=str)

    def _swagger_ui(self):
        self._set_cors_headers()
        self.response.content_type = 'text/html'
        return _SWAGGER_HTML

    # ── Spec helpers ─────────────────────────────────────────────────

    def _paths_for_table(self, pkg, tname, fullname, tag, write_schema):
        ref = '#/components/schemas/%s' % fullname.replace('/', '~1')
        list_response = {
            'type': 'object',
            'properties': {
                'data': {'type': 'array',
                         'items': {'$ref': ref}},
                'pagination': {'type': 'object'},
            },
        }
        single_response = {
            'type': 'object',
            'properties': {'data': {'$ref': ref}},
        }
        search_body = {
            'type': 'object',
            'properties': {
                'columns': {'type': 'string'},
                'where': {'type': 'string'},
                'sqlparams': {'type': 'object'},
                'order_by': {'type': 'string'},
                'group_by': {'type': 'string'},
                'having': {'type': 'string'},
                'distinct': {'type': 'boolean'},
                'limit': {'type': 'integer'},
                'offset': {'type': 'integer'},
            },
        }
        collection_path = '/%s/%s' % (pkg, tname)
        record_path = '/%s/%s/{pkey}' % (pkg, tname)
        search_path = '/%s/%s/_search' % (pkg, tname)
        return {
            collection_path: {
                'get': {
                    'tags': [tag],
                    'summary': 'List %s' % fullname,
                    'parameters': [
                        {'$ref': '#/components/parameters/limit'},
                        {'$ref': '#/components/parameters/offset'},
                        {'$ref': '#/components/parameters/where'},
                        {'$ref': '#/components/parameters/order_by'},
                        {'$ref': '#/components/parameters/columns'},
                    ],
                    'responses': {
                        '200': {'description': 'OK',
                                'content': {'application/json': {
                                    'schema': list_response}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            record_path: {
                'get': {
                    'tags': [tag],
                    'summary': 'Get %s by pkey' % fullname,
                    'parameters': [{
                        'name': 'pkey', 'in': 'path', 'required': True,
                        'schema': {'type': 'string'},
                    }],
                    'responses': {
                        '200': {'description': 'OK',
                                'content': {'application/json': {
                                    'schema': single_response}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                    },
                },
            },
            search_path: {
                'post': {
                    'tags': [tag],
                    'summary': 'Search %s' % fullname,
                    'requestBody': {
                        'required': False,
                        'content': {'application/json': {
                            'schema': search_body}},
                    },
                    'responses': {
                        '200': {'description': 'OK',
                                'content': {'application/json': {
                                    'schema': list_response}}},
                        '401': {'$ref': '#/components/responses/Unauthorized'},
                        '404': {'$ref': '#/components/responses/NotFound'},
                        '422': {'$ref': '#/components/responses/InvalidQuery'},
                    },
                },
            },
        }

    def _common_parameters(self):
        return {
            'limit': {
                'name': 'limit', 'in': 'query', 'required': False,
                'schema': {'type': 'integer', 'minimum': 1,
                           'maximum': MAX_ROWS, 'default': DEFAULT_LIMIT},
            },
            'offset': {
                'name': 'offset', 'in': 'query', 'required': False,
                'schema': {'type': 'integer', 'minimum': 0, 'default': 0},
            },
            'where': {
                'name': 'where', 'in': 'query', 'required': False,
                'description': ('GenroPy where clause with :name '
                                'placeholders, e.g. "$status = :s".'),
                'schema': {'type': 'string'},
            },
            'order_by': {
                'name': 'order_by', 'in': 'query', 'required': False,
                'schema': {'type': 'string'},
            },
            'columns': {
                'name': 'columns', 'in': 'query', 'required': False,
                'description': ('Comma-separated GenroPy columns '
                                'expression, e.g. "$id,$name".'),
                'schema': {'type': 'string'},
            },
        }

    def _common_responses(self):
        error_schema = {
            'type': 'object',
            'properties': {
                'error': {
                    'type': 'object',
                    'properties': {
                        'code': {'type': 'string'},
                        'message': {'type': 'string'},
                        'details': {'type': 'object'},
                    },
                    'required': ['code', 'message'],
                },
            },
        }
        return {
            'Unauthorized': {
                'description': 'Missing or invalid bearer token',
                'content': {'application/json': {'schema': error_schema}},
            },
            'NotFound': {
                'description': 'Resource not found',
                'content': {'application/json': {'schema': error_schema}},
            },
            'InvalidQuery': {
                'description': 'Query parameters did not pass validation',
                'content': {'application/json': {'schema': error_schema}},
            },
        }

    def _server_url(self):
        try:
            return self.site.externalUrl('/sys/ep_openapi').rstrip('/')
        except Exception:
            return '/sys/ep_openapi'

    # ── Helpers: model probe, body, response ─────────────────────────

    def _is_exposed(self, fullname):
        try:
            tbl = self.db.table(fullname)
        except Exception:
            return False
        if not tbl.attributes.get('openapi'):
            return False
        pkg_name = fullname.split('.', 1)[0]
        try:
            pkg = self.db.packages[pkg_name]
        except Exception:
            return False
        return pkg.attributes.get('openapi') is not False

    def _read_json_body(self):
        # GnrWebRequest delegates to a Werkzeug request via __getattr__.
        # Werkzeug exposes the raw body on request.get_data(); the
        # legacy 'body' attribute returns a stream object, not bytes.
        req = self.request._request
        try:
            raw = req.get_data(as_text=False)
        except Exception:
            return {'__error__': self._error(
                400, 'bad_body', 'Could not read request body')}
        if not raw:
            return {}
        if isinstance(raw, bytes):
            try:
                raw = raw.decode('utf-8')
            except UnicodeDecodeError:
                return {'__error__': self._error(
                    400, 'bad_body', 'Body is not valid UTF-8')}
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return {'__error__': self._error(
                400, 'bad_body', 'Body is not valid JSON')}

    def _ok(self, payload):
        self._set_cors_headers()
        self.response.content_type = 'application/json'
        return json.dumps(payload, default=str)

    def _error(self, status, code, message, details=None):
        self._set_cors_headers()
        self.response.content_type = 'application/json'
        self.response._response.status_code = status
        body = {'error': {'code': code, 'message': message}}
        if details is not None:
            body['error']['details'] = details
        return json.dumps(body, default=str)
