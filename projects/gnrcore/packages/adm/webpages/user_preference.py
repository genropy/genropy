#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Preference
#
#  Created by Francesco Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.
#

class GnrCustomWebPage(object):
    """USER PREFERENCE BUILDER"""
    maintable = 'adm.user'
    py_requires = """public:Public,th/th:TableHandler,prefhandler/prefhandler:UserPrefHandler"""

    def windowTitle(self):
        return '!!User preference panel'

    def main(self, root, **kwargs):
        """USER PREFERENCE BUILDER"""
        form = root.thFormHandler(formId='user_preferences',formResource='FormProfile',
                                table='adm.user',datapath='main',**kwargs)
        form.dataController("""
            var tkw = _triggerpars.kw;
            if(tkw.reason && tkw.reason.attr && tkw.reason.attr.livePreference){
                genro.mainGenroWindow.genro.publish({topic:'externalSetData',
                iframe:'*'},{path:'gnr.user_preference.'+tkw.pathlist.slice(2).join('.'),value:tkw.value});
            }""",preference='^#FORM.record.preferences')

        bar = form.bottom.slotBar('5,cancel,*,revertbtn,10,savebtn,saveAndClose,5',margin_bottom='2px',_class='slotbar_dialog_footer')
        bar.cancel.button('!!Close',action='this.form.abort();')
        #bar.revertbtn.button('!!Revert',action='this.form.publish("reload")',disabled='^.controller.changed?=!#v')
        bar.savebtn.button('!!Apply',action='this.form.publish("save"})')
        bar.saveAndClose.button('!!Confirm',action='this.form.publish("save",{destPkey:"*dismiss*"})')
        form.dataController("""
                                this.form.load({destPkey:startKey,discardChange:true});
                               """,startKey=self.avatar.user_id,
                               _onStart=True,
                            subscribe_changedStartArgs=True,
                            subscribe_modal_page_open=True)
        form.dataController("genro.dom.windowMessage('parent',{'topic':'modal_page_close'})",
                            formsubscribe_onDismissed=True)