"""Tests for the db.addMacro() infrastructure (issue #617).

Verifies that:
- GnrSqlDb.registerMacros() populates _macro_registry with base macros
- Postgres adapter adds its own macros via registerMacros()
- every entry is a dict with ``regex``, ``callback`` and ``contexts``
- MacroExpander copies the registry and expands one context at a time
- a callback receives the regex match and the running SqlQueryCompiler
- GnrSqlAppDb registers the app-level macros and broadcasts to packages
"""

import os
import re

import pytest

from gnr.sql.gnrsql.db import GnrSqlDb
from gnr.sql.gnrsqldata.compiler import SqlQueryCompiler
from gnr.sql.gnrsqlmacros import (IN_RANGEFINDER, PERIODFINDER,
                                  BAGEXPFINDER, BAGCOLSEXPFINDER,
                                  expand_in_range, expand_period,
                                  expand_bag, expand_bagcols)
from gnr.sql.adapters._gnrbasepostgresadapter import (TSQUERYFINDER,
                                                      VECQUERYFINDER,
                                                      expand_tsquery,
                                                      expand_vecquery)


def _double(match, compiler):
    return str(int(match.group(1)) * 2)


DOUBLEFINDER = re.compile(r'#DOUBLE\((\d+)\)')


# -- GnrSqlDb macro registration -------------------------------------------

class TestDbRegisterMacros:
    """GnrSqlDb.registerMacros() must populate _macro_registry."""

    def test_sqlite_db_has_base_macros(self):
        """A plain SQLite db must have IN_RANGE and PERIOD registered."""
        db = GnrSqlDb(implementation='sqlite')
        assert 'IN_RANGE' in db._macro_registry
        assert 'PERIOD' in db._macro_registry

    def test_sqlite_db_has_no_adapter_macros(self):
        """SQLite adapter has no macros — only the 2 base ones."""
        db = GnrSqlDb(implementation='sqlite')
        assert 'TSQUERY' not in db._macro_registry
        assert 'VECQUERY' not in db._macro_registry

    def test_base_macros_have_regex(self):
        """Each registered macro must have a compiled regex, not None."""
        db = GnrSqlDb(implementation='sqlite')
        for name, macro in db._macro_registry.items():
            assert macro['regex'] is not None, f'Macro {name} has no regex'
            assert hasattr(macro['regex'], 'pattern'), f'Macro {name} regex is not compiled'

    def test_base_macros_have_callback(self):
        """A macro with no callback would never expand: none is allowed."""
        db = GnrSqlDb(implementation='sqlite')
        for name, macro in db._macro_registry.items():
            assert macro['callback'] is not None, f'Macro {name} has no callback'

    def test_base_macros_contexts(self):
        """IN_RANGE and PERIOD declare the contexts the compiler expands."""
        db = GnrSqlDb(implementation='sqlite')
        assert db._macro_registry['IN_RANGE']['contexts'] == 'where,formula_post,join_cnd'
        assert db._macro_registry['PERIOD']['contexts'] == 'where'

    def test_base_macros_come_from_gnrsqlmacros(self):
        """The base macros are the SQL_MACROS entries of gnrsqlmacros."""
        db = GnrSqlDb(implementation='sqlite')
        assert db._macro_registry['IN_RANGE']['regex'] is IN_RANGEFINDER
        assert db._macro_registry['IN_RANGE']['callback'] is expand_in_range
        assert db._macro_registry['PERIOD']['regex'] is PERIODFINDER
        assert db._macro_registry['PERIOD']['callback'] is expand_period

    def test_in_range_regex_matches(self):
        """IN_RANGE regex must match the macro syntax."""
        db = GnrSqlDb(implementation='sqlite')
        assert db._macro_registry['IN_RANGE']['regex'].search('#IN_RANGE($value, $low, $high)')

    def test_period_regex_matches(self):
        """PERIOD regex must match the macro syntax."""
        db = GnrSqlDb(implementation='sqlite')
        assert db._macro_registry['PERIOD']['regex'].search('#PERIOD($date_field, period_param)')

    def test_addMacro_adds_to_registry(self):
        """addMacro must add to _macro_registry."""
        db = GnrSqlDb(implementation='sqlite')
        n_before = len(db._macro_registry)
        db.addMacro('DOUBLE', DOUBLEFINDER, _double)
        assert len(db._macro_registry) == n_before + 1
        assert db._macro_registry['DOUBLE']['regex'] is DOUBLEFINDER
        assert db._macro_registry['DOUBLE']['callback'] is _double

    def test_addMacro_contexts_default_is_none(self):
        """Without contexts the macro is valid in every context."""
        db = GnrSqlDb(implementation='sqlite')
        db.addMacro('DOUBLE', DOUBLEFINDER, _double)
        assert db._macro_registry['DOUBLE']['contexts'] is None

    def test_addMacro_stores_contexts(self):
        """The contexts string is stored as given."""
        db = GnrSqlDb(implementation='sqlite')
        db.addMacro('DOUBLE', DOUBLEFINDER, _double, contexts='where,columns')
        assert db._macro_registry['DOUBLE']['contexts'] == 'where,columns'

    def test_addMacro_without_callback_raises(self):
        """A macro without callback would never expand: it is refused."""
        db = GnrSqlDb(implementation='sqlite')
        with pytest.raises(ValueError):
            db.addMacro('DOUBLE', DOUBLEFINDER, None)

    def test_addMacro_duplicate_raises(self):
        """addMacro must raise on duplicate name without replace=True."""
        db = GnrSqlDb(implementation='sqlite')
        db.addMacro('DOUBLE', DOUBLEFINDER, _double)
        with pytest.raises(KeyError):
            db.addMacro('DOUBLE', DOUBLEFINDER, _double)

    def test_addMacro_replace(self):
        """addMacro with replace=True must overwrite."""
        db = GnrSqlDb(implementation='sqlite')
        other = re.compile(r'#DOUBLE2\(\)')
        db.addMacro('DOUBLE', DOUBLEFINDER, _double)
        db.addMacro('DOUBLE', other, _double, replace=True)
        assert db._macro_registry['DOUBLE']['regex'] is other


# -- Postgres adapter macro registration -----------------------------------

class TestPostgresAdapterRegisterMacros:
    """Postgres adapter must register its 5 macros."""

    @pytest.fixture()
    def pg_db(self):
        try:
            db = GnrSqlDb(implementation='postgres')
        except Exception:
            pytest.skip('Postgres adapter not available')
        return db

    def test_postgres_has_adapter_macros(self, pg_db):
        for expected in ('TSQUERY', 'TSRANK', 'TSHEADLINE', 'VECQUERY', 'VECRANK'):
            assert expected in pg_db._macro_registry, f'{expected} not registered by Postgres adapter'

    def test_postgres_has_base_macros_too(self, pg_db):
        assert 'IN_RANGE' in pg_db._macro_registry
        assert 'PERIOD' in pg_db._macro_registry

    def test_postgres_macros_have_regex(self, pg_db):
        for name, macro in pg_db._macro_registry.items():
            assert macro['regex'] is not None, f'Macro {name} has no regex'
            assert hasattr(macro['regex'], 'pattern'), f'Macro {name} regex is not compiled'

    def test_postgres_macros_have_callback(self, pg_db):
        for name, macro in pg_db._macro_registry.items():
            assert macro['callback'] is not None, f'Macro {name} has no callback'

    def test_postgres_macros_contexts(self, pg_db):
        expected = {
            'TSQUERY': 'where',
            'TSRANK': 'formula_pre,columns_final,order_by',
            'TSHEADLINE': 'formula_pre,columns_final',
            'VECQUERY': 'where',
            'VECRANK': 'formula_pre,columns_final,order_by',
        }
        for name, contexts in expected.items():
            assert pg_db._macro_registry[name]['contexts'] == contexts

    def test_postgres_macros_come_from_the_adapter_module(self, pg_db):
        """The adapter macros are the POSTGRES_MACROS entries."""
        assert pg_db._macro_registry['TSQUERY']['regex'] is TSQUERYFINDER
        assert pg_db._macro_registry['TSQUERY']['callback'] is expand_tsquery
        assert pg_db._macro_registry['VECQUERY']['regex'] is VECQUERYFINDER
        assert pg_db._macro_registry['VECQUERY']['callback'] is expand_vecquery

    def test_postgres_tsquery_regex_matches(self, pg_db):
        assert pg_db._macro_registry['TSQUERY']['regex'].search('#TSQUERY($ts_vec, :search_text)')

    def test_postgres_vecquery_regex_matches(self, pg_db):
        assert pg_db._macro_registry['VECQUERY']['regex'].search('#VECQUERY($embedding, :target)')


# -- Real application database ---------------------------------------------

@pytest.fixture(scope='module')
def app_db(tmp_path_factory):
    """Create a real GnrApp('test_invoice') with SQLite."""
    from core.common import BaseGnrTest
    from gnr.app.gnrapp import GnrApp
    BaseGnrTest.setup_class()
    try:
        tmpdir = tmp_path_factory.mktemp('macro_reg')
        app = GnrApp('test_invoice', db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(str(tmpdir), 'testing'),
        ))
        yield app.db
    finally:
        BaseGnrTest.teardown_class()


def _expander(db):
    """A MacroExpander built the way the compiler builds it."""
    compiler = SqlQueryCompiler(db.table('invc.product').model, sqlparams={})
    return compiler.macro_expander


# -- MacroExpander ----------------------------------------------------------

class TestMacroExpander:
    """The expander copies the registry and filters the macros by context."""

    @pytest.fixture()
    def where_only_db(self, app_db):
        app_db.addMacro('DOUBLE', DOUBLEFINDER, _double, contexts='where')
        yield app_db
        del app_db._macro_registry['DOUBLE']

    @pytest.fixture()
    def every_context_db(self, app_db):
        app_db.addMacro('DOUBLE', DOUBLEFINDER, _double)
        yield app_db
        del app_db._macro_registry['DOUBLE']

    def test_copies_the_registry_in_order(self, app_db):
        expander = _expander(app_db)
        assert list(expander._registered_macros) == list(app_db._macro_registry)

    def test_replace_context_expands_in_the_declared_context(self, where_only_db):
        expander = _expander(where_only_db)
        assert expander.replace_context('SELECT #DOUBLE(21)', 'where') == 'SELECT 42'

    def test_replace_context_skips_the_other_contexts(self, where_only_db):
        expander = _expander(where_only_db)
        text = 'SELECT #DOUBLE(21)'
        assert expander.replace_context(text, 'order_by') == text

    @pytest.mark.parametrize('context', ['where', 'columns', 'columns_final',
                                         'order_by', 'formula_pre',
                                         'formula_post', 'join_cnd'])
    def test_contexts_none_expands_everywhere(self, every_context_db, context):
        expander = _expander(every_context_db)
        assert expander.replace_context('#DOUBLE(21)', context) == '42'

    def test_callback_receives_the_query_compiler(self, app_db):
        """The second argument of a callback is the running compiler."""
        seen = []

        def _capture(match, compiler):
            seen.append(compiler)
            return '42'

        app_db.addMacro('DOUBLE', DOUBLEFINDER, _capture, contexts='where')
        try:
            compiler = SqlQueryCompiler(app_db.table('invc.product').model,
                                        sqlparams={})
            compiler.macro_expander.replace_context('#DOUBLE(21)', 'where')
        finally:
            del app_db._macro_registry['DOUBLE']
        assert isinstance(seen[0], SqlQueryCompiler)
        assert seen[0] is compiler


# -- App-level macro registration ------------------------------------------

class TestAppLevelMacroRegistration:
    """GnrSqlAppDb.registerMacros() adds the macros the compiler needs."""

    def test_app_level_macros_registered(self, app_db):
        """App-level macros (BAG, BAGCOLS) must be in registry."""
        for name in ('BAG', 'BAGCOLS'):
            assert name in app_db._macro_registry, f'{name} not registered'

    def test_app_level_macros_have_regex(self, app_db):
        """App-level macros must have a compiled regex."""
        for name in ('BAG', 'BAGCOLS'):
            regex = app_db._macro_registry[name]['regex']
            assert regex is not None, f'{name} has no regex'
            assert hasattr(regex, 'pattern'), f'{name} regex is not compiled'

    def test_app_level_macros_come_from_gnrsqlmacros(self, app_db):
        """The app-level macros are the APP_MACROS entries of gnrsqlmacros."""
        assert app_db._macro_registry['BAG']['regex'] is BAGEXPFINDER
        assert app_db._macro_registry['BAG']['callback'] is expand_bag
        assert app_db._macro_registry['BAGCOLS']['regex'] is BAGCOLSEXPFINDER
        assert app_db._macro_registry['BAGCOLS']['callback'] is expand_bagcols

    def test_app_level_macros_contexts(self, app_db):
        """BAG and BAGCOLS are expanded in the select list only."""
        for name in ('BAG', 'BAGCOLS'):
            assert app_db._macro_registry[name]['contexts'] == 'columns'

    def test_closure_macros_are_not_registered(self, app_db):
        """ENV, PREF and THIS are expanded by closures of getFieldAlias."""
        for name in ('ENV', 'PREF', 'THIS'):
            assert name not in app_db._macro_registry

    def test_base_and_adapter_macros_come_first(self, app_db):
        """Registration order drives expansion order inside a context."""
        names = list(app_db._macro_registry)
        assert names[:2] == ['IN_RANGE', 'PERIOD']
        assert names.index('BAG') > names.index('PERIOD')
