"""Documentation ratchet over the gnrcore test-page packages.

`TestHandler.testHandler` prints the module docstring's first line as the page
title (`resources/common/gnrcomponents/testhandler.py:29-31`) and every `test_*`
docstring as that card's description (`testhandler.py:54-56`), so a page missing
them is an undocumented page in the UI, not just an undocumented file.

This check reads the source and nothing else — no instance, no daemon, no
database — which is why it lives apart from the render sweep and runs in CI. It
is a ratchet against `docstring_debt.txt` and fails in both directions: a page
that offends while outside the list is a regression, and a list entry that no
longer offends is a stale entry, so the list can only shrink.
"""
from pages_ratchet import DOCSTRING_RATCHET, assert_ratchet, discover_pages, docstring_defects


def test_pages_are_documented():
    """Every page documents its title and its test methods, except the debt list"""
    undocumented = [page_path for page_path in discover_pages()
                    if docstring_defects(page_path)]
    assert_ratchet(undocumented, DOCSTRING_RATCHET, 'undocumented pages')
