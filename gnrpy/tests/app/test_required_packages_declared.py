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
import tempfile

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
