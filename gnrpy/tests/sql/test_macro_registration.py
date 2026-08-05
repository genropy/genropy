"""Tests for the db.addMacro() infrastructure (issue #617, Phase 1).

Verifies that:
- GnrSqlDb.registerMacros() populates _macro_registry with base macros
- Postgres adapter adds its own macros via registerMacros()
- MacroExpander.register() and replace() work correctly
- The compiler copies registered macros into the expander
- Package-level macros are registered via pkgBroadcast
"""

import os
import re

import pytest

from gnr.sql.gnrsql.db import GnrSqlDb
from gnr.sql.adapters._gnrbaseadapter import MacroExpander


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
        for name, (regex, cb) in db._macro_registry.items():
            assert regex is not None, f'Macro {name} has no regex'
            assert hasattr(regex, 'pattern'), f'Macro {name} regex is not compiled'

    def test_in_range_regex_matches(self):
        """IN_RANGE regex must match the macro syntax."""
        db = GnrSqlDb(implementation='sqlite')
        regex, cb = db._macro_registry['IN_RANGE']
        assert regex.search('#IN_RANGE($value, $low, $high)')

    def test_period_regex_matches(self):
        """PERIOD regex must match the macro syntax."""
        db = GnrSqlDb(implementation='sqlite')
        regex, cb = db._macro_registry['PERIOD']
        assert regex.search('#PERIOD($date_field, period_param)')

    def test_addMacro_adds_to_registry(self):
        """addMacro must add to _macro_registry."""
        db = GnrSqlDb(implementation='sqlite')
        n_before = len(db._macro_registry)
        dummy_re = re.compile(r'#DUMMY\(\)')
        db.addMacro('DUMMY', dummy_re, None)
        assert len(db._macro_registry) == n_before + 1
        assert 'DUMMY' in db._macro_registry
        regex, cb = db._macro_registry['DUMMY']
        assert regex is dummy_re

    def test_addMacro_duplicate_raises(self):
        """addMacro must raise on duplicate name without replace=True."""
        db = GnrSqlDb(implementation='sqlite')
        dummy_re = re.compile(r'#DUMMY\(\)')
        db.addMacro('DUMMY', dummy_re, None)
        with pytest.raises(KeyError):
            db.addMacro('DUMMY', dummy_re, None)

    def test_addMacro_replace(self):
        """addMacro with replace=True must overwrite."""
        db = GnrSqlDb(implementation='sqlite')
        dummy_re1 = re.compile(r'#DUMMY1\(\)')
        dummy_re2 = re.compile(r'#DUMMY2\(\)')
        db.addMacro('DUMMY', dummy_re1, None)
        db.addMacro('DUMMY', dummy_re2, None, replace=True)
        regex, cb = db._macro_registry['DUMMY']
        assert regex is dummy_re2


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
        for name, (regex, cb) in pg_db._macro_registry.items():
            assert regex is not None, f'Macro {name} has no regex'
            assert hasattr(regex, 'pattern'), f'Macro {name} regex is not compiled'

    def test_postgres_tsquery_regex_matches(self, pg_db):
        regex, cb = pg_db._macro_registry['TSQUERY']
        assert regex.search('#TSQUERY($ts_vec, :search_text)')

    def test_postgres_vecquery_regex_matches(self, pg_db):
        regex, cb = pg_db._macro_registry['VECQUERY']
        assert regex.search('#VECQUERY($embedding, :target)')


# -- MacroExpander unit tests ----------------------------------------------

class TestMacroExpanderRegister:
    """MacroExpander.register() and replace() with registered macros."""

    def test_register_and_replace(self):
        """A registered macro must be expanded by replace()."""
        expander = MacroExpander(querycompiler=None)
        regex = re.compile(r'#DOUBLE\((\d+)\)')

        def expand_double(m, exp):
            return str(int(m.group(1)) * 2)

        expander.register('DOUBLE', regex, expand_double)
        result = expander.replace('SELECT #DOUBLE(21)', 'DOUBLE')
        assert result == 'SELECT 42'

    def test_replace_unknown_macro_is_noop(self):
        """Requesting an unregistered macro must leave text unchanged."""
        expander = MacroExpander(querycompiler=None)
        text = 'SELECT #UNKNOWN(x)'
        assert expander.replace(text, 'UNKNOWN') == text

    def test_registered_overrides_class_level(self):
        """Instance-registered macros take precedence over class-level."""

        class CustomExpander(MacroExpander):
            macros = {'HELLO': re.compile(r'#HELLO')}

            def _expand_HELLO(self, m):
                return 'class_level'

        expander = CustomExpander(querycompiler=None)
        # Class-level works
        assert expander.replace('#HELLO', 'HELLO') == 'class_level'
        # Now register override
        expander.register('HELLO', re.compile(r'#HELLO'),
                          lambda m, exp: 'instance_level')
        assert expander.replace('#HELLO', 'HELLO') == 'instance_level'

    def test_context_available_in_callback(self):
        """The expander.context dict must be accessible from callbacks."""
        expander = MacroExpander(querycompiler=None)
        expander.context['multiplier'] = 3
        regex = re.compile(r'#MULT\((\d+)\)')

        def expand_mult(m, exp):
            return str(int(m.group(1)) * exp.context['multiplier'])

        expander.register('MULT', regex, expand_mult)
        assert expander.replace('#MULT(7)', 'MULT') == '21'

    def test_multiple_macros_in_one_replace(self):
        """replace() with comma-separated names must expand all."""
        expander = MacroExpander(querycompiler=None)
        expander.register('A', re.compile(r'#A'), lambda m, e: '1')
        expander.register('B', re.compile(r'#B'), lambda m, e: '2')
        result = expander.replace('#A + #B', 'A,B')
        assert result == '1 + 2'


# -- Package-level macro registration via GnrApp ---------------------------

class TestPackageMacroRegistration:
    """Package registerMacros() via pkgBroadcast with real GnrApp."""

    @pytest.fixture(scope='class')
    def app_db(self, tmp_path_factory):
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

    def test_package_macro_registered(self, app_db):
        """invc package must register #UPPERCASE via registerMacros."""
        assert 'UPPERCASE' in app_db._macro_registry

    def test_package_macro_has_regex(self, app_db):
        """Package macro must have a compiled regex."""
        regex, cb = app_db._macro_registry['UPPERCASE']
        assert regex is not None
        assert hasattr(regex, 'pattern')
        assert regex.search('#UPPERCASE($name)')

    def test_package_macro_has_callback(self, app_db):
        """Package macro must have a callback."""
        regex, cb = app_db._macro_registry['UPPERCASE']
        assert cb is not None

    def test_package_macro_callback_expands(self, app_db):
        """The #UPPERCASE callback must produce UPPER(...)."""
        regex, cb = app_db._macro_registry['UPPERCASE']
        m = regex.search('#UPPERCASE($name)')
        result = cb(m, None)
        assert result == 'UPPER($name)'

    def test_app_level_macros_registered(self, app_db):
        """App-level macros (PREF, THIS, BAG, BAGCOLS) must be in registry."""
        for name in ('PREF', 'THIS', 'BAG', 'BAGCOLS'):
            assert name in app_db._macro_registry, f'{name} not registered'

    def test_app_level_macros_have_regex(self, app_db):
        """App-level macros must have a compiled regex."""
        for name in ('PREF', 'THIS', 'BAG', 'BAGCOLS'):
            regex, cb = app_db._macro_registry[name]
            assert regex is not None, f'{name} has no regex'
            assert hasattr(regex, 'pattern'), f'{name} regex is not compiled'

    def test_app_level_macros_callback_is_none(self, app_db):
        """App-level macros have None callback (registration only)."""
        for name in ('PREF', 'THIS', 'BAG', 'BAGCOLS'):
            regex, cb = app_db._macro_registry[name]
            assert cb is None, f'{name} should have None callback'

    def test_package_macro_in_expander(self, app_db):
        """Package macros must be copied into the MacroExpander."""
        expander = MacroExpander(querycompiler=None)
        for name, (regex, callback) in app_db._macro_registry.items():
            expander.register(name, regex, callback)
        result = expander.replace('SELECT #UPPERCASE($name)', 'UPPERCASE')
        assert result == 'SELECT UPPER($name)'
