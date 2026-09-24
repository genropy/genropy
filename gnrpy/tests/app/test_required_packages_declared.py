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

from gnr.app.cli import gnrcheckdep
from gnr.app.gnrapp import GnrApp, GnrPackageNotFoundException, GnrUndeclaredPackageException
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

CUSTOM_ATTRIBUTE = """class Package(object):
    required_packages = ['gnrcore:email']
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

    def _checkdep(self, monkeypatch, *args):
        monkeypatch.setattr(sys, 'argv', ['gnr app checkdep'] + list(args) + [self.test_instance_name])
        with pytest.raises(SystemExit) as excinfo:
            gnrcheckdep.main()
            raise SystemExit(0)
        return excinfo.value.code

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
            assert app.packages['biz'].required_packages() == ['gnrcore:email']
            assert 'email' in app.packages
            static = self._app('biz', checkdepcli=True, static_closure=True)
            assert static.package_closure()['email']['required_by'] == set(['biz'])
            assert static.package_closure()['adm']['required_by'] == set(['email'])
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

    def test_checkdep_requirements_prints_the_closure_without_importing(self, monkeypatch, capsys):
        broken = self._package('brokenpkg', ATTRIBUTE_MAIN, ['surely-missing-dist-for-this-test'])
        self._app('sys', extra=broken, checkdepcli=True)
        target = os.path.join(tempfile.mkdtemp(prefix='gnrtest_req_'), 'requirements.txt')
        assert self._checkdep(monkeypatch, '--requirements', target) == 0
        with open(target, encoding='utf-8') as fp:
            lines = fp.read().splitlines()
        assert 'surely-missing-dist-for-this-test' in lines
        assert lines == sorted(set(lines))
        assert 'Cannot compute' not in capsys.readouterr().err

    def test_checkdep_requirements_fails_naming_the_package(self, monkeypatch, capsys):
        dynamic = self._package('dynamicpkg', DYNAMIC_MAIN, ['some-dist-for-this-test'])
        self._app('sys', extra=dynamic, checkdepcli=True)
        target = os.path.join(tempfile.mkdtemp(prefix='gnrtest_req_'), 'requirements.txt')
        assert self._checkdep(monkeypatch, '--requirements', target) == 5
        assert not os.path.exists(target)
        assert 'dynamicpkg' in capsys.readouterr().err

    def test_check_package_imports_names_every_failure(self):
        first = self._package('brokenpkg', BROKEN_MAIN)
        second = self._package('attrbroken', ATTRIBUTE_MAIN)
        app = self._app('sys', extra=first + '\n' + second, checkdepcli=True, static_closure=True)
        failures = app.check_package_imports()
        assert [entry['code'] for entry, error in failures] == ['attrbroken', 'brokenpkg']
        report = app.package_imports_report(failures)
        assert 'brokenpkg: GnrImportException' in report
        assert 'surely_missing_module_for_this_test' in report

    def test_check_package_imports_loads_custom_py(self):
        app = self._app('biz', checkdepcli=True)
        custom_root = self._custom(app, 'adm', 'import surely_missing_module_for_this_test\n')
        try:
            app = self._app('biz', checkdepcli=True, static_closure=True)
            failures = app.check_package_imports()
            assert [entry['code'] for entry, error in failures] == ['gnrcore:adm']
            assert isinstance(failures[0][1], ModuleNotFoundError)
        finally:
            shutil.rmtree(custom_root)

    def test_check_package_imports_passes_on_a_loadable_closure(self):
        app = self._app('biz', checkdepcli=True, static_closure=True)
        assert app.check_package_imports() == []

    def test_checkdep_imports_fails_naming_the_package(self, monkeypatch, capsys):
        broken = self._package('brokenpkg', BROKEN_MAIN)
        self._app('sys', extra=broken, checkdepcli=True)
        assert self._checkdep(monkeypatch, '--imports') == 6
        out, err = capsys.readouterr()
        assert 'brokenpkg' in err
        assert 'All good!' not in out

    def test_checkdep_imports_passes(self, monkeypatch, capsys):
        self._app('biz', checkdepcli=True)
        assert self._checkdep(monkeypatch, '--imports') == 0
        assert 'All good!' in capsys.readouterr().out

    def test_checkdep_imports_fails_on_an_unresolved_closure(self, monkeypatch, capsys):
        dynamic = self._package('dynamicpkg', DYNAMIC_MAIN)
        self._app('sys', extra=dynamic, checkdepcli=True)
        assert self._checkdep(monkeypatch, '--imports') == 5
        assert 'dynamicpkg' in capsys.readouterr().err
