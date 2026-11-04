# -*- coding: utf-8 -*-

"""Writing into another USER's store: a two-way chat over `userStore`

Where the page store belongs to one open page, the user store belongs to a
person and survives every page they have open. `self.userStore(username)`
returns it, and `set_datachange` pushes a value into it from the server, so
the recipient sees the change without asking for it. The case writes each
message twice - once into the sender's own store and once into the
recipient's, with opposite `in_out` attributes - which is what lets one page
render both sides of the conversation. It takes TWO logged-in users to drive:
open it as one user, address the other by username.
"""

from datetime import datetime


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def pageAuthTags(self, method=None, **kwargs):
        return 'user'

    def test_1_send(self, pane):
        """Send a message to another user: it lands in their store and in yours, and both are rendered

        The server delivers a user-store datachange only to the pages subscribed to that
        store under a matching path: without `setStoreSubscription` on `gnr._chat` the
        change stays on the server and this page never sees it. Untick Subscribed and the
        messages stop arriving; tick it again and the ones held meanwhile arrive at once.
        """
        bc = pane.borderContainer(height='250px', datapath='test1')
        bc.contentPane(region='right', width='40%')
        center = bc.contentPane(region='center')
        fb = center.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.user', lbl='Talk to')
        fb.div(nodeId='chat_monitor', height='150px', overflow='auto',
               width='20em', background='white', border='1px solid gray')
        fb.dataController("SET rows_datapath = 'gnr._chat.rooms.'+user;", user='^.user')
        fb.dataController("""
                            var rootnode= genro.nodeById("chat_monitor");
                            var domNode = rootnode.domNode;
                            rootnode.clearValue().freeze();
                            rows.forEach(function(n){
                                var attr = n.attr;
                                var msgattr = {};
                                msgattr['float'] = attr['in_out']=='out'?'left':'right';
                                msgattr['color'] = attr['in_out']=='out'?'red':'green';
                                msgattr.content = n.getValue();
                                var line = rootnode._('div',{height:lineHeight+'px'});
                                line._('div',msgattr);
                            });
                            rootnode.unfreeze();
                            var scrollHeight = genro.nodeById("chat_monitor").domNode.scrollHeight;
                            var scrollTop;
                            if (scrollHeight>boxHeight){
                                scrollTop = scrollHeight-domNode.scrollWidth;
                            }
                            if (scrollTop){
                                rootnode.domNode.scrollTop = scrollTop;
                            }

                            """, rows="^.rows", datapath='^rows_datapath', _if='rows', lineHeight=20,
                          boxHeight=150)
        fb.data('.subscribed', True)
        fb.checkbox(value='^.subscribed', label='Subscribed')
        # every kwarg without an underscore travels to the RPC: the pair is driven by topics
        fb.dataController("genro.publish(subscribed ? 'user_store_chat_on' : 'user_store_chat_off');",
                          subscribed='^.subscribed')
        fb.dataRpc('dummy', 'setStoreSubscription', subscribe_user_store_chat_on=True, _onStart=True,
                   storename='user', client_path='gnr._chat', active=True,
                   _onResult='genro.setFastPolling(true);')
        fb.dataRpc('dummy', 'setStoreSubscription', subscribe_user_store_chat_off=True,
                   storename='user', client_path='gnr._chat', active=False,
                   _onCalling='genro.setFastPolling(false);')
        fb.textbox(value='^.message', lbl='Msg')
        fb.button('send', fire='.send')
        center.dataRpc('dummy', 'send_message', user='=.user', msg='=.message', _fired='^.send', _if='user&&msg')

    def rpc_send_message(self, user=None, msg=None):
        ts = datetime.now()
        path = 'gnr._chat.rooms.%s.rows.#id'
        with self.userStore(self.user) as store:
            store.set_datachange(path % user, msg, fired=False, reason='chat_in',
                                 attributes=dict(from_user=self.user, in_out='out', ts=ts))
        with self.userStore(user) as store:
            store.set_datachange(path % self.user, msg, fired=False, reason='chat_out',
                                 attributes=dict(from_user=self.user, in_out='in', ts=ts))
