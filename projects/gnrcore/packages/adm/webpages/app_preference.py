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
        form = root.appPreferencesForm(datapath='main',**kwargs)
        form.dataController("""this.form.load({destPkey:'_mainpref_',discardChange:true});""",
                            subscribe_changedStartArgs=True,
                            subscribe_modal_page_open=True)
        form.dataController("genro.dom.windowMessage('parent',{'topic':'modal_page_close'})",
                            formsubscribe_onDismissed=True)
        bar = form.bottom.bar
        bar.cancel.button('!!Cancel',action='this.form.abort();')
        bar.saveAndClose.button('!!Confirm',action='this.form.publish("save",{destPkey:"*dismiss*"})')