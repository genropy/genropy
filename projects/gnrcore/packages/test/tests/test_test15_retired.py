"""gnrcore:test15 is retired to a placeholder that only warns.

Its examples live in gnrcore:test now. The package itself survives as a bare
`main.py` because instances outside this repository still mount it, and a
package that cannot be found stops an instance from starting.
"""
import importlib.util
import logging
import os
import subprocess

from gnr.core.gnrbag import Bag

PACKAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
TEST15_DIR = os.path.join(PACKAGES_DIR, 'test15')
GNRDEVELOP_DIR = os.path.join(PACKAGES_DIR, os.pardir, 'instances', 'gnrdevelop')
INSTANCECONFIG = os.path.join(GNRDEVELOP_DIR, 'config', 'instanceconfig.xml')
TEST_LOCALIZATION = os.path.join(PACKAGES_DIR, 'test', 'localization.xml')


def load_test15_main():
    spec = importlib.util.spec_from_file_location('test15_main', os.path.join(TEST15_DIR, 'main.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTest15Placeholder(object):
    """What is left of the package is a main.py that warns"""

    def test_only_main_is_left(self):
        """No model, resource, page or localization survives in the repository"""
        tracked = subprocess.run(['git', 'ls-files', '.'], cwd=TEST15_DIR, capture_output=True,
                                 text=True, check=True).stdout.split()
        assert tracked == ['main.py']

    def test_inited_warns(self, caplog):
        """Mounting the package logs a warning naming it as retired"""
        module = load_test15_main()
        with caplog.at_level(logging.WARNING, logger='gnr.pkg'):
            module.Package.onApplicationInited(None)
        warnings = [r for r in caplog.records if r.name == 'gnr.pkg' and r.levelno == logging.WARNING]
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert 'gnrcore:test15' in message
        assert 'retired' in message

    def test_schema_is_kept(self):
        """Existing databases keep mapping the package onto its own schema"""
        module = load_test15_main()
        assert module.Package.config_attributes(None)['sqlschema'] == 'test15'


class TestGnrdevelopWithoutTest15(object):
    """The instance the suites boot no longer mounts the package"""

    def test_not_mounted(self):
        packages = Bag(INSTANCECONFIG)['packages']
        pkgcodes = [node.attr.get('pkgcode') for node in packages]
        assert 'gnrcore:test15' not in pkgcodes
        assert 'gnrcore:test' in pkgcodes

    def test_not_in_menu(self):
        menu_packages = Bag(INSTANCECONFIG).getAttr('menu', 'package').split(',')
        assert 'test15' not in menu_packages
        assert 'test' in menu_packages

    def test_no_test15_database(self):
        assert not os.path.exists(os.path.join(GNRDEVELOP_DIR, 'data', 'test15.db'))


class TestTestLocalization(object):
    """test/localization.xml carries no block of the deleted test15 models"""

    def test_no_orphan_model_blocks(self):
        with open(TEST_LOCALIZATION, encoding='utf-8') as localization:
            content = localization.read()
        assert 'path="model/nodetbl.py"' not in content
        assert 'path="model/recursive.py"' not in content
