# -*- coding: utf-8 -*-

"""
TEST 04 - Error Detail Page Navigation

EXPECTED BEHAVIOR:
- First trigger an error using the button (creates an error record).
- Then click "Open Error Table" to see sys.error records.
- The error_code column should be the first column.
- Click "Detail" link on any row -> opens /sys/ep_error?error_code=<id> in new tab.
- The error detail page shows:
  * Header with error code and description (red left border)
  * Info grid: error type, date, user, IP, RPC method, page ID
  * Request details: URI, user agent
  * Traceback section: expandable frames with module, line, function,
    file hash (gray badge), locals count (blue badge)
  * Expandable locals table per frame
- Test 404: navigating to /sys/ep_error?error_code=INVALID shows "Not Found".
- Test auth: page requires _DEV_ or admin tags.

VERIFY:
- [ ] Error detail page renders correctly with all sections
- [ ] Traceback frames are expandable (click to show locals)
- [ ] File hashes shown as gray badges (12-char SHA256 prefix)
- [ ] 404 page for invalid error code
- [ ] Non-dev/non-admin users cannot access the page
"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_generate_error(self, pane):
        """Generate an error to inspect in the detail page"""
        pane.button('Generate Error', fire='.fire_gen_error')
        pane.dataRpc('.last_error_msg', self.rpc_generate_error,
                     _fired='^.fire_gen_error')
        pane.div('^.last_error_msg', font_style='italic', color='#666',
                 margin_top='8px')

    @public_method
    def rpc_generate_error(self):
        data = {'items': [{'id': 1}, {'id': 2}]}
        return data['items'][99]['name']

    def test_1_open_error_table(self, pane):
        """Open the sys.error table view to browse errors and click Detail links"""
        pane.button('Open Error Table',
                     action="genro.pageBack('sys/th_error');")

    def test_2_test_404(self, pane):
        """Open error detail page with invalid code - should show 'Not Found'"""
        pane.button('Open Invalid Error Page',
                     action="window.open('/sys/ep_error?error_code=INVALID_CODE_999', '_blank');")

    def test_3_open_latest_error(self, pane):
        """After generating an error, open the latest error detail page.
        Check the toast message for the error code reference."""
        pane.div('After triggering test_0, look at the error toast message.')
        pane.div('Copy the ref code (e.g. 260311-07K4M) and open:')
        fb = pane.formbuilder(cols=2)
        fb.textbox(value='^.error_code_input', lbl='Error code',
                    width='15em', placeholder='YYMMDD-XXXXX')
        fb.button('Open Detail Page',
                   action="window.open('/sys/ep_error?error_code=' + GET .error_code_input, '_blank');")
