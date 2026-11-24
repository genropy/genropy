"""A shutdown announced to the connected users, and its cancellation.

The announcement lives in the global store of the rootDomain register, so a
single entry reaches the pages of every domain. Each ping carries what is left
of it, computed on the server, so the countdown does not depend on the clock of
the browser.
"""

import re
from datetime import datetime, timedelta

SHUTDOWN_KEY = 'SHUTDOWN'
SHUTDOWN_GRACE_SECONDS = 60

_DELAY_RE = re.compile(r'^\s*(\d+)\s*([smh]?)\s*$')
_DELAY_UNITS = {'': 1, 's': 1, 'm': 60, 'h': 3600}


def parse_delay(text):
    """Seconds in a delay written as ``N``, ``Ns``, ``Nm`` or ``Nh``."""
    match = _DELAY_RE.match(text or '')
    if not match:
        raise ValueError("invalid delay %r: use N, Ns, Nm or Nh" % text)
    seconds = int(match.group(1)) * _DELAY_UNITS[match.group(2)]
    if not seconds:
        raise ValueError("invalid delay %r: it must be greater than zero" % text)
    return seconds


def announce_shutdown(store, seconds, reason):
    """Write the announcement in ``store`` and return its deadline."""
    deadline = datetime.now() + timedelta(seconds=seconds)
    with store as global_store:
        global_store.setItem(SHUTDOWN_KEY, dict(deadline=deadline, reason=reason))
    return deadline


def cancel_shutdown(store):
    """Withdraw the announcement; True when one was still pending."""
    with store as global_store:
        notice = shutdown_notice(global_store.getItem(SHUTDOWN_KEY))
        pending = bool(notice and notice['seconds_left'])
        # the key is cleared, not deleted: a delete at the top of a register
        # store fails in its change trigger
        global_store.setItem(SHUTDOWN_KEY, None)
    return pending


def shutdown_notice(entry, now=None):
    """What a page has to show for ``entry``: reason and seconds left, or None.

    Past the deadline the seconds left stay 0 for SHUTDOWN_GRACE_SECONDS, so a
    page that pings late still sees the deadline go by and does not take the
    end of the notice for a cancellation. After that the entry is ignored, as
    is a stale one restored with the register after a restart."""
    if not entry:
        return None
    seconds_left = (entry['deadline'] - (now or datetime.now())).total_seconds()
    if seconds_left <= -SHUTDOWN_GRACE_SECONDS:
        return None
    return dict(reason=entry['reason'], seconds_left=round(max(0, seconds_left), 1))
