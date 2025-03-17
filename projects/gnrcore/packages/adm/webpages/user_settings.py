#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Preference
#
#  Created by Francesco Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.
#
from gnr.core.gnrlang import objectExtract
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import metadata,public_method

class GnrCustomWebPage(object):
    """USER PREFERENCE BUILDER"""
    maintable = 'adm.user'
    py_requires = """public:Public,th/th:TableHandler,
                    gnrcomponents/settingmanager/settingmanager:SettingManager AS setting_manager"""

    def windowTitle(self):
        return '!!User preference panel'

    def main(self, root, **kwargs):
       #bar = frame.top.slotBar('backTitle,*',height='30px',font_weight='bold',
       #                     color='var(--mainWindow-color)',border_bottom='1px solid silver')
       #btn = bar.backTitle.lightButton(action="genro.dom.windowMessage('parent',{'topic':'modal_page_close'});",
       #                               style='display:flex;align-items:center;',cursor='pointer')
       # btn.div(_class="iconbox leftOut",height='25px',background_color='var(--mainWindow-color)')
        #bc = frame.center.borderContainer(design='sidebar')
        #bc.contentPane(region='left',width='350px',border_right='1px solid silver')
        #bc.contentPane(region='center')

        self.setting_manager.setting_panel(root,title='!![en]User settings',datapath='main',table='adm.user_setting')
