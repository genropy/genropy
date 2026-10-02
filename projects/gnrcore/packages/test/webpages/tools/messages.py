# -*- coding: utf-8 -*-

"""The two channels the server uses to push a message into a client

Both cases send from the server into a page the sender is not sitting in, and
they differ in what they address. `sendMessageToClient` addresses PAGES: it
writes the message into `gnr.servermsg` of each target, named by page id or
selected from the page register by a filter - `name:regex` pairs joined by
` AND `, e.g. `user:admin AND pagename:messages`. `chatMessageToUser` addresses
a PERSON: it writes into the recipient's user store and raises the chat window
of every page they have open, which is why the second case mixes in
`ChatComponent` and the first does not need it.
"""


class GnrCustomWebPage(object):
    py_requires = ("gnrcomponents/testhandler:TestHandlerFull,"
                   "gnrcomponents/chat_component/chat_component:ChatComponent")

    def windowTitle(self):
        return 'Messages'

    def test_1_send_message(self, pane):
        """Push a message into one page by its id, or into every page a filter selects

        With neither field set the message would land in the sender's own page,
        so the case refuses and says so instead."""
        fb = pane.formbuilder()
        fb.textbox(value='^.message', lbl='Message')
        fb.textbox(value='^.info.pageId', lbl='Page Id')
        fb.textbox(value='^.filters', width='40em', lbl='Filters')
        fb.button('Send', fire='.send_message')
        pane.div('^.result')
        pane.dataRpc('.result', 'send_page_message', _fired='^.send_message',
                     message='=.message', pageId='=.info.pageId', filters='=.filters')

    def test_2_chat_message(self, pane):
        """Push a message to a USER: it reaches the chat window of every page they have open"""
        pane.textbox(value='^.message', lbl='Message')
        pane.textbox(value='^.user', lbl='User')
        pane.button('Send', action='FIRE .sendmessage')
        pane.div('^.result')
        pane.dataRpc('.result', 'send_chat_message',
                     msg='=.message', user='=.user',
                     _fired='^.sendmessage')

    def rpc_send_page_message(self, message=None, pageId=None, filters=None):
        # No silent fallback: with no target the framework writes into the sender's page.
        if not pageId and not filters:
            return 'Give a page id or a filter first'
        self.sendMessageToClient(message, pageId=pageId, filters=filters)
        return 'Sent to %s' % (pageId or filters)

    def rpc_send_chat_message(self, msg=None, user=None):
        # No silent fallback: with an empty user the framework messages the sender.
        if not user:
            return 'Type a user first'
        self.chatMessageToUser(msg=msg, user=user, sysmessage=True)
        return 'Sent to %s' % user
