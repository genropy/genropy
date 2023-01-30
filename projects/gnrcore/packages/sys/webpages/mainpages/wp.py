# -*- coding: utf-8 -*-

# thpage.py
# Created by Francesco Porcari on 2011-05-05.
# Copyright (c) 2011 Softwell. All rights reserved.


from builtins import object
class GnrCustomWebPage(object):
    auth_main='user'

    @classmethod
    def getMainPackage(cls,request_args=None,request_kwargs=None):
        return request_kwargs.get('th_from_package') or request_args[0]

    def onIniting(self, request_args, request_kwargs):
        pkg = request_args[0]
        component_path = '/'.join(request_args[1:])
        self.mixinComponent('pages',f'{component_path}:Page',pkg=pkg,only_callables=False)
