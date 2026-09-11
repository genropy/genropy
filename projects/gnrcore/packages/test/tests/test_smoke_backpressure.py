"""Unit tests for the port-exhaustion backpressure of the render sweep.

The drain path of `page_statuses` costs `PORT_DRAIN_ROUNDS * PORT_DRAIN_SECONDS`
and, when it gives up, latches itself off for the rest of the run: it has to
fire where the register is stalled and nowhere else. These tests drive the loop
with its two IO boundaries — the render and the sleep — answered by the test, so
they need no site, no daemon and no wait.

The module is imported rather than its class, so that `TestPagesSmoke` does not
land in this module's namespace and get collected a second time here.
"""
import test_pages_smoke as smoke
from pages_ratchet import discover_pages

FAILED = '500 Internal Server Error'
SERVED = '200 OK'


def stalled_status():
    """The status `render_status` reports when the register cannot be reached"""
    return '%s: [Errno 49] Can\'t assign requested address' % smoke.REGISTER_UNREACHABLE


def test_a_broken_first_page_neither_drains_nor_disarms():
    """A page that fails before any page has rendered is recorded, not probed

    Pages are swept in sort order, so the first one can be a page that simply
    fails. With no page known to render, the sweep has no probe to tell an
    exhausted register from a broken page: it must not spend the drain on the
    failing page itself, and above all must not latch `register_dead` on it,
    which would leave every later page unprotected — a genuine exhaustion
    downstream would then be reported as a mass of regressions.
    """
    pages = discover_pages()
    broken, stalled = pages[0], pages[-1]

    class Sweep(smoke.TestPagesSmoke):
        probes = []
        drained = False

        @classmethod
        def render_status(cls, page_path):
            if page_path == broken:
                return FAILED
            if page_path == stalled and not cls.drained:
                return stalled_status()
            return SERVED

        @classmethod
        def wait_ports_drained(cls, probe_path):
            cls.probes.append(probe_path)
            cls.drained = True
            return True

    statuses = Sweep.page_statuses()

    # the broken first page cost no drain round and stayed a plain failure
    assert statuses[broken] == FAILED
    assert broken not in Sweep.probes
    # and the protection was still armed for the stall further down, probed
    # with a page that had answered 200 rather than with the stalled one
    assert Sweep.probes == [pages[1]]
    assert statuses[stalled] == SERVED


def test_a_stall_is_drained_and_probed_with_a_page_that_rendered():
    """A stalled render waits for the ports to drain, then answers 200"""
    pages = discover_pages()
    stalled = pages[1]

    class Sweep(smoke.TestPagesSmoke):
        probes = []
        drained = False

        @classmethod
        def render_status(cls, page_path):
            if page_path == stalled and not cls.drained:
                return stalled_status()
            return SERVED

        @classmethod
        def wait_ports_drained(cls, probe_path):
            cls.probes.append(probe_path)
            cls.drained = True
            return True

    statuses = Sweep.page_statuses()

    assert Sweep.probes == [pages[0]]
    assert statuses[stalled] == SERVED
    assert not [page for page, status in statuses.items() if status != SERVED]
