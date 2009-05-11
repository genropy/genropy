#!/usr/bin/env pythonw
# -*- coding: UTF-8 -*-
#
#  Genro Dojo - Examples & Tutorial
#
#  Created by Giovanni Porcari on 2007-03-07.
#  Copyright (c) 2007 Softwell. All rights reserved.
#

""" GnrDojo Examples & Tutorials """

#from gnr.core.gnrbag import Bag
#from gnr.web.gnrwebpage import GnrWebPage
#from gnr.core.gnrlang import gnrImport
#from gnr.core.gnrbag import Bag
#import os

# ----- GnrWebPage subclass -----

class GnrCustomWebPage(object): 
    #css_requires='index.css'   
    def main(self, root, **kwargs):
        cont = root.div(_class='docpane')
        cont.div("""Hello""", _class='demodoc')
        cont.button('prova',action='alert(window.parent.location.search)')

#---- rpc index call -----
#def index(req, **kwargs):
#    return GnrWebPage(req, GnrCustomWebPage, __file__, **kwargs).index()
