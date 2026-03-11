# -*- coding: utf-8 -*-

# untitled.py
# Created by Giovanni Porcari on 2010-08-29.
# Copyright (c) 2010 Softwell. All rights reserved.

import os

from gnr.core.gnrbag import DirectoryResolver

class GnrCustomWebPage(object):

    def pageAuthTags(self, method=None, **kwargs):
        return ''

    def windowTitle(self):
        return ''
    def isDeveloper(self):
        return True

    def main(self, root, **kwargs):
        url_info = self.site.getUrlInfo(self.getCallArgs())
        dirpath=os.path.join(url_info.basepath,*url_info.request_args)
        if not os.path.isdir(dirpath):
            requested_path = '/'.join(url_info.request_args)
            cp = root.contentPane(overflow='hidden',
                style='display:flex; align-items:center; justify-content:center; flex-direction:column; height:100%;')
            cp.img(src='/_rsrc/common/css_icons/svg/16/genrologo_sad.svg',
                   height='64px', opacity='.5', margin_bottom='12px')
            cp.div('Page /%s not found' % requested_path,
                   style='color:#888; font-size:13px; text-align:center; max-width:400px; line-height:1.5;')
            return
        bc=root.borderContainer(datapath='main')
        bc.style("")
        center=bc.contentPane(region='center',datapath='.current',overflow='hidden')
        left=bc.contentPane(region='left',width='200px',splitter=True,background='#eee',
                           datapath='.tree',overflow_y='auto')
        left.data('.store',DirectoryResolver(dirpath,cacheTime=10,
                            include='*.py', exclude='_*,.*',dropext=True,readOnly=False)()
                            )
        center.dataController(""" let url = (window.location.pathname+'/'+rel_path).replace('//','/');
            SET .url = url;
        """,_if="file_ext=='py'",_else="''",
            rel_path='^.rel_path',file_ext='=.file_ext',_delay=1)                   
        left.tree(storepath='.store', hideValues=True, inspect='shift', 
              labelAttribute='caption',
              getLabelClass="""var _class= (node._resolver || node._value) ? 'menu_shape menu_level_0' :  'menu_shape menu_level_2';
                                            return _class""",
              isTree=False, selected_rel_path='main.current.rel_path',  _class='menutree',
              openOnClick=True,
              autoCollapse=True,
              connect_ondblclick='window.open(GET main.current.url,GET main.current.caption);',
              selected_caption='main.current.caption',
              selected_file_ext='main.current.file_ext')
        center.iframe(border='0px',width='100%',height='100%',src='^.url')


