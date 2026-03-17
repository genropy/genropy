# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.web.verifiers import AuthorizationBearerVerifier


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
