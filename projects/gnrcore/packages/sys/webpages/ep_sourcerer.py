# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/externalcall:BaseRpc'
    skip_connection = False

    def _check_sourcerer_token(self):
        auth_header = self.request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        bearer_token = auth_header[7:]
        sourcerer_token = self.getPreference('sourcerer.sourcerer_token', pkg='sys')
        return sourcerer_token and bearer_token == sourcerer_token

    @public_method
    def rpc_health(self, **kwargs):
        if not self._check_sourcerer_token():
            self.response.status_code = 401
            return Bag(dict(error='Invalid token'))
        return Bag(dict(result='ok'))
