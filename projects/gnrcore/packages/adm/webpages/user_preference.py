#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Preference
#
#  Created by Francesco Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.
#
from builtins import object
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import GnrMixinError
from gnr.core.gnrdecorator import public_method
class GnrCustomWebPage(object):
    """USER PREFERENCE BUILDER"""
    maintable = 'adm.user'
    py_requires = """public:Public,th/th:TableHandler,prefhandler/prefhandler:UserPrefHandler"""

    def windowTitle(self):
        return '!!User preference panel'

    def main(self, root, **kwargs):
        """USER PREFERENCE BUILDER"""
        root = root.rootContentPane(title='!![en]User preferences')
        form = root.thFormHandler(formId='user_preferences',formResource='FormProfile',startKey=self.avatar.user_id,
                                table='adm.user',datapath='main',**kwargs)
        form.top.slotToolbar('2,*,form_revert,form_save,semaphore,2')
        form.dataController("""
            var tkw = _triggerpars.kw;
            if(tkw.reason && tkw.reason.attr && tkw.reason.attr.livePreference){
                genro.mainGenroWindow.genro.publish({topic:'externalSetData',
                iframe:'*'},{path:'gnr.user_preference.'+tkw.pathlist.slice(2).join('.'),value:tkw.value});
            }""",preference='^#FORM.record.preferences')

