# -*- coding: utf-8 -*-

"""Holding another user's store open: what happens to everyone else meanwhile

`self.userStore(username)` is a LOCK on that user's register entry, not just a
handle: entering the `with` block takes the lock and retries while somebody
else holds it, and every other request touching the same store waits meanwhile.
The case makes that visible by holding the lock for a chosen number of seconds,
and by raising inside the block on demand - the release happens on the way out
either way, so a second attempt right after an error has to succeed. Drive it
from two browser tabs to see the wait. Contention never comes back as a value:
after about 10 seconds of retries (`LOCK_MAX_RETRY` x `RETRY_DELAY`) the `with`
raises `GnrDaemonLocked`, which the case catches and shows - so lock the user
for longer than that in the first tab to see it in the second.
"""

from time import sleep

from gnr.core.gnrdecorator import public_method
from gnr.web.daemon.siteregister import GnrDaemonLocked


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    dojo_theme = 'tundra'
    dojo_version = '11'

    def test_1_user_lock(self, pane):
        """Lock a user's store for N seconds, optionally raising inside the block"""
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.dbSelect(dbtable='adm.user', value='^.user_id', lbl='User',
                    selected_username='.username', width='25em',
                    hasDownArrow=True)
        fb.numberTextbox(value='^.seconds', lbl='Seconds')
        fb.checkbox(value='^.doError', label='Do Error')
        fb.button('Lock', fire='.lockUser')
        fb.div('^.result', lbl='Result')
        fb.dataRpc('.result', self.lockUser, username='=.username', seconds='=.seconds',
                   doError='=.doError',
                   _fired='^.lockUser')

    @public_method
    def lockUser(self, username=None, seconds=None, doError=None):
        # an empty username falls back to the reader's own store, which would lock it
        # and report `done` exactly like a real lock of someone else
        if not username:
            return 'Pick a user first'
        seconds = seconds or 1
        try:
            with self.userStore(username):
                if doError:
                    raise Exception('x exception')
                sleep(seconds)
                return 'done %s %s' % (self.getUuid(), seconds)
        except GnrDaemonLocked:
            return 'Locked: %s is held by another request, gave up retrying' % username
