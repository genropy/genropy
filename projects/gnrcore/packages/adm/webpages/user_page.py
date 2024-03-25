# -*- coding: utf-8 -*-

# user_page.py
# Created by Francesco Porcari on 2011-04-08.
# Copyright (c) 2011 softwell All rights reserved.

import hashlib

class GnrCustomWebPage(object):
    py_requires = """public:TableHandlerMain"""
    maintable = 'adm.user'

    def windowTitle(self):
        return '!!User'

    def barTitle(self):
        return '!!Users'