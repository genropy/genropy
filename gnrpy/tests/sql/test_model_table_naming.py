# -*- coding: utf-8 -*-
"""Model build behavior when a model module's filename does not match
the table name declared by its config_db (issue #106).

The table-mixin registry is keyed by the module filename, the model by
the name config_db declares.  When the two disagree the build used to
call pkgsrc.table(filename), which is get-or-create: it materialized an
empty phantom table named after the file and left the declared one
without its mixin.  The mismatch is an error in the application model,
so the build now refuses it instead of guessing what was meant.
"""

import pytest

from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.gnrsql_exceptions import GnrSqlException

from core.common import BaseGnrAppTest


class MatchingMixin:
    """Simulates model/real.py declaring pkg.table('real')"""
    def config_db(self, pkg):
        tbl = pkg.table('real', pkey='id', name_long='Real')
        tbl.column('id', 'L')

    def real_method(self):
        return 'real'


class MismatchedMixin:
    """Simulates model/foo.py declaring pkg.table('bar')"""
    def config_db(self, pkg):
        tbl = pkg.table('bar', pkey='id', name_long='Bar')
        tbl.column('id', 'L')


class EmptyMixin:
    """Simulates a model module declaring nothing"""
    pass


class MultiTableMixin:
    """Simulates model/alfa.py declaring both alfa and beta"""
    def config_db(self, pkg):
        for name in ('alfa', 'beta'):
            tbl = pkg.table(name, pkey='id', name_long=name)
            tbl.column('id', 'L')

    def alfa_method(self):
        return 'alfa'


class MultiTableUnnamedMixin:
    """Simulates model/gamma.py declaring delta and epsilon, but no gamma"""
    def config_db(self, pkg):
        for name in ('delta', 'epsilon'):
            tbl = pkg.table(name, pkey='id', name_long=name)
            tbl.column('id', 'L')


def build_model(**mixins):
    """Build a model for package `demo` out of the given filename/mixin pairs."""
    db = GnrSqlDb()
    pkgsrc = db.packageSrc('demo')
    pkgsrc.attributes.update(name_short='demo', name_long='demo', name_full='demo')
    for module_name, mixin in mixins.items():
        db.tableMixin('demo.%s' % module_name, mixin)
    db.startup()
    return db


class TestModelTableNaming:

    def test_matching_module_builds_and_binds(self):
        db = build_model(real=MatchingMixin())
        assert sorted(db.package('demo').tables.keys()) == ['real']
        assert hasattr(db.table('demo.real'), 'real_method')

    def test_mismatched_module_is_refused(self):
        with pytest.raises(GnrSqlException) as excinfo:
            build_model(foo=MismatchedMixin())
        message = str(excinfo.value)
        assert 'demo/foo' in message
        assert "no table named 'foo'" in message
        assert 'declared: bar' in message

    def test_module_declaring_nothing_is_refused(self):
        with pytest.raises(GnrSqlException) as excinfo:
            build_model(real=MatchingMixin(), whatever=EmptyMixin())
        message = str(excinfo.value)
        assert 'demo/whatever' in message
        assert 'declared: real' in message

    def test_module_declaring_nothing_in_an_empty_package(self):
        with pytest.raises(GnrSqlException) as excinfo:
            build_model(whatever=EmptyMixin())
        assert 'declared: none' in str(excinfo.value)

    def test_module_declaring_several_tables_is_accepted(self):
        db = build_model(alfa=MultiTableMixin())
        assert sorted(db.package('demo').tables.keys()) == ['alfa', 'beta']
        assert hasattr(db.table('demo.alfa'), 'alfa_method')

    def test_module_declaring_several_tables_but_not_its_own(self):
        with pytest.raises(GnrSqlException) as excinfo:
            build_model(gamma=MultiTableUnnamedMixin())
        message = str(excinfo.value)
        assert 'demo/gamma' in message
        assert 'declared: delta, epsilon' in message


class TestGnrDockerModel(BaseGnrAppTest):
    app_name = 'gnrdocker'

    def test_image_relation_has_a_real_target(self):
        tables = self.app.db.package('docker').tables
        assert 'image' in tables

        image = self.app.db.table('docker.image')
        assert image.model.pkey == 'id'
        assert image.model.column('name') is not None

        image_id = self.app.db.table('docker.container').model.column('image_id')
        assert image_id.relatedColumn().fullname == 'docker.image.id'
