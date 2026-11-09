"""Ratchet against a page using the same frameCode literal twice.

`TestHandlerFull` renders every case of a page on one page and gives each case
its own datapath, but not its own frameCode
(`resources/common/gnrcomponents/testhandler.py:50-51`), so two cases that build
a frame with the same code collide. The client raises while it builds the
structure, after the page has already answered 200 -- which is why the render
sweep is blind to this defect and why it needs a check of its own.

Source-only like `test_pages_documented.py`: no instance, no daemon, no
database, which is what lets it run in CI. It is a ratchet against
`framecode_debt.txt` and fails in both directions -- a page that collides while
outside the list is a regression, a list entry that no longer collides is stale,
so the list can only shrink.
"""
from pages_ratchet import FRAMECODE_RATCHET, assert_ratchet, discover_pages, framecode_collisions


def test_pages_have_unique_framecodes():
    """Every page uses each of its frameCode literals once, except the debt list"""
    colliding = [page_path for page_path in discover_pages()
                 if framecode_collisions(page_path)]
    assert_ratchet(colliding, FRAMECODE_RATCHET, 'pages with duplicate frameCodes')
