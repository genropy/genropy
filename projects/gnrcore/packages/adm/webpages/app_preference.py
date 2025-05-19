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
        form = root.frameForm(frameCode='app_preferences',store_startKey='_mainpref_',
                                table=self.maintable,datapath='main',store=True,modal=True,**kwargs)
        form.top.slotToolbar('*,stackButtons,*',
                             stackButtons_stackNodeId='PREFROOT')
        form.dataController("""
            var tkw = _triggerpars.kw;
            if(tkw.reason && tkw.reason.attr && tkw.reason.attr.livePreference){
                genro.mainGenroWindow.genro.publish({topic:'externalSetData',
                iframe:'*'},{path:'gnr.app_preference.'+tkw.pathlist.slice(4).join('.'),value:tkw.value});
            }""",preference='^#FORM.record.data')
        form.center.appPreferencesTabs(datapath='#FORM.record.data',wdg='stack')
        bar = form.bottom.slotBar('5,cancel,*,revertbtn,10,savebtn,saveAndClose,5',margin_bottom='2px',_class='slotbar_dialog_footer')
        bar.cancel.button('!!Cancel',action='this.form.abort();')
        bar.savebtn.button('!!Apply',action='this.form.publish("save"})')
        bar.saveAndClose.button('!!Confirm',action='this.form.publish("save",{destPkey:"*dismiss*"})')
        form.dataController("""
                                this.form.load({destPkey:'_mainpref_',discardChange:true});
                               """,
                            subscribe_changedStartArgs=True,
                            subscribe_modal_page_open=True)
        form.dataController("genro.dom.windowMessage('parent',{'topic':'modal_page_close'})",
                            formsubscribe_onDismissed=True)