#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  dojo_20.py
#
#  Softwell fork of Dojo 1.1 (Giojo.js)
#  Copyright (c) 2007 Softwell. All rights reserved.

# --------------------------- GnrWebPage subclass ---------------------------
from gnr.web.gnrwebpage_proxy.frontend.dojo_base import GnrBaseDojoFrontend
from gnr.web.gnrwebstruct import GnrDomSrc_dojo_20

class GnrWebFrontend(GnrBaseDojoFrontend):
    version = 'd20'
    domSrcFactory = GnrDomSrc_dojo_20

    def css_frontend(self, theme=None):
        theme = theme or self.theme
        return ['dojo/resources/dojo.css',
                'dijit/themes/dijit.css',
                'dojox/widget/ColorPicker/ColorPicker.css',
                'dojox/grid/_grid/Grid.css',
                f'dojox/grid/_grid/{theme}Grid.css'
        ]

    def gnrjs_frontend(self):
        return ['gnrbag','gnrdomsource','gnrlang', 'gnrstores',
                'genro','genro_patch','genro_rpc','genro_wdg', 'genro_src',
                'genro_widgets','genro_tree','genro_grid','genro_components','genro_frm',
                'genro_dev','genro_dlg', 'genro_dom','genro_extra','genro_google','genro_mobile','genro_cordova','gnrwebsocket','gnrsharedobjects']

    def css_genro_frontend(self):
        return {'all': ['gnr_dojotheme/gnr_dojotheme', 'gnrbase'], 'print': ['gnrprint']}

    def dojo_release_imports(self):
        return ['dojo_release.js']
