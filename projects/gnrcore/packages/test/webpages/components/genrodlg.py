# -*- coding: utf-8 -*-

"""genro.dlg.ask: a confirmation dialog that resumes the action it interrupted

genro.dlg.ask opens a modal question with one callback per answer. The pattern
shown here is the common one: two buttons write the command they wanted to run
into a datapath, a single dataController asks for confirmation, and only the
'continue' callback fires the command that was parked.
"""


class GnrCustomWebPage(object):
    dojo_version = '11'
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        """Browser window title of this page"""
        return 'Test warning and ask'

    def test_1_ask(self, pane):
        """Ask before saving: two commands sharing one confirmation

        Press either button: neither acts directly, both store their own event
        name in .savingCommand. The controller listening on that path opens the
        warning and, on 'continue', fires the stored event — so the same dialog
        serves 'Save and close' and 'Save and new'.
        """
        pane.button(action="FIRE .savingCommand='.saveAndClose'", label='Save and close')
        pane.button(action="FIRE .savingCommand='.saveAndAdd'", label='Save and new')
        pane.dataController("""
                            var _this = this;
                            var cb = function(){_this.fireEvent(savingCommand);}
                            genro.dlg.ask("Warning",
                                                 "This job has zero amount, proceed anyway?",
                                                  {'cancel':'Cancel', 'continue':'Continue'},
                                                  {'continue': cb});
                            """, savingCommand='^.savingCommand')
        pane.dataController("""alert('saveAndClose')""", fire='^.saveAndClose')
        pane.dataController("""alert('saveAndAdd')""", fire='^.saveAndAdd')
