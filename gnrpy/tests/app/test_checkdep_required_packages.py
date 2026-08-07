"""Tests for the dependency check performed by `gnr app checkdep`.

`GnrApp.check_package_dependencies()` must collect the requirements of every
package the instance really loads, i.e. the packages declared in
instanceconfig.xml plus the transitive closure of the ones pulled in through
`Package.required_packages()`.

The check runs in `checkdepcli` mode, so `GnrApp.init()` returns before the
database is built: no db is needed here.
"""

import os

from gnr.app.gnrapp import GnrApp
from core.common import BaseGnrTest

# gnrcore:biz requires gnrcore:adm, which in turn requires gnrcore:sys.
# The instanceconfig below declares biz only, so adm and sys must be
# discovered through required_packages().
INSTANCE_CONFIG = """<?xml version="1.0" ?>
<GenRoBag>
  <db filename="test.db" implementation="sqlite"/>
  <packages>
    <gnrcore_biz pkgcode="gnrcore:biz"/>
  </packages>
</GenRoBag>"""

BIZ_REQUIREMENTS = ['psutil']
ADM_REQUIREMENTS = ['pyotp', 'python_dateutil', 'qrcode']
SYS_REQUIREMENTS = ['pdf2image', 'watchdog', 'PyPDF2']


class TestCheckdepRequiredPackages(BaseGnrTest):
    """Dependency collection must follow the required_packages() closure."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        with open(cls.test_instance_config_path, 'w', encoding='utf-8') as fp:
            fp.write(INSTANCE_CONFIG)
        cls.app = GnrApp(cls.test_instance_name, checkdepcli=True)

    def test_declared_package_requirements(self):
        """The explicitly declared package still contributes its requirements."""
        deps = self.app.instance_packages_dependencies
        for dep in BIZ_REQUIREMENTS:
            assert dep in deps, f"{dep} (biz) not collected"
            assert 'biz' in deps[dep]

    def test_implicit_package_requirements(self):
        """adm is pulled in by biz.required_packages(): its deps must be there."""
        deps = self.app.instance_packages_dependencies
        for dep in ADM_REQUIREMENTS:
            assert dep in deps, f"{dep} (adm) not collected"
            assert 'adm' in deps[dep]

    def test_transitive_package_requirements(self):
        """sys is required by adm, itself required by biz: two levels down."""
        deps = self.app.instance_packages_dependencies
        for dep in SYS_REQUIREMENTS:
            assert dep in deps, f"{dep} (sys) not collected"
            assert 'sys' in deps[dep]

    def test_no_duplicated_package_in_closure(self):
        """A package reached more than once is accounted for only once."""
        for dep, packages in self.app.instance_packages_dependencies.items():
            assert len(packages) == len(set(packages)), f"{dep} collected twice"

    def test_packages_not_loaded_in_checkdep_mode(self):
        """The check must not build GnrPackage objects nor touch the db."""
        assert len(self.app.packages) == 0
        assert getattr(self.app, 'db', None) is None

    def test_required_packages_resolution_survives_broken_main(self):
        """A main.py that cannot be imported is warned about, not fatal."""
        broken = os.path.join(self.tmp_conf_dir, 'brokenpkg')
        os.makedirs(os.path.join(broken, 'brokenpkg'), exist_ok=True)
        with open(os.path.join(broken, 'brokenpkg', 'main.py'), 'w',
                  encoding='utf-8') as fp:
            fp.write("import a_module_that_does_not_exist\n")
        assert self.app.package_required_packages(broken, 'brokenpkg') == []
