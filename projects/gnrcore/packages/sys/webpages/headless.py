#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.web.gnrheadlesspage import GnrHeadlessPage

class GnrCustomWebPage(object):
    page_factory = GnrHeadlessPage
    skip_connection=True
    
