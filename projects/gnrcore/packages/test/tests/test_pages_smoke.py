"""Render sweep over the gnrcore test-page packages.

Every page under the `webpages/` folder of `test` and `test15` is rendered
through a real WSGI request against the gnrdevelop site. The sweep is a ratchet
against `smoke_known_failures.txt` and fails in both directions: a page that
fails while outside the list is a regression, and a list entry that answers 200
is a stale entry, so the list can only shrink. Pages are discovered by walking
the tree (`pages_ratchet.discover_pages`), so the sweep shrinks by itself as
test15 empties.

This half needs a booted site and a running daemon, which is why the
documentation ratchet lives in `test_pages_documented.py` instead: a check that
can skip must not be the one guarding the documentation debt.

What a 200 does not prove: a Genropy page answers the first GET with its
bootstrap document and the client POSTs back to the same url to have the
structure built, so a page can answer 200 here and still fail while building.
The browser pass at the end of each migration macro is what covers that.
"""
import time

from Pyro4.errors import CommunicationError

from webcommon import BaseGnrDaemonTest

from pages_ratchet import SMOKE_RATCHET, assert_ratchet, discover_pages, page_url

# Every page render opens ~79 short-lived loopback connections to the site
# register (`gnr/web/daemon/siteregister_client.py` connects and releases a
# Pyro proxy per register call), and each one parks in TIME_WAIT for 2*MSL.
# A full-speed sweep therefore exhausts the OS ephemeral port range (16384
# ports on macOS) after ~206 renders: the next render fails with
# `Pyro4.errors.CommunicationError ... [Errno 49] Can't assign requested
# address` — sometimes raised through the WSGI call, sometimes surfacing as a
# spurious 500 — while the register itself stays healthy. The churn is
# framework behaviour this suite must not change, so the sweep applies
# backpressure instead: when a render fails while the register is unreachable
# (told apart by re-rendering a page that already answered 200), it sleeps
# until the TIME_WAIT backlog drains and renders the page again. A full sweep
# pays about one 35s drain round on a 16384-port host (none expected on a
# Linux-sized range), and a failing page can add one when it fails with
# CommunicationError or before any page has answered 200.
PORT_DRAIN_SECONDS = 35  # > 2*MSL on macOS (30s); Linux (60s) needs two rounds
PORT_DRAIN_ROUNDS = 3
REGISTER_UNREACHABLE = 'register unreachable'


class TestPagesSmoke(BaseGnrDaemonTest):
    """Renders every test page of both packages against the gnrdevelop site"""

    @classmethod
    def render_status(cls, page_path):
        """HTTP status of one render; an unreachable register becomes a status"""
        try:
            return cls.client.get(page_url(page_path))['status']
        except CommunicationError as error:
            return '%s: %s' % (REGISTER_UNREACHABLE, error)

    @classmethod
    def wait_ports_drained(cls, probe_path):
        """Sleep until the probe page renders again; False if it never does"""
        for _ in range(PORT_DRAIN_ROUNDS):
            time.sleep(PORT_DRAIN_SECONDS)
            if cls.render_status(probe_path).startswith('200'):
                return True
        return False

    @classmethod
    def page_statuses(cls):
        """HTTP status of every discovered page, absorbing port-exhaustion stalls"""
        statuses = {}
        canary = None
        register_dead = False
        for page_path in discover_pages():
            status = cls.render_status(page_path)
            if not status.startswith('200') and not register_dead:
                probe = canary or page_path
                if (status.startswith(REGISTER_UNREACHABLE)
                        or not cls.render_status(probe).startswith('200')):
                    if cls.wait_ports_drained(probe):
                        status = cls.render_status(page_path)
                    else:
                        register_dead = True
            if status.startswith('200') and canary is None:
                canary = page_path
            statuses[page_path] = status
        return statuses

    def test_pages_answer_200(self):
        """Every page returns 200, except the ones in smoke_known_failures.txt"""
        failing = [page_path for page_path, status in self.page_statuses().items()
                   if not status.startswith('200')]
        assert_ratchet(failing, SMOKE_RATCHET, 'failing pages')
