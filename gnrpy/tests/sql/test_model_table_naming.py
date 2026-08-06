# -*- coding: utf-8 -*-
"""Model build behavior when a model module's filename does not match
the table name declared by its config_db (issue #106).

The table-mixin registry is keyed by module filename: before the fix,
a module model/foo.py declaring pkg.table('bar') produced an empty
phantom table 'foo' and left the real table 'bar' without its mixin;
an empty module produced an empty table named after the file.
"""

from gnr.sql.gnrsql import GnrSqlDb

from .common import BaseGnrSqlTest


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
        tbl.column('notes', name_long='Notes')

    def bar_method(self):
        return 'bar'


class EmptyMixin:
    """Simulates an empty model module"""
    pass


class TestModelTableNaming(BaseGnrSqlTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = GnrSqlDb()
        pkg = cls.db.packageSrc('demo')
        pkg.attributes.update(name_short='demo', name_long='demo', name_full='demo')
        cls.db.tableMixin('demo.real', MatchingMixin())
        cls.db.tableMixin('demo.foo', MismatchedMixin())
        cls.db.tableMixin('demo.whatever', EmptyMixin())
        cls.db.startup()

    def test_matching_module_unchanged(self):
        tables = self.db.package('demo').tables
        assert 'real' in tables
        assert hasattr(self.db.table('demo.real'), 'real_method')

    def test_no_phantom_table_on_name_mismatch(self):
        tables = sorted(self.db.package('demo').tables.keys())
        assert 'foo' not in tables
        assert 'bar' in tables

    def test_mixin_rebound_to_declared_table(self):
        bar = self.db.table('demo.bar')
        assert hasattr(bar, 'bar_method')
        assert bar.model.column('notes') is not None

    def test_empty_module_creates_no_table(self):
        tables = sorted(self.db.package('demo').tables.keys())
        assert 'whatever' not in tables
        assert tables == ['bar', 'real']
