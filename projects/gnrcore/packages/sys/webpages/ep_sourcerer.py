# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import toTypedJSON
from gnr.web.gnrwebpage import GnrUserNotAllowed, GnrBasicAuthenticationError
from gnr.web.verifiers import AuthorizationBearerVerifier

from gnrpkg.sys.sourcerer_endpoint import (
    build_relationtree_response,
    run_query,
)


class SourcererBearerVerifier(AuthorizationBearerVerifier):
    def get_token_to_verify(self):
        service = self.page.getService('sourcerer')
        if service:
            return service.token


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/externalcall:BaseRpc'
    convert_result = False

    def rootPage(self, *args, **kwargs):
        kwargs.pop('pagetemplate', None)
        if args:
            try:
                method = self.getPublicMethod('rpc', args[0])
            except (GnrUserNotAllowed, GnrBasicAuthenticationError) as err:
                self.response.content_type = 'application/json'
                return toTypedJSON({'error': str(err)})
            if not method:
                self.response.content_type = 'application/json'
                return toTypedJSON({'error': f'Not existing method {args[0]}'})
            args = list(args)[1:]
        else:
            method = self.rpc_index
        result = method(*args, **kwargs)
        self.response.content_type = 'application/json'
        return toTypedJSON(result)

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_health(self, **kwargs):
        return {'result': 'ok'}

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_query(self, ticket_code=None, **kwargs):
        info_base = {'endpoint': 'rpc_query', 'error': None}

        service = self.getService('sourcerer')
        if not service or not service.is_query_enabled():
            info_base['error'] = 'endpoint_disabled'
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info_base, 'data': []}

        result = run_query(self.site, **kwargs)
        # merge endpoint metadata into info
        result_info = result.get('info') or {}
        result_info['endpoint'] = 'rpc_query'
        result['info'] = result_info
        result['ticket_code'] = ticket_code
        return result

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_relationtree(self, ticket_code=None, table=None, **kwargs):
        service = self.getService('sourcerer')
        if not service or not service.is_query_enabled():
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': {'endpoint': 'rpc_relationtree',
                             'error': 'endpoint_disabled'},
                    'tables': None, 'trees': None}

        return build_relationtree_response(
            self.db, table=table, ticket_code=ticket_code)
