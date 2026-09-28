# -*- coding: utf-8 -*-

"""setInClientData over HTTP and over the websocket channel

Both cards call the server, which writes back into the client datastore
instead of returning a value: `setInClientData` pushes a path, a value and
its attributes to the page that asked for it. The first card lets you choose
that path and compare the HTTP call with the same call sent with
httpMethod='WSK'; the second shows `self.log` reaching the developer console
from a server method.
"""

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
    dojo_source = True

    def windowTitle(self):
        return 'setInClientData'
         
    def test_0_setInClientData(self,pane):
        """setInClientData: the server writes into the client datastore

        Set a destination path, a value and any attributes, then send the
        call over HTTP or over the websocket: the yellow pane at the bottom
        binds `foo.bar`, `spam` and `alpha`, so a path pointing at one of
        them updates in place. The nodeId, fired and reason fields are passed
        through to `setInClientData` to show how the change is attributed.
        """
        bc = pane.borderContainer(height='500px')
        left = bc.contentPane(region='left',width='50%',datapath='.pars')
        pane.data('.pars',Bag(dict(destpath='foo.bar',value='44')))
        fb = left.formbuilder(cols=1, border_spacing='4px')
        fb.textbox(value='^.destpath',lbl='Path')
        fb.textbox(value='^.value',lbl='Value')
        bc.contentPane(region='center',datapath='.pars').multiValueEditor(value='^.attributes')
        fb.textbox(value='^._nodeId',lbl='NodeId')
        fb.textbox(value='^._fired',lbl='Fired')
        fb.textbox(value='^._reason',lbl='Reason')
        fb.button('Send RPC',fire='.#parent.send_rpc')
        fb.button('Send WSK',fire='.#parent.send_wsk')

        fb = bc.contentPane(region='bottom',nodeId='mybox',datapath='.mybox.data',background='yellow').formbuilder(cols=3,border_spacing='3px')
        fb.div('^.foo.bar',lbl='foo.bar',width='10em')
        fb.div('^.spam',lbl='spam',width='10em')
        fb.div('^.alpha',lbl='alpha',width='10em')

        pane.dataRpc('dummy',self.testSetInClientDataSimple,pars='=.pars',_fired='^.send_rpc')        
        pane.dataRpc('dummy',self.testSetInClientDataSimple,pars='=.pars',_fired='^.send_wsk',httpMethod='WSK')        

    @public_method
    def testSetInClientDataSimple(self,pars=None):
        attributes = pars['attributes']
        if attributes:
            attributes = attributes.asDict(ascii=True)
        self.setInClientData(pars['destpath'],value=pars['value'],attributes=attributes,
                             nodeId=pars['_nodeId'],fired=pars['_fired'],reason=pars['_reason'])



    def test_2_testLog(self,pane):
        """self.log from a server method

        Each click sends the incremented counter to the server, which logs it
        with extra keyword arguments; the log line reaches the browser console
        of the calling page.
        """
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.button('Log',action="""var current = (current || 0)+1;
                                SET .number = current;
                                SET .current = current""",current='=.current')
        fb.dataRpc('.result',self.testLog,number='^.number',
                    _onCalling='SET .number=null',_if='number')
        fb.div('^.result')

    @public_method
    def testLog(self,number=None):
        self.log('Il mio numero',number,prova=33,test={'aaa':99})
