# -*- coding: utf-8 -*-

"""
TEST 05 - Client-Side Error Events

EXPECTED BEHAVIOR:
- Client errors publish to the 'client_error' topic.
- In developer mode, errors appear in the developer console
  via genro.dev.addError().
- Open browser DevTools console to see '[client_error]' log entries.

Test scenarios:
- Network error: simulated by calling a non-existent server URL.
- Missing resource: triggers a 'missing_resource' client_error event.
- Manual client_error: publishes a custom error event.

VERIFY:
- [ ] Console shows '[client_error]' entries with errorType and description
- [ ] Developer console (genro dev panel) shows CLIENT errors
- [ ] Toast appears for developer users via addError
"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_manual_client_error(self, pane):
        """Publish a client_error event manually - check browser console"""
        pane.button('Publish client_error', action="""
            genro.publish('client_error', {
                errorType: 'test_error',
                description: 'This is a manually triggered client error for testing.'
            });
        """)
        pane.div('Open browser DevTools console to see the [client_error] log entry.',
                 font_style='italic', color='#666', margin_top='8px')

    def test_1_network_error(self, pane):
        """Simulate network error by calling unreachable URL.
        Disconnect the network or stop the server after clicking."""
        pane.button('Call Non-Existent RPC', action="""
            genro.rpc.remoteCall('this_method_does_not_exist_at_all', {}, null, null, null, 'POST');
        """)
        pane.div('This may produce a network or 404 error depending on server state.',
                 font_style='italic', color='#666', margin_top='8px')

    def test_2_check_dev_console(self, pane):
        """Open the Genropy developer console to see logged errors"""
        pane.div('Press Ctrl+Shift+D (or the developer toggle) to open the Genropy dev panel.')
        pane.div('CLIENT errors from test_0 and test_1 should appear in the error log.',
                 font_style='italic', color='#666')
