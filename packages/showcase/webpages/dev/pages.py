#!/usr/bin/env pythonw
# -*- coding: UTF-8 -*-
#
#  untitled
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.
#

from gnr.core.gnrbag import Bag
class GnrCustomWebPage(object):
    def pageAuthTags(self, method=None, **kwargs):
        return ''
        
    def windowTitle(self):
         return '!!'

    def main(self, root, **kwargs):
        root.button('Refresh', fire='refresh')
        root.horizontalslider(lbl='!!Refresh', value = '^timing', width='200px', 
                                         minimum=0, maximum=60, discreteValues=61)
        root.data('pages',Bag())
        root.dataRpc('pages.served', 'refresh_current_pages',_fired='^refresh',_timing='=timing')
        root.tree(storepath='pages')
        
        
    def rpc_refresh_current_pages(self):
        return Bag(self.site.page_register.pages())