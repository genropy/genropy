"""Dojo HTTP transport integration."""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrlang import GnrException


class GnrCustomWebPage(object):
    py_requires = ('gnrcomponents/testhandler:TestHandlerFull,'
                   'th/th:TableHandler')
    maintable = 'glbl.provincia'

    def test_0_deferred(self, pane):
        """Check the active transport and the public Deferred contract."""
        pane.button('Check Deferred', action="""
            var dfd = genro.serverCall('transport_echo', {}, function(result){
                genro.setData('transport.echo', result.getItem('message'));
            });
            SET .contract = dfd instanceof dojo.Deferred ? 'Dojo Deferred' : 'FAIL';
            SET .transport = dfd.ioArgs.xhr instanceof XMLHttpRequest ? 'XHR' : 'fetch';
            dfd.addCallback(function(result){
                genro.setData('transport.chain', 'Callback chain completed');
                return result;
            });
        """)
        pane.div('^.contract')
        pane.div('^.transport')
        pane.div('^transport.echo')
        pane.div('^transport.chain')
        pane.div('^transport.datachange')

    def test_1_recovery(self, pane):
        """An expected RPC error must leave subsequent calls usable."""
        pane.button('Expected RPC error').dataRpc(
            '.result', self.transport_error,
            _onError="SET .status = 'Expected RPC error received';")
        pane.button('Recover with RPC').dataRpc(
            '.result', self.transport_echo,
            _onResult="SET .status = result.getItem('message');")
        pane.div('^.status')

    def test_2_tablehandler(self, pane):
        """Load and save a province in the dedicated test database."""
        pane.borderContainer(height='400px').contentPane(
            region='center').dialogTableHandler(
                table='glbl.provincia', view_store_onStart=True,
                dialog_height='300px', dialog_width='450px')

    @public_method
    def transport_echo(self):
        self.setInClientData('transport.datachange', 'Datachange received')
        return Bag(dict(message='RPC completed'))

    @public_method
    def transport_error(self):
        raise GnrException('Expected transport test error')
