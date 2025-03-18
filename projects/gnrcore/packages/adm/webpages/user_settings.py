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
    css_requires='gnrcomponents/settingmanager/settingmanager'

    maintable = 'adm.user'
    py_requires = """public:Public,th/th:TableHandler"""

    def windowTitle(self):
        return '!!User preference panel'

    def main(self, root, **kwargs):
        root.thFormHandler(formResource='FormUserSettings',datapath='main',
                    table='adm.user',formId='legacy_user_settings',
                    startKey=self.db.currentEnv.get('user_id'))
       
    
    @public_method
    def updateUserPreferenceFromSettings(self,data=None,**kwargs):
        pass

