#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  gnrbaseproxy.py
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.

#from builtins import object
class GnrBaseProxy(object):
    """TODO"""
    def __init__(self, page, **kwargs):
        self.page = page
        [self.page._subscribe_event(attr[6:], self) for attr in dir(self) if attr.startswith('event_')]
        ## For every method starting with 'event_' self.page._subscribe_event is called
        self.init(**kwargs)

        
    def init(self, **kwargs):
        """Hook method. You can customize the ``__init__`` method"""
        pass