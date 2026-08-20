# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
class Proxy_test(BaseComponent):
    proxy=True

    def ciao_test(self):

        return 'ciao'

    @public_method
    def ciao(self):
        return 'ciao'

class Proxy_test2(BaseComponent):
    proxy='proxy_test'

    @public_method
    def ciao(self):
        return 'ciao2'