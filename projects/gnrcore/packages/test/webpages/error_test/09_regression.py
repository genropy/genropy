# -*- coding: utf-8 -*-

"""
TEST 09 - Regression Checks

EXPECTED BEHAVIOR:
- Normal operations should work exactly as before the error-handler changes.
- No toast notifications on successful RPC calls.
- No console errors on page load.
- Existing table views/forms with proper resources load normally.
- genro.toast object is initialized (not null/undefined).

VERIFY:
- [ ] Page loads without JS console errors
- [ ] genro.toast is initialized (check in console)
- [ ] Successful RPC calls produce no toast
- [ ] Existing table views still work normally
- [ ] Unicode data submission works without errors
"""

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_toast_initialized(self, pane):
        """Verify genro.toast is initialized"""
        pane.button('Check genro.toast', action="""
            if(genro.toast){
                genro.toast.show({message: 'genro.toast is initialized!', level: 'success'});
            } else {
                alert('ERROR: genro.toast is NOT initialized!');
            }
        """)

    def test_1_successful_rpc(self, pane):
        """Normal RPC call - should return result with NO toast"""
        fb = pane.formbuilder(cols=2)
        fb.textbox(value='^.name', lbl='Name', placeholder='Type a name')
        fb.button('Call RPC', fire='.fire_normal_rpc')
        fb.dataRpc('.rpc_result', self.rpc_normal,
                   name='=.name', _fired='^.fire_normal_rpc')
        fb.div('^.rpc_result', lbl='Result', color='green')

    @public_method
    def rpc_normal(self, name=None):
        return 'Hello, %s! RPC worked correctly.' % (name or 'World')

    def test_2_unicode_rpc(self, pane):
        """Unicode data round-trip - should work without UnicodeDecodeError toast"""
        fb = pane.formbuilder(cols=2)
        fb.textbox(value='^.unicode_input', lbl='Unicode text',
                    placeholder='Inserisci testo con accenti: e o a u')
        fb.button('Send Unicode', fire='.fire_unicode')
        fb.dataRpc('.unicode_result', self.rpc_unicode,
                   text='=.unicode_input', _fired='^.fire_unicode')
        fb.div('^.unicode_result', lbl='Result', color='green')

    @public_method
    def rpc_unicode(self, text=None):
        return 'Received: %s (length: %d)' % (text or '', len(text or ''))

    def test_3_rpc_returns_bag(self, pane):
        """RPC returning a Bag - normal structured data response"""
        pane.button('Get Bag Data', fire='.fire_bag')
        pane.dataRpc('.bag_result', self.rpc_bag, _fired='^.fire_bag')
        pane.quickGrid(value='^.bag_result', height='auto', width='auto',
                       margin_top='10px')

    @public_method
    def rpc_bag(self):
        result = Bag()
        for i in range(5):
            row = Bag()
            row['name'] = 'Item %d' % i
            row['value'] = i * 10
            result.setItem('r_%d' % i, row)
        return result
