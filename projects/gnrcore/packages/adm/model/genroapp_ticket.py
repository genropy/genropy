# encoding: utf-8
"""Single use tickets that carry the login of a browser page into GenroApp.

"Open with GenroApp" in the browser asks a ticket for the logged user and passes it to
GenroApp in the link ``genroapp://add?url=<site>&ticket=<ticket>``. GenroApp opens the
site with ``?genroapp_ticket=<ticket>``; the login page consumes it and logs the same user
in without the password, then offers the registration of the computer. Only the SHA-256
of a ticket is stored; a ticket is used once and expires after ``TICKET_SECONDS``.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

TICKET_SECONDS = 120


def ticket_hash(ticket):
    return hashlib.sha256(ticket.encode('ascii')).hexdigest()


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('genroapp_ticket', pkey='id',
                        name_long='!![en]GenroApp ticket',
                        name_plural='!![en]GenroApp tickets')
        self.sysFields(tbl, id=False)
        tbl.column('id', size='64', name_long='!![en]Ticket hash')
        tbl.column('user_id', size='22', group='_', name_long='!![en]User').relation(
                   'adm.user.id', relation_name='genroapp_tickets', mode='foreignkey', onDelete='cascade')
        tbl.column('expires', dtype='DHZ', name_long='!![en]Expires')
        tbl.column('used', dtype='B', name_long='!![en]Used')

    def newTicket(self, user_id):
        """A new ticket for ``user_id``: the string to put in the link. Expired tickets are removed."""
        now = datetime.now(timezone.utc)
        self.deleteSelection(where='$expires<:now', now=now)
        ticket = secrets.token_urlsafe(32)
        self.insert(self.newrecord(id=ticket_hash(ticket), user_id=user_id,
                                   expires=now + timedelta(seconds=TICKET_SECONDS)))
        return ticket

    def consume(self, ticket):
        """The username of a valid ``ticket``, which is used up; None when unknown, used or expired."""
        if not ticket or len(ticket) > 128:
            return None
        rows = self.query(columns='$id,$user_id,@user_id.username AS username',
                          where='$id=:id AND $used IS NOT TRUE AND $expires>:now',
                          id=ticket_hash(ticket), now=datetime.now(timezone.utc),
                          for_update=True).fetch()
        if not rows:
            return None
        with self.recordToUpdate(rows[0]['id']) as record:
            record['used'] = True
        return rows[0]['username']
