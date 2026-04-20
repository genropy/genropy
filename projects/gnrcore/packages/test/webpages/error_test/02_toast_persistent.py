# -*- coding: utf-8 -*-

"""
TEST 02 - Persistent Toast (duration=0)

EXPECTED BEHAVIOR:
- Persistent toasts do NOT auto-dismiss: they stay until manually closed.
- No progress bar is shown.
- Two action buttons appear on the right: Close (X) and Copy (clipboard icon).
- "Copy" copies title + message text (HTML stripped) to clipboard.
- "Close" dismisses the toast with slide-out animation.
- Clicking the toast body does NOT dismiss persistent toasts.

VERIFY:
- [ ] Toast stays indefinitely (no progress bar)
- [ ] Close button dismisses toast
- [ ] Copy button copies clean text to clipboard (paste somewhere to check)
- [ ] Long text wraps correctly within max-width
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_persistent_error(self, pane):
        """Persistent error toast with copy and close buttons"""
        pane.button('Show Persistent Error', action="""
            genro.toast.show({
                title: 'Server Error',
                message: 'NoneType has no attribute get (ref: 260311-07K4M)',
                level: 'error',
                duration: 0
            });
        """)

    def test_1_persistent_warning(self, pane):
        """Persistent warning toast"""
        pane.button('Show Persistent Warning', action="""
            genro.toast.show({
                title: 'Configuration Warning',
                message: 'Database connection pool is running low. Consider increasing max_connections.',
                level: 'warning',
                duration: 0
            });
        """)

    def test_2_persistent_long_text(self, pane):
        """Persistent toast with long text - should wrap within max-width 420px"""
        pane.button('Show Long Text Toast', action="""
            genro.toast.show({
                title: 'Detailed Error Report',
                message: 'The server encountered an unexpected condition that prevented it from fulfilling the request. The error occurred in module gnrwebpage.py at line 621 during RPC method execution. Please contact your system administrator. Reference code: 260311-A1B2C',
                level: 'error',
                duration: 0
            });
        """)

    def test_3_copy_and_verify(self, pane):
        """Copy test: click Copy on toast, then paste in the textarea below"""
        pane.button('Show Toast to Copy', action="""
            genro.toast.show({
                title: 'Copy Me',
                message: 'This text should appear in clipboard after pressing Copy button.',
                level: 'info',
                duration: 0
            });
        """)
        pane.br()
        pane.textarea(lbl='Paste here to verify', width='400px', height='80px',
                       placeholder='Paste clipboard content here...')
