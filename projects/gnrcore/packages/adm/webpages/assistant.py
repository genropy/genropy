#!/usr/bin/env python
# encoding: utf-8


from gnr.core.gnrdecorator import public_method,metadata
from gnr.core.gnrbag import Bag
from datetime import time

class GnrCustomWebPage(object):
    py_requires="""assistant:Assistant"""
    auth_main='user'
