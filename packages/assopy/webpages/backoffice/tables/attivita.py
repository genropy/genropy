#!/usr/bin/env pythonw
# -*- coding: UTF-8 -*-
#
#  untitled
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.
#

""" Attività """

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    maintable='assopy.attivita'
    py_requires='basecomponent:Public,standard_tables:TableHandler'
    
    def windowTitle(self):
        return u'!!Assopy Attività'
         
    def pageAuthTags(self, method=None, **kwargs):
        return 'socio'
        
    def tableWriteTags(self):
        return 'talkadmin,superadmin'
        
    def barTitle(self):
        return u'!!Tabella Attività'
        
    def columnsBase(self):
        return """descrizione:20,descrizione_en:10"""

    def formBase(self,pane,disabled=False,datapath=''):
        fb = pane.formbuilder(datapath=datapath,cols=1, margin_left='2em',border_spacing='7px',margin_top='1em',disabled=disabled)
        fb.field('assopy.attivita.descrizione')
        fb.field('assopy.attivita.descrizione_en')
        
    def orderBase(self):
        return 'descrizione'    
    
    def queryBase(self):
        return dict(column='descrizione',op='contains', val=None)

