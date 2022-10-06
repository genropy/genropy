#!/usr/bin/env python
# encoding: utf-8


from gnr.core.gnrdecorator import public_method,metadata
from gnr.core.gnrbag import Bag
from datetime import time

class GnrCustomWebPage(object):
    py_requires="""public:Public,assistant:Assistant"""
    pageOptions = dict(openMenu=False,enableZoom=False)
    auth_main='user'
   
    def pbl_avatarTemplate(self):
        return '<div>$user<div>'

    def main(self,root,**kwargs):
        frame = root.framePane(datapath='main')
        mainbar = frame.top.slotToolbar('5,stackSwitch,*,username,5',background='white',color='#444',font_size='1.3em',height='30px')
        pages = self.getAssistantPages()
        root.data('main.availablePages',pages)
        root.data('main.currentPage',pages.getAttr('#0','code'))
        root.data('main.currentPageTitle',pages.getAttr('#0','caption'))
        mainbar.username.div(self.user,font_weight='bold')
        mainbar.stackSwitch.menudiv(value='^main.currentPage',storepath='main.availablePages',
                        caption_path='main.currentPageTitle',colorWhite=False)
        mainsc = frame.center.stackContainer(selectedPage='^main.currentPage')
        for key in pages.keys():
            getattr(self,f'assistant_{key}')(mainsc,pageName=key)