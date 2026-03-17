# -*- coding: utf-8 -*-

"""
TEST 03 - Server-Side RPC Errors

EXPECTED BEHAVIOR:
- Each button triggers an RPC call that raises an exception on the server.
- A persistent error toast appears with the error message and a reference code
  in format (ref: YYMMDD-XXXXX).
- For DEVELOPER users: the toast message includes a clickable link to the
  error detail page at /sys/ep_error?error_code=<id>.
- For NORMAL users: the toast shows the reference code as plain text.
- The error is stored in the sys.error table with full context:
  error_code, description, traceback, username, user_ip, user_agent,
  request_uri, rpc_method, page_id.

VERIFY:
- [ ] Toast appears with error message and ref code
- [ ] Error stored in sys.error table (check via admin UI)
- [ ] Error detail page shows full traceback with expandable frames
- [ ] Developer sees clickable link, non-developer sees plain text
- [ ] Different exception types produce different error_type values
"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_key_error(self, pane):
        """KeyError - common Python exception"""
        pane.button('Trigger KeyError', fire='.fire_key_error')
        pane.dataRpc(None, self.rpc_key_error, _fired='^.fire_key_error')

    @public_method
    def rpc_key_error(self):
        d = {'name': 'test'}
        return d['missing_key']

    def test_1_zero_division(self, pane):
        """ZeroDivisionError - arithmetic exception"""
        pane.button('Trigger ZeroDivisionError', fire='.fire_zero_div')
        pane.dataRpc(None, self.rpc_zero_division, _fired='^.fire_zero_div')

    @public_method
    def rpc_zero_division(self):
        return 1 / 0

    def test_2_attribute_error(self, pane):
        """AttributeError - accessing non-existent attribute"""
        pane.button('Trigger AttributeError', fire='.fire_attr_error')
        pane.dataRpc(None, self.rpc_attribute_error, _fired='^.fire_attr_error')

    @public_method
    def rpc_attribute_error(self):
        obj = None
        return obj.some_method()

    def test_3_value_error(self, pane):
        """ValueError - invalid value conversion"""
        pane.button('Trigger ValueError', fire='.fire_value_error')
        pane.dataRpc(None, self.rpc_value_error, _fired='^.fire_value_error')

    @public_method
    def rpc_value_error(self):
        return int('not_a_number')

    def test_4_nested_exception(self, pane):
        """Deep nested call - traceback should show multiple frames"""
        pane.button('Trigger Nested Error', fire='.fire_nested')
        pane.dataRpc(None, self.rpc_nested_error, _fired='^.fire_nested')


    def test_5_parameters_in_error(self, pane):
        """Check parameters error logging"""
        pane.button('Trigger Error', fire='.fire_error')
        pane.numberTextBox(value='^.alfa',lbl='Alfa')
        pane.numberTextBox(value='^.beta',lbl='Beta')

        pane.dataRpc(self.rpc_with_parameters, alfa='=.alfa',beta='=.beta',_fired='^.fire_error')



    @public_method
    def rpc_nested_error(self):
        return self._level_1()

    def _level_1(self):
        return self._level_2()

    def _level_2(self):
        return self._level_3()

    def _level_3(self):
        data = {'users': []}
        return data['users'][0]['name']

    def test_5_custom_message(self, pane):
        """RuntimeError with a custom descriptive message"""
        pane.button('Trigger RuntimeError', fire='.fire_runtime')
        pane.dataRpc(None, self.rpc_runtime_error, _fired='^.fire_runtime')

    @public_method
    def rpc_runtime_error(self):
        raise RuntimeError('Custom error: configuration file not found at /etc/myapp/config.xml')


    @public_method
    def rpc_with_parameters(self,alfa=None,beta=None):
        omega = None
        return alfa+beta+omega