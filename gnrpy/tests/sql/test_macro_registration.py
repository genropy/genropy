"""Tests for the db.addMacro() infrastructure (issue #617, Phase 1).

Verifies that:
- GnrSqlDb.registerMacros() populates _custom_macros with base macros
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
    """GnrSqlDb.registerMacros() must populate _custom_macros."""

    def test_sqlite_db_has_base_macros(self):
        """A plain SQLite db must have IN_RANGE and PERIOD registered."""
        db = GnrSqlDb(implementation='sqlite')
        names = [name for name, regex, cb in db._custom_macros]
        assert 'IN_RANGE' in names
        assert 'PERIOD' in names

    def test_sqlite_db_has_no_adapter_macros(self):
        """SQLite adapter has no macros — only the 2 base ones."""
        db = GnrSqlDb(implementation='sqlite')
        names = [name for name, regex, cb in db._custom_macros]
        assert 'TSQUERY' not in names
        assert 'VECQUERY' not in names

    def test_base_macros_have_regex(self):
        """Each registered macro must have a compiled regex, not None."""
        db = GnrSqlDb(implementation='sqlite')
        for name, regex, cb in db._custom_macros:
            assert regex is not None, f'Macro {name} has no regex'
            assert hasattr(regex, 'pattern'), f'Macro {name} regex is not compiled'

    def test_in_range_regex_matches(self):
        """IN_RANGE regex must match the macro syntax."""
        db = GnrSqlDb(implementation='sqlite')
        macros = {name: regex for name, regex, cb in db._custom_macros}
        assert macros['IN_RANGE'].search('#IN_RANGE($value, $low, $high)')

    def test_period_regex_matches(self):
        """PERIOD regex must match the macro syntax."""
        db = GnrSqlDb(implementation='sqlite')
        macros = {name: regex for name, regex, cb in db._custom_macros}
        assert macros['PERIOD'].search('#PERIOD($date_field, period_param)')

    def test_addMacro_appends(self):
        """addMacro must append to _custom_macros."""
        db = GnrSqlDb(implementation='sqlite')
        n_before = len(db._custom_macros)
        dummy_re = re.compile(r'#DUMMY\(\)')
        db.addMacro('DUMMY', dummy_re, None)
        assert len(db._custom_macros) == n_before + 1
        last = db._custom_macros[-1]
        assert last[0] == 'DUMMY'
        assert last[1] is dummy_re


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
        names = [name for name, regex, cb in pg_db._custom_macros]
        for expected in ('TSQUERY', 'TSRANK', 'TSHEADLINE', 'VECQUERY', 'VECRANK'):
            assert expected in names, f'{expected} not registered by Postgres adapter'

    def test_postgres_has_base_macros_too(self, pg_db):
        names = [name for name, regex, cb in pg_db._custom_macros]
        assert 'IN_RANGE' in names
        assert 'PERIOD' in names

    def test_postgres_macros_have_regex(self, pg_db):
        for name, regex, cb in pg_db._custom_macros:
            assert regex is not None, f'Macro {name} has no regex'
            assert hasattr(regex, 'pattern'), f'Macro {name} regex is not compiled'

    def test_postgres_tsquery_regex_matches(self, pg_db):
        macros = {name: regex for name, regex, cb in pg_db._custom_macros}
        assert macros['TSQUERY'].search('#TSQUERY($ts_vec, :search_text)')

    def test_postgres_vecquery_regex_matches(self, pg_db):
        macros = {name: regex for name, regex, cb in pg_db._custom_macros}
        assert macros['VECQUERY'].search('#VECQUERY($embedding, :target)')

    def test_base_macros_come_first(self, pg_db):
        """Base macros (IN_RANGE, PERIOD) must be registered before adapter ones."""
        names = [name for name, regex, cb in pg_db._custom_macros]
        idx_in_range = names.index('IN_RANGE')
        idx_tsquery = names.index('TSQUERY')
        assert idx_in_range < idx_tsquery


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
        names = [name for name, regex, cb in app_db._custom_macros]
        assert 'UPPERCASE' in names

    def test_package_macro_has_regex(self, app_db):
        """Package macro must have a compiled regex."""
        macros = {name: (regex, cb) for name, regex, cb in app_db._custom_macros}
        regex, cb = macros['UPPERCASE']
        assert regex is not None
        assert hasattr(regex, 'pattern')
        assert regex.search('#UPPERCASE($name)')

    def test_package_macro_has_callback(self, app_db):
        """Package macro must have a callback."""
        macros = {name: (regex, cb) for name, regex, cb in app_db._custom_macros}
        regex, cb = macros['UPPERCASE']
        assert cb is not None

    def test_package_macro_callback_expands(self, app_db):
        """The #UPPERCASE callback must produce UPPER(...)."""
        macros = {name: (regex, cb) for name, regex, cb in app_db._custom_macros}
        regex, cb = macros['UPPERCASE']
        m = regex.search('#UPPERCASE($name)')
        result = cb(m, None)
        assert result == 'UPPER($name)'

    def test_package_macro_after_base_and_adapter(self, app_db):
        """Package macros must come after base macros."""
        names = [name for name, regex, cb in app_db._custom_macros]
        idx_in_range = names.index('IN_RANGE')
        idx_uppercase = names.index('UPPERCASE')
        assert idx_in_range < idx_uppercase

    def test_package_macro_in_expander(self, app_db):
        """Package macros must be copied into the MacroExpander."""
        expander = MacroExpander(querycompiler=None)
        for name, regex, callback in app_db._custom_macros:
            expander.register(name, regex, callback)
        result = expander.replace('SELECT #UPPERCASE($name)', 'UPPERCASE')
        assert result == 'SELECT UPPER($name)'
