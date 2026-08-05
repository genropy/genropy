# -*- coding: utf-8 -*-

"""
TEST 01 - Toast Notification System (basic)

EXPECTED BEHAVIOR:
- Each button triggers a toast notification at the top-right corner.
- "Info" toast: blue left border, info icon, auto-dismisses in ~4 seconds.
- "Success" toast: green left border, checkmark icon, auto-dismisses in ~3 seconds.
- "Warning" toast: amber left border, triangle icon, auto-dismisses in ~5 seconds.
- "Error" toast: red left border, X icon, auto-dismisses in ~6 seconds.
- All toasts show a progress bar at the bottom that shrinks over time.
- Hovering pauses the progress bar; leaving resumes and dismisses after 2s.
- Clicking a toast dismisses it immediately with a slide-out animation.
- Multiple toasts stack vertically without overlapping.

VERIFY:
- [ ] Each level has correct color and icon
- [ ] Progress bar animates and pauses on hover
- [ ] Click dismisses toast
- [ ] Multiple toasts stack correctly
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_info(self, pane):
        """Info toast - blue, auto-dismiss ~4s"""
        pane.button('Show Info Toast',
                     action="genro.toast.show({title:'Info', message:'This is an info notification.', level:'info'});")

    def test_1_success(self, pane):
        """Success toast - green, auto-dismiss ~3s"""
        pane.button('Show Success Toast',
                     action="genro.toast.show({title:'Success', message:'Operation completed successfully.', level:'success'});")

    def test_2_warning(self, pane):
        """Warning toast - amber, auto-dismiss ~5s"""
        pane.button('Show Warning Toast',
                     action="genro.toast.show({title:'Warning', message:'Something needs your attention.', level:'warning'});")

    def test_3_error(self, pane):
        """Error toast - red, auto-dismiss ~6s"""
        pane.button('Show Error Toast',
                     action="genro.toast.show({title:'Error', message:'Something went wrong.', level:'error'});")

    def test_4_multiple(self, pane):
        """Fire 4 toasts rapidly - should stack vertically"""
        pane.button('Fire All Toasts', action="""
            genro.toast.show({title:'First', message:'Info toast', level:'info'});
            genro.toast.show({title:'Second', message:'Success toast', level:'success'});
            genro.toast.show({title:'Third', message:'Warning toast', level:'warning'});
            genro.toast.show({title:'Fourth', message:'Error toast', level:'error'});
        """)

    def test_5_dlg_message(self, pane):
        """genro.dlg.message() should use toast instead of old dojo toaster"""
        pane.button('dlg.message (info)',
                     action="genro.dlg.message('Hello from dlg.message!');")
        pane.button('dlg.message (error)',
                     action="genro.dlg.message('An error via dlg.message', null, 'error', 5000);")
