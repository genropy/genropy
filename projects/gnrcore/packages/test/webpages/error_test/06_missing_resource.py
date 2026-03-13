# -*- coding: utf-8 -*-

"""
TEST 06 - Missing Resource Graceful Degradation

EXPECTED BEHAVIOR:
- When a table view/form/dialog references a resource file (th_*.py) that
  does not exist, the page should NOT crash.
- Instead, a sad Genropy logo with an error message is displayed in the
  pane where the form/view would have been.
- The error is logged to sys.error with error_type='missing_resource'.
- A 'client_error' event with errorType='missing_resource' is published.

This test uses a fake table name that has no th_ resource file.

VERIFY:
- [ ] Sad logo (gray Genropy face) appears instead of crash
- [ ] Error message is displayed below the sad logo
- [ ] Page remains functional (other UI elements work)
- [ ] Error logged in sys.error table
- [ ] Console shows client_error with errorType='missing_resource'
"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_0_missing_form_dialog(self, pane):
        """Open a dialog for a table with no Form resource.
        Should show sad logo, not crash."""
        pane.div('Clicking the button opens a dialogTableHandler for a table without th_ resource.')
        pane.button('Open Missing Form Dialog', fire='.fire_missing_dialog')
        pane.dataController("""
            genro.publish('openTableHandlerDialog',
                {table:'sys.error', formResource:'THIS_RESOURCE_DOES_NOT_EXIST'});
        """, _fired='^.fire_missing_dialog')

    def test_1_inline_view(self, pane):
        """Inline table view - the view should gracefully handle missing resources.
        If the sys.error table view works, it proves the error table handler is functional."""
        pane.div('This loads the sys.error table view inline to verify it works correctly.')
        pane.plainTableHandler(table='sys.error',
                               viewResource='ViewFromColumns',
                               height='300px')
