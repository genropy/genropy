# -*- coding: utf-8 -*-

"""toolbar"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_1_toolbar(self, pane):
        "Basic toolbar with buttons and save alert"
        tb = pane.toolbar(height='20px')
        fb = tb.formbuilder(cols=8, border_spacing=0)
        for i in ('icnBaseAdd', 'icnBuilding', 'icnBaseCalendar',
                  'icnBuddy', 'queryMenu', 'icnBuddyChat'):
            fb.slotButton('tooltip', iconClass=i)
        fb.textbox()
        fb.button('save', action='alert("Saving!")')