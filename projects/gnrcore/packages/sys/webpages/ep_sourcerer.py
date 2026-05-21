# -*- coding: utf-8 -*-
"""Internal operations endpoint backing the Sourcerer MCP client.

This is **not** a public REST API. The bearer is the token of the
``sourcerer`` service, custodied by the operations team, revocable at
will, and intended for diagnostic / introspection work performed by
the Sourcerer toolchain (MCP server, target_db tool surface).

Implications:

- The endpoint trusts the bearer holder to be the operator. ``rpc_query``
  therefore accepts ``partition_kwargs`` straight from the payload —
  on a partitioned DB the operator can scope the env to any tenant for
  diagnosis. This would be inappropriate for a user-facing API; it is
  intentional here.
- ``ApiEngine`` is invoked without ``acting_user`` or auth tags. Audit
  attribution is at the service level, not the end-user level.

External integrators must use ``ep_openapi`` instead, which has its
own (much tighter) exposure boundary keyed on ``openapi=True`` flags.
"""

import json

from gnr.app.api_engine import ApiEngine, ApiEngineError
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.web.verifiers import AuthorizationBearerVerifier


MAX_ROWS = 1000

_RUN_QUERY_PRIMARY_KEYS = frozenset((
    'columns', 'where', 'sqlparams', 'order_by', 'group_by', 'having',
    'distinct', 'limit', 'offset', 'subtable', 'storename',
    'partition_kwargs', 'language',
))
_RUN_QUERY_OPT_KEYS = frozenset((
    'excludeLogicalDeleted', 'excludeDraft', 'mode', 'checkPermissions',
))


class SourcererBearerVerifier(AuthorizationBearerVerifier):
    def get_token_to_verify(self):
        service = self.page.getService('sourcerer')
        if service:
            return service.token


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/externalcall:BaseRpc'

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_health(self, **kwargs):
        return Bag(dict(result='ok'))

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_query(self, ticket_code=None, **kwargs):
        service = self.getService('sourcerer')
        if not service or not service.is_query_enabled():
            return self._query_error('endpoint_disabled', ticket_code)

        table = kwargs.pop('table', None)
        if not table:
            return self._query_error('missing_table', ticket_code)

        count_only = bool(kwargs.pop('countOnly', False))
        if count_only:
            kwargs['columns'] = 'count(*) AS totalrows'
        kwargs.pop('recordResolver', None)

        # When this endpoint is reached via HTTP, structured kwargs
        # (sqlparams, partition_kwargs) arrive JSON-encoded as strings
        # because urlencode flattens dicts. Restore them to dicts.
        for k in ('sqlparams', 'partition_kwargs'):
            v = kwargs.get(k)
            if isinstance(v, str) and v:
                try:
                    kwargs[k] = json.loads(v)
                except (TypeError, ValueError):
                    return self._query_error(
                        '%s must be valid JSON' % k, ticket_code)

        primary = {k: kwargs[k] for k in _RUN_QUERY_PRIMARY_KEYS
                   if k in kwargs}
        opt = {k: kwargs[k] for k in _RUN_QUERY_OPT_KEYS if k in kwargs}

        condition = kwargs.get('condition')
        if condition:
            existing = primary.get('where')
            primary['where'] = ('(%s) AND (%s)' % (existing, condition)
                                if existing else condition)

        pkeys = kwargs.get('pkeys')
        if pkeys is not None:
            existing = primary.get('where')
            pkey_clause = '$pkey IN :_pkeys'
            primary['where'] = ('(%s) AND (%s)' % (existing, pkey_clause)
                                if existing else pkey_clause)
            sp = dict(primary.get('sqlparams') or {})
            if isinstance(pkeys, str):
                pkeys = [p.strip() for p in pkeys.split(',') if p.strip()]
            sp['_pkeys'] = pkeys
            primary['sqlparams'] = sp

        engine = ApiEngine(self.app, max_rows=MAX_ROWS)
        try:
            result = engine.run_query(table, opt_kwargs=opt or None,
                                      **primary)
        except (ApiEngineError, ValueError) as e:
            return self._query_error(str(e), ticket_code)

        if result['error']:
            return self._query_error(result['error'], ticket_code)

        rows = result['rows']
        rowcount = result['rowcount']
        if count_only:
            # Lift the count(*) result out of the row payload into
            # rowcount so callers always see a number, not a row.
            total = 0
            if rows and isinstance(rows[0], dict):
                total = int(rows[0].get('totalrows') or 0)
            rows = []
            rowcount = total
        return {'ok': True, 'ticket_code': ticket_code,
                'info': {'endpoint': 'rpc_query', 'error': None},
                'rows': rows,
                'rowcount': rowcount,
                'truncated': result['truncated'],
                'elapsed_ms': result['elapsed_ms']}

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_relationtree(self, ticket_code=None, table=None, **kwargs):
        info = {'endpoint': 'rpc_relationtree', 'error': None}

        service = self.getService('sourcerer')
        if not service or not service.is_query_enabled():
            info['error'] = 'endpoint_disabled'
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'tables': None, 'trees': None}

        engine = ApiEngine(self.app)
        if not table:
            try:
                return {'ok': True, 'ticket_code': ticket_code,
                        'info': info,
                        'tables': engine.table_names(), 'trees': None}
            except Exception as e:
                info['error'] = str(e)
                return {'ok': False, 'ticket_code': ticket_code,
                        'info': info, 'tables': None, 'trees': None}

        requested = [t.strip() for t in str(table).split(',') if t.strip()]
        info['tables_requested'] = requested
        trees = {}
        failed = {}
        for tname in requested:
            try:
                wrapped = engine.table_schema(tname)
                trees[tname] = wrapped[tname]
            except Exception as e:
                failed[tname] = str(e)
        if failed:
            info['tables_failed'] = failed
        if not trees:
            info['error'] = 'no_table_resolved'
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'tables': None, 'trees': None}
        return {'ok': True, 'ticket_code': ticket_code,
                'info': info, 'tables': None, 'trees': trees}

    def _query_error(self, msg, ticket_code):
        return {'ok': False, 'ticket_code': ticket_code,
                'info': {'endpoint': 'rpc_query', 'error': msg},
                'rows': [], 'rowcount': 0, 'truncated': False,
                'elapsed_ms': 0.0}
