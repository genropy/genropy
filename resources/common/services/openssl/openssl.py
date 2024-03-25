#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-


from gnr.lib.services.openssl import OpenSSLService


class Service(OpenSSLService):

    def extractContent(self, storage_node):
        return storage_node.service.call(('openssl','cms','-verify','-noverify','-in',storage_node,'-inform','DER','-no_attr_verify'),return_output=True)