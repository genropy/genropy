"""Tests for packages declared with an explicit path in the instanceconfig.

InstanceMaker writes a path attribute for every package passed as a
(package, path) pair. Such a package can live anywhere on the filesystem,
outside the project packages folder and outside every packages root declared
in environment.xml, so the attribute is the only way to resolve it.
"""

import os
import shutil
import tempfile

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.dev.makers.instance import InstanceMaker

from core.common import BaseGnrTest

EXTERNAL_PACKAGE_MAIN = """from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='external package', sqlschema='extpkg', sqlprefix=True,
                    name_short='Ext', name_long='External', name_full='External package')

    def config_db(self, pkg):
        pass


class Table(GnrDboTable):
    pass
"""

# a distribution genropy itself depends on: the dependency check must find it
# through the declared path, and must not report it as missing
EXTERNAL_PACKAGE_REQUIREMENTS = "packaging\n"


class TestExternalPackagePath(BaseGnrTest):
    """A package reachable only through the path attribute of its instanceconfig"""

    package_id = 'extpkg'
    abs_instance_name = 'extpkg_abs'
    rel_instance_name = 'extpkg_rel'

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.tempdir = tempfile.mkdtemp()
        cls.external_packages_path = os.path.join(cls.tempdir, 'external_packages')
        package_path = os.path.join(cls.external_packages_path, cls.package_id)
        os.makedirs(package_path)
        with open(os.path.join(package_path, 'main.py'), 'w', encoding='utf-8') as fp:
            fp.write(EXTERNAL_PACKAGE_MAIN)
        with open(os.path.join(package_path, 'requirements.txt'), 'w', encoding='utf-8') as fp:
            fp.write(EXTERNAL_PACKAGE_REQUIREMENTS)
        cls.makeInstance(cls.abs_instance_name, cls.external_packages_path)
        rel_config_path = os.path.join(cls.test_instance_path, cls.rel_instance_name, 'config')
        cls.makeInstance(cls.rel_instance_name,
                         os.path.relpath(cls.external_packages_path, rel_config_path))

    @classmethod
    def teardown_class(cls):
        super().teardown_class()
        shutil.rmtree(cls.tempdir, ignore_errors=True)

    @classmethod
    def makeInstance(cls, instance_name, packages_path):
        """Create an instance declaring the external package at packages_path"""
        InstanceMaker(instance_name, base_path=cls.test_instance_path,
                      packages=[(cls.package_id, packages_path)],
                      authentication=False).do()

    def loadApp(self, instance_name):
        return GnrApp(instance_name, db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(self.tempdir, instance_name)))

    def expectedPackageFolder(self):
        return os.path.realpath(os.path.join(self.external_packages_path, self.package_id))

    def test_instancemaker_declares_path(self):
        """InstanceMaker writes the path attribute the instance depends on"""
        config = Bag(os.path.join(self.test_instance_path, self.abs_instance_name,
                                  'config', 'instanceconfig.xml'))
        assert config['packages.%s?path' % self.package_id] == self.external_packages_path

    def test_package_is_not_in_packages_roots(self):
        """Without the declared path there would be no way to find the package"""
        app = self.loadApp(self.abs_instance_name)
        with pytest.raises(Exception, match='not found'):
            app.pkg_name_to_path(self.package_id)

    def test_app_boots_with_absolute_path(self):
        app = self.loadApp(self.abs_instance_name)
        assert self.package_id in app.packages
        assert os.path.realpath(
            app.packages[self.package_id].packageFolder) == self.expectedPackageFolder()

    def test_app_boots_with_relative_path(self):
        """A relative path is resolved against the instance folder"""
        app = self.loadApp(self.rel_instance_name)
        assert os.path.realpath(
            app.packages[self.package_id].packageFolder) == self.expectedPackageFolder()

    def test_dependencies_found_through_declared_path(self):
        """The requirements of the external package are collected at boot"""
        app = self.loadApp(self.abs_instance_name)
        assert app.instance_packages_dependencies['packaging'] == [self.package_id]
        missing, wrong = app.check_package_missing_dependencies()
        assert missing == []
