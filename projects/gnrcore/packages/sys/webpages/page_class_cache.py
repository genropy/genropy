#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2026 Softwell.
#

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/framegrid:FrameGrid'
    auth_main = 'superadmin,_DEV_'

    def windowTitle(self):
        return '!!Page Class Cache'

    def main(self, root, **kwargs):
        bc = root.borderContainer(datapath='main')
        frame = bc.frameGrid(region='center', frameCode='cacheEntries',
                             datapath='cacheEntries',
                             struct=self.cacheStruct,
                             _class='pbl_roundedGroup', margin='2px')
        frame.top.slotBar('2,vtitle,*,clearcache,5,refresh,2',
                          vtitle='!!Page Class Cache',
                          _class='pbl_roundedGroupLabel')
        frame.top.bar.clearcache.button('!!Clear Cache', fire='.clearcache')
        frame.top.bar.refresh.button('!!Refresh', fire='.refresh')
        frame.grid.bagStore(storepath='cacheEntries.store',
                            storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^cacheEntries.loaded_data',
                            selfUpdate=True)
        bc.dataRpc('cacheEntries.loaded_data', self.getCacheEntries,
                   _onStart=True,
                   _fired='^cacheEntries.refresh'
                   )
        bc.dataRpc('dummy', self.clearCacheEntries,
                   _fired='^cacheEntries.clearcache',
                   _onResult='FIRE cacheEntries.refresh;'
                   )
        
    def cacheStruct(self, struct):
        r = struct.view().rows()
        r.cell('page_id', name='!!Page ID', width='20em')
        r.cell('module_path', name='!!Module Path', width='40em')
        r.cell('class_name', name='!!Class Name', width='20em')

    @public_method
    def clearCacheEntries(self):
        self.site.resource_loader.clear_page_class_cache()

    @public_method
    def getCacheEntries(self):
        result = Bag()
        cache = self.site.resource_loader._page_class_cache
        for i, ((page_id, module_path), page_class) in enumerate(cache.items()):
            result.setItem(str(i), None,
                        dict(
                            page_id=page_id,
                            module_path=module_path,
                            class_name=page_class.__name__
                        )
                           )
        return result
