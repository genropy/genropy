#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Preference
#
#  Created by Francesco Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.
#


class GnrCustomWebPage(object):
    maintable = 'adm.preference'
    py_requires = """public:Public,gnrcomponents/formhandler:FormHandler,prefhandler/prefhandler:AppPrefHandler"""

    def windowTitle(self):
        return '!!Preference panel'

    def main(self, root, **kwargs):
        """APPLICATION PREFERENCE BUILDER"""
        root = root.rootContentPane(title='!![en]Application preference')
        form = root.frameForm(frameCode='app_preferences',store_startKey='_mainpref_',
                                table=self.maintable,datapath='main',store=True,**kwargs)
        form.top.slotToolbar('2,stackButtons,*,form_revert,form_save,semaphore,2',stackButtons_stackNodeId='PREFROOT')
        form.dataController("""
            var tkw = _triggerpars.kw;
            if(tkw.reason && tkw.reason.attr && tkw.reason.attr.livePreference){
                genro.mainGenroWindow.genro.publish({topic:'externalSetData',
                iframe:'*'},{path:'gnr.app_preference.'+tkw.pathlist.slice(4).join('.'),value:tkw.value});
            }""",preference='^#FORM.record.data')
        form.center.appPreferencesTabs(datapath='#FORM.record.data',margin='2px',wdg='stack')