"""Unit tests for the sweep loop: what it skips, and when it waits.

`page_statuses` decides two things no other check covers: which pages it leaves
out because the instance does not mount their packages, and when a failed render
is a stalled register worth waiting for rather than a broken page. The drain path
costs `PORT_DRAIN_ROUNDS * PORT_DRAIN_SECONDS` and latches itself off when it
gives up, so it has to fire where the register is stalled and nowhere else.

These tests drive the loop with its three IO boundaries — the mounted packages,
the render and the wait — answered by the test through a subclass, so they need
no site, no daemon and no wait.

The module is imported rather than its class, so that `TestPagesSmoke` does not
land in this module's namespace and get collected a second time here.
"""
import test_pages_smoke as smoke
from pages_ratchet import discover_pages, page_required_packages

FAILED = '500 Internal Server Error'
SERVED = '200 OK'


def stalled_status():
    """The status `render_status` reports when the register cannot be reached"""
    return '%s: [Errno 49] Can\'t assign requested address' % smoke.REGISTER_UNREACHABLE


def all_required_packages(pages):
    """Every package the given pages address, so that none of them is skipped"""
    required = set()
    for page_path in pages:
        required |= page_required_packages(page_path)
    return required


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
    mounted = all_required_packages(pages)

    class Sweep(smoke.TestPagesSmoke):
        probes = []
        drained = False

        @classmethod
        def mounted_packages(cls):
            return mounted

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

    statuses, skipped = Sweep.page_statuses()

    assert not skipped
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
    mounted = all_required_packages(pages)

    class Sweep(smoke.TestPagesSmoke):
        probes = []
        drained = False

        @classmethod
        def mounted_packages(cls):
            return mounted

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

    statuses, skipped = Sweep.page_statuses()

    assert not skipped
    assert Sweep.probes == [pages[0]]
    assert statuses[stalled] == SERVED
    assert not [page for page, status in statuses.items() if status != SERVED]


def test_a_page_of_an_unmounted_package_is_skipped_not_rendered():
    """A page the instance cannot serve is left out and reported apart

    Rendering it would fail for a reason that is not a defect of the page, so
    the sweep neither renders it nor counts it: it returns it in its own map,
    naming the packages that are missing.
    """
    pages = discover_pages()
    bound = next(page for page in pages if page_required_packages(page))
    absent = sorted(page_required_packages(bound))[0]
    mounted = all_required_packages(pages) - {absent}

    class Sweep(smoke.TestPagesSmoke):
        rendered = []

        @classmethod
        def mounted_packages(cls):
            return mounted

        @classmethod
        def render_status(cls, page_path):
            cls.rendered.append(page_path)
            return SERVED

    statuses, skipped = Sweep.page_statuses()

    assert bound in skipped
    assert absent in skipped[bound]
    assert bound not in statuses
    assert bound not in Sweep.rendered
    # every other page of that package went the same way, and nothing else did
    assert all(absent in page_required_packages(page) for page in skipped)
