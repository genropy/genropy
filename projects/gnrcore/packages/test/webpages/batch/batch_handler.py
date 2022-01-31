# -*- coding: utf-8 -*-

# Created by Francesco Porcari on 2010-10-01 and updated by Davide Paci on 2022-01-25
# Copyright (c) 2021 Softwell. All rights reserved.

class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                   gnrcomponents/batch_handler/batch_handler:TableScriptRunner,
                   gnrcomponents/batch_handler/batch_handler:BatchMonitor"""

    maintable = 'glbl.localita'
    defaultscript = 'localita_script'

    def test_0_launch_button(self, pane):
        "Launch action from button"
        parameters = """{res_type:"action",table:"%s",resource:"%s",selectionName:"currsel",}""" % (
        self.maintable, self.defaultscript)
        pane.button('Launch action',
                    action="PUBLISH table_script_run=params;",
                    params=dict(res_type='action', table=self.maintable,
                                selectionName='cursel', structurepath='list.structure'))

    def test_1_launch_tree(self, pane):
        "Launch test from tree"
        box = pane.div(datapath='test2', height='200px')
        self.table_script_resource_tree(box, res_type='action', table=self.maintable, gridId='mygrid',
                                        selectionName='currsel')



        
        