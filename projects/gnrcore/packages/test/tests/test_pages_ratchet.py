"""Unit tests for the page-source helpers of `pages_ratchet`.

Source-only by design: no instance, no db, no daemon. That is what lets this
suite run in CI next to `test_pages_documented.py`, while the render sweep
stays local. The pages asserted on belong to the `test` package and are not
touched by the migration macros, so the expectations stay true.
"""
from pages_ratchet import page_required_packages


class TestPageRequiredPackages(object):
    """page_required_packages reads the packages a page addresses off its source"""

    def test_table_kwarg(self):
        """A page whose dbSelect/tableSelect calls name tables requires their packages"""
        required = page_required_packages('test/webpages/inputfields/dbselect.py')
        assert required == {'adm', 'glbl'}

    def test_single_package(self):
        """A page addressing only its own package requires only that one"""
        required = page_required_packages('test/webpages/components/palette_importer.py')
        assert required == {'test'}

    def test_no_table(self):
        """A page addressing no table requires no package"""
        assert page_required_packages('test/webpages/html/div.py') == set()
