"""An instance must declare every package it really loads.

`Package.required_packages()` is a second, implicit way of listing an instance's
packages, and the requirements of a package pulled in that way were never seen by
`check_package_dependencies()`, which reads `instanceconfig.xml` alone. Rather
than teaching the check a second source of truth, the boot now refuses to start
when a required package is missing from `instanceconfig.xml`, so the two lists
cannot drift apart.

`gnrcore:biz` requires `gnrcore:adm`, which requires `gnrcore:sys`: two levels,
enough to exercise the transitive case.
"""

import pytest

from gnr.app.gnrapp import GnrApp, GnrUndeclaredPackageException
from core.common import BaseGnrTest

CONFIG = """<?xml version="1.0" ?>
<GenRoBag>
  <db filename="test.db" implementation="sqlite"/>
  <packages>
%s
  </packages>
</GenRoBag>"""

DECLARE = {
    'sys': '    <gnrcore_sys pkgcode="gnrcore:sys"/>',
    'adm': '    <gnrcore_adm pkgcode="gnrcore:adm"/>',
    'biz': '    <gnrcore_biz pkgcode="gnrcore:biz"/>',
}


class TestRequiredPackagesDeclared(BaseGnrTest):

    def _app(self, *packages):
        with open(self.test_instance_config_path, 'w', encoding='utf-8') as fp:
            fp.write(CONFIG % '\n'.join(DECLARE[p] for p in packages))
        return GnrApp(self.test_instance_name)

    def test_undeclared_required_package_stops_the_boot(self):
        """biz requires adm: declaring biz alone must not start."""
        with pytest.raises(GnrUndeclaredPackageException) as excinfo:
            self._app('biz')
        message = str(excinfo.value)
        assert 'gnrcore:adm' in message
        assert 'instanceconfig.xml' in message

    def test_undeclared_transitive_package_stops_the_boot(self):
        """adm requires sys: the second level is caught too."""
        with pytest.raises(GnrUndeclaredPackageException) as excinfo:
            self._app('biz', 'adm')
        assert 'gnrcore:sys' in str(excinfo.value)

    def test_complete_declaration_boots(self):
        """The whole closure declared: every package is loaded."""
        app = self._app('biz', 'adm', 'sys')
        assert set(['biz', 'adm', 'sys']).issubset(set(app.packages.keys()))

    def test_declared_packages_ignores_the_project_prefix(self):
        """A requirement reads 'gnrcore:adm' while the declaration may be keyed
        by pkgcode or by a bare label: both name the same package."""
        app = self._app('biz', 'adm', 'sys')
        assert app.declared_packages == set(['biz', 'adm', 'sys'])
