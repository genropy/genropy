"""Packages reached through ``Package.required_packages()`` and the packages section.

``required_packages()`` is how a package carries its own dependencies, and what
instance flavours rely on: an instance declares ``biz`` and gets ``adm`` and
``sys`` with it. The boot keeps loading that way and reports, once and in a
pasteable form, what the packages section does not declare. ``checkdep`` walks
the same closure, reading ``required_packages()`` from the source when
``main.py`` cannot be imported, so an image build installs every requirement;
``--strict`` turns the report into a failure where a refusal costs nothing.

``gnrcore:biz`` requires ``gnrcore:adm``, which requires ``gnrcore:sys``: two
levels, enough to exercise the transitive case.
"""
import logging
import os
import shutil
import sys
import tempfile

import pytest

from gnr.app.gnrapp import GnrApp, GnrPackageNotFoundException, GnrUndeclaredPackageException, \
    GnrUnresolvedPackageException
from gnr.app.gnrdeploy import GunicornDeployBuilder
from gnr.core.gnrconfig import IniConfStruct
from gnr.web.daemon.handler import GnrDaemon
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

BROKEN_MAIN = """import surely_missing_module_for_this_test
from gnr.app.gnrdbo import GnrDboPackage

class Package(GnrDboPackage):
    def required_packages(self):
        return ['gnrcore:adm']
"""

DYNAMIC_MAIN = """from gnr.app.gnrdbo import GnrDboPackage

REQUIRED = ['gnrcore:adm']

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(sqlschema='dynamicpkg', name_short='dyn', name_long='dyn', name_full='dyn')

    def required_packages(self):
        return list(REQUIRED)
"""

ATTRIBUTE_MAIN = """import surely_missing_module_for_this_test
from gnr.app.gnrdbo import GnrDboPackage

class Package(GnrDboPackage):
    required_packages = ['gnrcore:adm']
"""

BOOTABLE_ATTRIBUTE_MAIN = """from gnr.app.gnrdbo import GnrDboPackage

class Package(GnrDboPackage):
    required_packages = ('gnrcore:adm',)

    def config_attributes(self):
        return dict(sqlschema='attrpkg', name_short='attr', name_long='attr', name_full='attr')
"""

NO_REQUIREMENTS_MAIN = """class Package(object):
    pass
"""

SECONDARY_SYS = '    <gnrcore_sys pkgcode="gnrcore:sys" secondary="y"/>'

CUSTOM_ATTRIBUTE = """class Package(object):
    required_packages = ['gnrcore:flib']
"""


class TestRequiredPackagesDeclared(BaseGnrTest):

    def _app(self, *packages, extra='', **kwargs):
        declared = [DECLARE[p] for p in packages]
        if extra:
            declared.append(extra)
        with open(self.test_instance_config_path, 'w', encoding='utf-8') as fp:
            fp.write(CONFIG % '\n'.join(declared))
        return GnrApp(self.test_instance_name, **kwargs)

    def _package(self, name, main_source, requirements=None):
        root = tempfile.mkdtemp(prefix='gnrtest_pkgs_')
        folder = os.path.join(root, name)
        os.makedirs(folder)
        with open(os.path.join(folder, 'main.py'), 'w', encoding='utf-8') as fp:
            fp.write(main_source)
        if requirements:
            with open(os.path.join(folder, 'requirements.txt'), 'w', encoding='utf-8') as fp:
                fp.write('\n'.join(requirements) + '\n')
        return '    <%s pkgcode="%s" path="%s"/>' % (name, name, root)

    def test_undeclared_required_packages_still_boot(self, caplog):
        """biz alone declared: adm and sys load through required_packages(), and
        the packages section gets the lines to paste."""
        with caplog.at_level(logging.WARNING, logger='gnr.app'):
            app = self._app('biz')
        assert set(['biz', 'adm', 'sys']).issubset(set(app.packages.keys()))
        assert [e['code'] for e in app.undeclared_packages] == ['gnrcore:adm', 'gnrcore:sys']
        report = app.undeclared_packages_report()
        assert '<gnrcore_adm pkgcode="gnrcore:adm"/>' in report
        assert '<gnrcore_sys pkgcode="gnrcore:sys"/>' in report
        assert 'gnrcore:adm (required by biz)' in report
        assert 'gnrcore:sys (required by adm)' in report
        assert report in caplog.text

    def test_complete_declaration_reports_nothing(self, caplog):
        with caplog.at_level(logging.WARNING, logger='gnr.app'):
            app = self._app('biz', 'adm', 'sys')
        assert app.undeclared_packages == []
        assert 'required_packages()' not in caplog.text

    def test_declared_packages_ignores_the_project_prefix(self):
        app = self._app('biz', 'adm', 'sys')
        assert app.declared_packages == set(['biz', 'adm', 'sys'])

    def test_checkdep_walks_the_closure(self):
        """Nothing is loaded in checkdep mode, yet the requirements of adm and sys
        are collected: the closure is read from the sources."""
        app = self._app('biz', checkdepcli=True)
        assert list(app.packages.keys()) == []
        assert set(app.package_closure().keys()) == set(['biz', 'adm', 'sys'])
        owners = set(sum(app.instance_packages_dependencies.values(), []))
        assert set(['adm', 'sys']).issubset(owners)

    def test_checkdep_reads_required_packages_without_importing(self):
        """A main.py that does not import in this environment still contributes
        its required_packages() and its requirements.txt."""
        broken = self._package('brokenpkg', BROKEN_MAIN, ['surely-missing-dist-for-this-test'])
        app = self._app('sys', extra=broken, checkdepcli=True)
        closure = app.package_closure()
        assert 'adm' in closure
        assert closure['adm']['required_by'] == set(['brokenpkg'])
        assert app.instance_packages_dependencies['surely-missing-dist-for-this-test'] == ['brokenpkg']

    def test_checkdep_falls_back_to_import_on_a_dynamic_list(self):
        dynamic = self._package('dynamicpkg', DYNAMIC_MAIN)
        app = self._app('sys', extra=dynamic, checkdepcli=True)
        assert 'adm' in app.package_closure()

    def test_strict_check_raises_on_an_undeclared_package(self):
        app = self._app('biz', checkdepcli=True)
        with pytest.raises(GnrUndeclaredPackageException) as excinfo:
            app.assert_packages_declared()
        assert '<gnrcore_adm pkgcode="gnrcore:adm"/>' in str(excinfo.value)

    def test_strict_check_passes_on_a_complete_declaration(self):
        app = self._app('biz', 'adm', 'sys', checkdepcli=True)
        app.assert_packages_declared()

    def _read(self, source):
        app = self._app('sys', checkdepcli=True)
        path = os.path.join(tempfile.mkdtemp(prefix='gnrtest_src_'), 'main.py')
        with open(path, 'w', encoding='utf-8') as fp:
            fp.write(source)
        return app._required_packages_from_source(path)

    def _custom(self, app, pkgid, source):
        folder = os.path.join(app.instanceFolder, 'custom', pkgid)
        os.makedirs(folder)
        with open(os.path.join(folder, 'custom.py'), 'w', encoding='utf-8') as fp:
            fp.write(source)
        return os.path.dirname(folder)

    def test_reader_attribute_form(self):
        assert self._read(ATTRIBUTE_MAIN) == (['gnrcore:adm'], None)

    def test_reader_method_form(self):
        assert self._read(BROKEN_MAIN) == (['gnrcore:adm'], None)

    def test_reader_nothing_declared_on_a_gnr_base(self):
        assert self._read("import gnr.app.gnrdbo\n\n"
                          "class Package(gnr.app.gnrdbo.GnrDboPackage):\n    pass\n") == (None, None)
        assert self._read("X = 1\n") == (None, None)

    @pytest.mark.parametrize('source, reason', [
        (DYNAMIC_MAIN, 'not a literal list'),
        ("from mycompany.base import CompanyPackage\n\n"
         "class Package(CompanyPackage):\n    pass\n", 'inherits from CompanyPackage'),
        ("class Package(object):\n    def required_packages(self):\n"
         "        if self:\n            return ['a']\n        return ['b']\n", '2 return statements'),
        ("class Package(object):\n    required_packages = ['a']\n\n"
         "    def required_packages(self):\n        return ['b']\n", 'declared more than once'),
        ("class Package(object):\n    required_packages = ['a', 1]\n", 'not a literal list'),
        ("class Package(:\n", 'cannot read main.py'),
    ])
    def test_reader_unresolved(self, source, reason):
        required, found = self._read(source)
        assert required is None
        assert reason in found

    def test_boot_loads_the_attribute_form(self):
        attrpkg = self._package('attrpkg', BOOTABLE_ATTRIBUTE_MAIN)
        app = self._app('sys', extra=attrpkg)
        assert app.packages['attrpkg'].required_packages() == ['gnrcore:adm']
        assert 'adm' in app.packages
        assert 'attrpkg' in app.package_closure()['adm']['required_by']

    def test_custom_attribute_overrides_main_on_boot_and_in_the_closure(self):
        app = self._app('biz', checkdepcli=True)
        custom_root = self._custom(app, 'biz', CUSTOM_ATTRIBUTE)
        try:
            app = self._app('biz', 'adm', 'sys')
            assert app.packages['biz'].required_packages() == ['gnrcore:flib']
            assert 'flib' in app.packages
            static = self._app('biz', checkdepcli=True, static_closure=True)
            assert static.package_closure()['flib']['required_by'] == set(['biz'])
            assert 'adm' not in static.package_closure()
        finally:
            shutil.rmtree(custom_root)

    def test_static_closure_reports_an_unresolved_package(self):
        dynamic = self._package('dynamicpkg', DYNAMIC_MAIN)
        app = self._app('sys', extra=dynamic, checkdepcli=True, static_closure=True)
        assert 'adm' not in app.package_closure()
        assert [e['code'] for e in app.unresolved_packages] == ['dynamicpkg']
        assert 'dynamicpkg: required_packages in main.py is not a literal list' \
            in app.unresolved_packages_report()

    def test_static_closure_reports_a_missing_package(self):
        missing = '    <nosuchpkg pkgcode="nosuchpkg"/>'
        app = self._app('sys', extra=missing, checkdepcli=True, static_closure=True)
        assert [e['code'] for e in app.unresolved_packages] == ['nosuchpkg']
        report = app.unresolved_packages_report()
        assert 'nosuchpkg: package folder not found' in report
        assert 'literal list' not in report

    def test_boot_still_raises_on_a_missing_package(self):
        with pytest.raises(GnrPackageNotFoundException):
            self._app('sys', extra='    <nosuchpkg pkgcode="nosuchpkg"/>', checkdepcli=True)

    def test_requirements_file_holds_the_closure_without_importing(self):
        broken = self._package('brokenpkg', ATTRIBUTE_MAIN, ['surely-missing-dist-for-this-test'])
        app = self._app('sys', extra=broken, checkdepcli=True, static_closure=True)
        target = os.path.join(tempfile.mkdtemp(prefix='gnrtest_req_'), 'requirements.txt')
        app.write_requirements_file(target)
        with open(target, encoding='utf-8') as fp:
            lines = fp.read().splitlines()
        assert 'surely-missing-dist-for-this-test' in lines
        assert lines == sorted(set(lines))

    def test_requirements_file_raises_naming_the_package(self):
        dynamic = self._package('dynamicpkg', DYNAMIC_MAIN, ['some-dist-for-this-test'])
        app = self._app('sys', extra=dynamic, checkdepcli=True, static_closure=True)
        target = os.path.join(tempfile.mkdtemp(prefix='gnrtest_req_'), 'requirements.txt')
        with pytest.raises(GnrUnresolvedPackageException) as excinfo:
            app.write_requirements_file(target)
        assert not os.path.exists(target)
        assert 'dynamicpkg' in str(excinfo.value)

    def test_enabled_packages_reach_sys_through_the_closure(self):
        """The task scheduler builds the app with only sys enabled: an instance
        declaring only biz still gets sys, reached through adm."""
        app = self._app('biz', enabled_packages=['gnrcore:sys'])
        assert list(app.packages.keys()) == ['sys']
        assert app.db.table('sys.task').fullname == 'sys.task'

    def test_enabled_packages_keep_their_declared_attributes(self):
        app = self._app('biz', extra=SECONDARY_SYS, enabled_packages=['gnrcore:sys'], checkdepcli=True)
        assert list(app.config['packages'].keys()) == ['gnrcore:sys']
        assert app.config['packages'].getAttr('gnrcore:sys')['secondary'] == 'y'

    def test_primary_sys_reached_through_the_closure(self):
        assert self._app('biz', config_only=True, static_closure=True).has_primary_sys_package()
        assert self._app('sys', config_only=True, static_closure=True).has_primary_sys_package()

    def test_primary_sys_declared_secondary(self):
        app = self._app('biz', extra=SECONDARY_SYS, config_only=True, static_closure=True)
        assert not app.has_primary_sys_package()

    def test_primary_sys_without_sys(self):
        nosys = self._package('nosyspkg', NO_REQUIREMENTS_MAIN)
        app = self._app(extra=nosys, config_only=True, static_closure=True)
        assert not app.has_primary_sys_package()

    def test_daemon_starts_the_scheduler_of_a_flavour(self):
        self._app('biz', checkdepcli=True)
        assert GnrDaemon.hasSysPackageAndIsPrimary(None, self.test_instance_name)
        self._app('biz', extra=SECONDARY_SYS, checkdepcli=True)
        assert not GnrDaemon.hasSysPackageAndIsPrimary(None, self.test_instance_name)

    def test_deploy_builder_configures_the_task_workers_of_a_flavour(self):
        app = self._app('biz', checkdepcli=True)
        group = IniConfStruct().section('group', self.test_instance_name)
        GunicornDeployBuilder(self.test_instance_name, app=app).taskWorkersConf(group)
        assert '%s_taskworkers' % self.test_instance_name in group.keys()

    def test_config_only_leaves_no_global_side_effect(self):
        """The gnrdaemon builds a config only app in its own process: no module
        finder, no logging.xml, no instance custom.py, no database."""
        instance_folder = self._app('biz', checkdepcli=True).instanceFolder
        probe = logging.getLogger('gnrtest.config_only_probe')
        logging_xml = os.path.join(instance_folder, 'logging.xml')
        custom_folder = os.path.join(instance_folder, 'custom')
        with open(logging_xml, 'w', encoding='utf-8') as fp:
            fp.write('<?xml version="1.0" ?>\n<GenRoBag><probe path="%s" level="DEBUG"/></GenRoBag>' % probe.name)
        os.makedirs(custom_folder)
        with open(os.path.join(custom_folder, 'custom.py'), 'w', encoding='utf-8') as fp:
            fp.write('raise RuntimeError("instance custom.py imported")\n')
        meta_path = list(sys.meta_path)
        try:
            app = self._app('biz', config_only=True, static_closure=True)
            assert sys.meta_path == meta_path
            assert probe.level == logging.NOTSET
            assert not hasattr(app, 'db')
            assert app.has_primary_sys_package()
            os.remove(os.path.join(custom_folder, 'custom.py'))
            self._app('biz', checkdepcli=True)
            assert probe.level == logging.DEBUG
        finally:
            probe.setLevel(logging.NOTSET)
            os.remove(logging_xml)
            shutil.rmtree(custom_folder)
