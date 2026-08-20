"""Unit tests for the page-source helpers of `pages_ratchet`.

Source-only by design: no instance, no db, no daemon. That is what lets this
suite run in CI next to `test_pages_documented.py`, while the render sweep
stays local. The pages asserted on belong to the `test` package and are not
touched by the migration macros, so the expectations stay true.
"""
from pages_ratchet import page_required_packages, resource_owner_package


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

    def test_py_requires_component(self):
        """A page mixing in a component requires the package owning that resource"""
        required = page_required_packages('test/webpages/components/dashboards.py')
        assert required == {'adm', 'biz'}

    def test_py_requires_unmountable_component(self):
        """A page mixing in a component of an unmounted package names it too"""
        required = page_required_packages('test/webpages/tools/flibpicker.py')
        assert required == {'flib'}


class TestResourceOwnerPackage(object):
    """resource_owner_package tells which package a py_requires entry needs"""

    def test_package_resource(self):
        """A resource living in one package alone is owned by it"""
        assert resource_owner_package('dashboard_component/dashboard_component') == 'biz'

    def test_common_resource(self):
        """A resource under resources/common belongs to no package"""
        assert resource_owner_package('gnrcomponents/testhandler') is None

    def test_ambiguous_resource(self):
        """A resource several packages provide constrains nothing: any of them serves"""
        assert resource_owner_package('preference') is None

    def test_unknown_resource(self):
        """A resource no package provides constrains nothing"""
        assert resource_owner_package('no/such/resource') is None
