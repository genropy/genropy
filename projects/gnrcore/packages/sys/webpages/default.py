# -*- coding: utf-8 -*-

# untitled.py
# Created by Giovanni Porcari on 2010-08-29.
# Copyright (c) 2010 Softwell. All rights reserved.

import os

from werkzeug.exceptions import NotFound

from gnr.core.gnrbag import DirectoryResolver

class GnrCustomWebPage(object):

    def pageAuthTags(self, method=None, **kwargs):
        return ''

    def windowTitle(self):
        return ''

    def onPreIniting(self, request_args, request_kwargs):
        # urls that map to no page and no folder answer 404 before the page
        # boots (#890): raising from this hook (which, unlike onIniting, is
        # not wrapped in a try/except) reaches the dispatcher's HTTPException
        # handler, that answers with werkzeug's plain 404 page instead of the
        # full framework envelope and its client bootstrap.
        # Only the plain page GET may abort here: method/rpc/_plugin calls and
        # page_id sub-requests of already served pages must go through (their
        # errorPane fallback in main() stays), and the direct /sys/default url
        # arrives with empty request_args.
        if not request_args or any(k in request_kwargs
                                   for k in ('method', 'rpc', '_plugin', 'page_id')):
            return
        url_info = self.site.getUrlInfo(request_args)
        if not os.path.isdir(os.path.join(url_info.basepath, *url_info.request_args)):
            raise NotFound(f"Page /{'/'.join(request_args)} not found")

    def main(self, root, **kwargs):
        url_info = self.site.getUrlInfo(self.getCallArgs())
        dirpath=os.path.join(url_info.basepath,*url_info.request_args)
        if not os.path.isdir(dirpath):
            requested_path = '/'.join(url_info.request_args)
            root.errorPane(f'Page /{requested_path} not found')
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


