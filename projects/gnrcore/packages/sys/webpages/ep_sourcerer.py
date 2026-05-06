# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.web.verifiers import AuthorizationBearerVerifier


MAX_ROWS = 1000


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
        info = {'endpoint': 'rpc_query', 'error': None}

        service = self.getService('sourcerer')
        if not service or not service.is_query_enabled():
            info['error'] = 'endpoint_disabled'
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'data': []}

        count_only = bool(kwargs.get('countOnly'))
        if count_only:
            cap_applied = False
            info['limit_applied'] = kwargs.get('limit')
        else:
            requested = kwargs.get('limit')
            cap_applied = requested is None or (
                isinstance(requested, int) and requested > MAX_ROWS)
            kwargs['limit'] = MAX_ROWS if cap_applied else requested
            info['limit_applied'] = kwargs['limit']

        kwargs.pop('recordResolver', None)

        try:
            adapter_name = type(self.db.adapter).__name__.lower()
            if 'postgres' in adapter_name or 'pg' in adapter_name:
                self.db.execute("SET LOCAL statement_timeout = 3000")
        except Exception:
            pass

        try:
            data_bag, attrs = self.app.getSelection(
                recordResolver=False, **kwargs)
            rows = []
            if not count_only:
                for k in data_bag.keys():
                    node = data_bag.getNode(k)
                    row = dict(node.attr)
                    row.pop('_customClasses', None)
                    row.pop('_attributes', None)
                    rows.append(row)
            info['totalrows'] = attrs.get('totalrows', 0)
            info['more'] = cap_applied and info['totalrows'] >= MAX_ROWS
            info['servertime_ms'] = attrs.get('servertime')
            return {'ok': True, 'ticket_code': ticket_code,
                    'info': info, 'data': rows}
        except Exception as e:
            info['error'] = str(e)
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'data': []}
