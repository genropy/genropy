"""Tests for gnr.app.api_engine.ApiEngine.

Uses the shared test_invoice fixture from this directory's conftest:
the engine is built from ``db_sqlite.application`` (a GnrApp loaded on
a temporary SQLite database with CSV-imported data).
"""

import json

import pytest

from core.common import BaseGnrTest

from gnr.app.api_engine import ApiEngine, ApiEngineError
from gnr.app.api_engine.core import _check_sql_fragment


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestConstruction:

    def test_init_from_app(self, db_sqlite):
        app = db_sqlite.application
        engine = ApiEngine(app)
        assert engine.app is app
        assert engine.db is db_sqlite
        assert engine.max_rows is None

    def test_init_with_max_rows(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application, max_rows=42)
        assert engine.max_rows == 42

    def test_init_rejects_statement_timeout_ms(self, db_sqlite):
        with pytest.raises(TypeError):
            ApiEngine(db_sqlite.application, statement_timeout_ms=100)


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------

class TestEnumeration:

    def test_package_names(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        names = engine.package_names()
        assert 'invc' in names
        assert 'adm' in names
        assert names == sorted(names)

    def test_table_names_all(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        names = engine.table_names()
        assert len(names) > 0
        assert all('.' in n for n in names)
        assert names == sorted(names)
        assert 'invc.invoice' in names

    def test_table_names_by_package(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        names = engine.table_names('invc')
        assert all(n.startswith('invc.') for n in names)
        assert 'invc.invoice' in names
        assert 'invc.customer' in names

    def test_table_names_unknown_package_raises(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        with pytest.raises(ValueError, match='Unknown package'):
            engine.table_names('nonexistent_pkg')

    def test_table_names_fullname_raises(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        with pytest.raises(ValueError, match='table fullname'):
            engine.table_names('invc.invoice')


# ---------------------------------------------------------------------------
# table_columns
# ---------------------------------------------------------------------------

class TestTableColumns:

    def test_single_table_wrapped(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        out = engine.table_columns('invc.invoice')
        assert list(out.keys()) == ['invc.invoice']

    def test_real_column_typing(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        cols = engine.table_columns('invc.invoice')['invc.invoice']
        # id: pkey
        assert cols['id']['kind'] == 'real'
        assert cols['id']['pkey'] is True
        assert cols['id']['nullable'] is False
        assert cols['id']['python_type'] == 'str'
        assert cols['id']['openapi_type'] == 'string'
        # total: Decimal
        assert cols['total']['kind'] == 'real'
        assert cols['total']['python_type'] == 'Decimal'
        assert cols['total']['openapi_type'] == 'string'
        assert cols['total']['openapi_format'] == 'decimal'

    def test_fk_detection_on_real_column(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        cols = engine.table_columns('invc.invoice')['invc.invoice']
        assert cols['customer_id']['fkey'] == {
            'target_table': 'invc.customer',
            'target_column': 'id',
        }

    def test_system_columns_flagged(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        cols = engine.table_columns('invc.invoice')['invc.invoice']
        assert cols['__ins_ts']['system'] is True
        assert cols['id']['system'] is False

    def test_pycolumn_excluded(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        cols = engine.table_columns('invc.invoice')['invc.invoice']
        for name, info in cols.items():
            assert info['kind'] != 'pycolumn', \
                'pycolumn %r should be excluded' % name

    def test_package_target(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        out = engine.table_columns('invc')
        assert 'invc.invoice' in out
        assert 'invc.customer' in out
        # adm.user should not be present when filtering by package
        assert not any(k.startswith('adm.') for k in out)

    def test_list_target(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        out = engine.table_columns(['invc.invoice', 'invc.customer'])
        assert set(out.keys()) == {'invc.invoice', 'invc.customer'}

    def test_unknown_table_raises(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        with pytest.raises(ValueError, match='Unknown table'):
            engine.table_columns('invc.nonexistent')

    def test_non_string_dtype_raises(self, db_sqlite):
        """A model with a non-string dtype (e.g. dtype=True from a typo)
        must raise ApiEngineError rather than silently fall back."""
        engine = ApiEngine(db_sqlite.application)
        col = engine.db.table('invc.customer').columns['account_name']
        prev = col.attributes.get('dtype')
        try:
            col.attributes['dtype'] = True
            with pytest.raises(ApiEngineError, match='Invalid dtype True'):
                engine.table_columns('invc.customer')
        finally:
            if prev is None:
                col.attributes.pop('dtype', None)
            else:
                col.attributes['dtype'] = prev

    def test_unknown_dtype_raises(self, db_sqlite):
        """A dtype that is a string but not in the known mapping must
        raise ApiEngineError listing the accepted codes."""
        engine = ApiEngine(db_sqlite.application)
        col = engine.db.table('invc.customer').columns['account_name']
        prev = col.attributes.get('dtype')
        try:
            col.attributes['dtype'] = 'ZZZ'
            with pytest.raises(ApiEngineError, match="Unknown dtype 'ZZZ'"):
                engine.table_columns('invc.customer')
        finally:
            if prev is None:
                col.attributes.pop('dtype', None)
            else:
                col.attributes['dtype'] = prev

    def test_fkey_orphan_omitted(self, db_sqlite):
        """A FK whose target column resolves but whose .table is None
        must not crash: the engine silently omits the fkey entry."""
        engine = ApiEngine(db_sqlite.application)
        col = engine.db.table('invc.invoice').columns['customer_id']
        orig = col.relatedColumn

        class _OrphanRelated:
            table = None
            name = 'irrelevant'

        col.relatedColumn = lambda: _OrphanRelated()
        try:
            cols = engine.table_columns('invc.invoice')
            assert 'fkey' not in cols['invc.invoice']['customer_id']
        finally:
            col.relatedColumn = orig

    def test_fkey_target_package_not_loaded(self, db_sqlite):
        """The real-world case: when the FK target table belongs to a
        package not loaded in the instance, model.table() returns None
        and model.column() raises AttributeError on the missing .column
        attribute. The engine must catch it and omit the fkey entry."""
        engine = ApiEngine(db_sqlite.application)
        col = engine.db.table('invc.invoice').columns['customer_id']
        orig = col.relatedColumn

        def _raise_attr_error():
            raise AttributeError(
                "'NoneType' object has no attribute 'column'")

        col.relatedColumn = _raise_attr_error
        try:
            cols = engine.table_columns('invc.invoice')
            assert 'fkey' not in cols['invc.invoice']['customer_id']
        finally:
            col.relatedColumn = orig


# ---------------------------------------------------------------------------
# table_schema
# ---------------------------------------------------------------------------

class TestTableSchema:

    def test_single_wrapped(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        out = engine.table_schema('invc.invoice')
        assert list(out.keys()) == ['invc.invoice']
        assert isinstance(out['invc.invoice'], dict)

    def test_relations_only(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        out = engine.table_schema(
            'invc.invoice', relations_only=True)['invc.invoice']
        for name, entry in out.items():
            assert entry['kind'] == 'relation', \
                '%s has kind %s, expected relation' % (name, entry['kind'])

    def test_depth_zero_no_children(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        out = engine.table_schema(
            'invc.invoice', depth=0)['invc.invoice']
        # at least one relation entry must exist and must not have children
        rel_entries = [v for v in out.values() if v['kind'] == 'relation']
        assert rel_entries
        for r in rel_entries:
            assert 'children' not in r

    def test_package_target(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        out = engine.table_schema('invc', depth=0)
        assert 'invc.invoice' in out
        assert 'invc.customer' in out


# ---------------------------------------------------------------------------
# openapi_schema
# ---------------------------------------------------------------------------

class TestOpenapiSchema:

    def test_empty_when_nothing_opted_in(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        assert engine.openapi_schema() == {}

    def test_unexposed_table_raises(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        with pytest.raises(ValueError, match='not exposed via openapi'):
            engine.openapi_schema('invc.invoice')

    def test_opt_in_table(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        pkg = engine.db.packages['invc']
        tbl = engine.db.table('invc.invoice')
        prev_pkg = pkg.attributes.get('openapi')
        prev_tbl = tbl.attributes.get('openapi')
        try:
            pkg.attributes['openapi'] = True
            tbl.attributes['openapi'] = True
            out = engine.openapi_schema('invc.invoice')
            assert 'invc.invoice' in out
            schema = out['invc.invoice']
            assert schema['type'] == 'object'
            assert schema['title'] == 'invc.invoice'
            # The pkey should be present and marked readOnly
            assert 'id' in schema['properties']
            assert schema['properties']['id'].get('readOnly') is True
        finally:
            self._restore(pkg.attributes, 'openapi', prev_pkg)
            self._restore(tbl.attributes, 'openapi', prev_tbl)

    def test_readonly_false_excludes_pkey_and_system(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        pkg = engine.db.packages['invc']
        tbl = engine.db.table('invc.invoice')
        prev_pkg = pkg.attributes.get('openapi')
        prev_tbl = tbl.attributes.get('openapi')
        try:
            pkg.attributes['openapi'] = True
            tbl.attributes['openapi'] = True
            out = engine.openapi_schema(
                'invc.invoice', readonly=False)
            props = out['invc.invoice']['properties']
            assert 'id' not in props
            assert '__ins_ts' not in props
            assert '__del_ts' not in props
            # writable real columns are present
            assert 'customer_id' in props
            assert 'total' in props
        finally:
            self._restore(pkg.attributes, 'openapi', prev_pkg)
            self._restore(tbl.attributes, 'openapi', prev_tbl)

    def test_column_readonly_setting(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        pkg = engine.db.packages['invc']
        tbl = engine.db.table('invc.invoice')
        col = tbl.columns['total']
        prev_pkg = pkg.attributes.get('openapi')
        prev_tbl = tbl.attributes.get('openapi')
        prev_col = col.attributes.get('openapi')
        try:
            pkg.attributes['openapi'] = True
            tbl.attributes['openapi'] = True
            col.attributes['openapi'] = 'R'
            # readonly=True: column appears, marked readOnly
            out = engine.openapi_schema('invc.invoice', readonly=True)
            assert out['invc.invoice']['properties']['total'].get(
                'readOnly') is True
            # readonly=False: column excluded
            out = engine.openapi_schema('invc.invoice', readonly=False)
            assert 'total' not in out['invc.invoice']['properties']
        finally:
            self._restore(pkg.attributes, 'openapi', prev_pkg)
            self._restore(tbl.attributes, 'openapi', prev_tbl)
            self._restore(col.attributes, 'openapi', prev_col)

    def test_column_excluded(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        pkg = engine.db.packages['invc']
        tbl = engine.db.table('invc.invoice')
        col = tbl.columns['inv_number']
        prev_pkg = pkg.attributes.get('openapi')
        prev_tbl = tbl.attributes.get('openapi')
        prev_col = col.attributes.get('openapi')
        try:
            pkg.attributes['openapi'] = True
            tbl.attributes['openapi'] = True
            col.attributes['openapi'] = False
            out = engine.openapi_schema('invc.invoice')
            assert 'inv_number' not in out['invc.invoice']['properties']
        finally:
            self._restore(pkg.attributes, 'openapi', prev_pkg)
            self._restore(tbl.attributes, 'openapi', prev_tbl)
            self._restore(col.attributes, 'openapi', prev_col)

    def test_package_veto(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        pkg = engine.db.packages['invc']
        tbl = engine.db.table('invc.invoice')
        prev_pkg = pkg.attributes.get('openapi')
        prev_tbl = tbl.attributes.get('openapi')
        try:
            pkg.attributes['openapi'] = False
            tbl.attributes['openapi'] = True
            with pytest.raises(
                    ValueError,
                    match='belongs to package .* not exposed via openapi'):
                engine.openapi_schema('invc.invoice')
        finally:
            self._restore(pkg.attributes, 'openapi', prev_pkg)
            self._restore(tbl.attributes, 'openapi', prev_tbl)

    def test_json_serializable(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        pkg = engine.db.packages['invc']
        tbl = engine.db.table('invc.invoice')
        prev_pkg = pkg.attributes.get('openapi')
        prev_tbl = tbl.attributes.get('openapi')
        try:
            pkg.attributes['openapi'] = True
            tbl.attributes['openapi'] = True
            out = engine.openapi_schema('invc.invoice')
            json.dumps(out)
        finally:
            self._restore(pkg.attributes, 'openapi', prev_pkg)
            self._restore(tbl.attributes, 'openapi', prev_tbl)

    @staticmethod
    def _restore(d, key, prev):
        if prev is None:
            d.pop(key, None)
        else:
            d[key] = prev


# ---------------------------------------------------------------------------
# run_query
# ---------------------------------------------------------------------------

class TestRunQuery:

    def test_basic_select(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        r = engine.run_query('invc.customer',
                             columns='$id,$account_name', limit=3)
        assert r['error'] is None
        assert r['rowcount'] == 3
        assert len(r['rows']) == 3
        for row in r['rows']:
            assert set(row.keys()) >= {'id', 'account_name'}

    def test_envelope_keys(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        r = engine.run_query('invc.customer', columns='$id', limit=1)
        assert set(r.keys()) == {
            'rows', 'rowcount', 'truncated', 'elapsed_ms', 'error'
        }
        assert isinstance(r['elapsed_ms'], float)

    def test_max_rows_clamp(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        r = engine.run_query('invc.customer', columns='$id',
                             limit=999, max_rows=2)
        assert r['rowcount'] == 2
        assert r['truncated'] is True

    def test_engine_level_max_rows(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application, max_rows=3)
        r = engine.run_query('invc.customer', columns='$id', limit=999)
        assert r['rowcount'] == 3
        assert r['truncated'] is True

    def test_per_call_max_rows_overrides_engine(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application, max_rows=2)
        r = engine.run_query('invc.customer', columns='$id',
                             limit=5, max_rows=5)
        assert r['rowcount'] == 5

    def test_truncated_false_when_rowcount_equals_cap_naturally(self,
                                                                 db_sqlite):
        """When the table happens to have exactly ``cap`` rows and the
        caller did not request more, ``truncated`` must be False —
        nothing was actually cut off."""
        engine = ApiEngine(db_sqlite.application)
        total = engine.run_query('invc.state',
                                 columns='$code')['rowcount']
        # Cap exactly equal to the table size, no explicit limit:
        # the engine returns all rows, but capped by max_rows. Since
        # the caller didn't ask for more, this is not truncation.
        r = engine.run_query('invc.state', columns='$code',
                             max_rows=total)
        assert r['rowcount'] == total
        assert r['truncated'] is False

    def test_truncated_false_when_limit_smaller_than_cap(self, db_sqlite):
        """If the caller explicitly limits below the cap, the cap
        never engages — ``truncated`` must be False even if rowcount
        equals the explicit limit."""
        engine = ApiEngine(db_sqlite.application)
        r = engine.run_query('invc.customer', columns='$id',
                             limit=3, max_rows=100)
        assert r['rowcount'] == 3
        assert r['truncated'] is False

    def test_invalid_sql_caught_as_error(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        r = engine.run_query('invc.invoice',
                             where='this is not valid SQL', limit=1)
        assert r['error'] is not None
        assert r['rowcount'] == 0

    def test_opt_kwargs_unknown_key_raises(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        with pytest.raises(ValueError, match='Unknown opt_kwargs'):
            engine.run_query('invc.customer',
                             opt_kwargs={'unknown_key': True})

    def test_opt_kwargs_valid_keys_accepted(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        r = engine.run_query('invc.customer', columns='$id',
                             opt_kwargs={'excludeLogicalDeleted': True},
                             limit=1)
        assert r['error'] is None

    def test_json_safe_envelope_plain(self, db_sqlite):
        """Envelope is serializable by stdlib json without any custom
        encoder for the typical projection (strings, ids)."""
        engine = ApiEngine(db_sqlite.application)
        r = engine.run_query('invc.customer', columns='$id,$account_name',
                             limit=2)
        json.dumps(r)

    def test_json_safe_envelope_with_decimal_and_date(self, db_sqlite):
        """Envelope is serializable by stdlib json even when the
        selection includes Decimal and date columns: the engine
        coerces them to JSON-safe shapes."""
        engine = ApiEngine(db_sqlite.application)
        r = engine.run_query('invc.invoice',
                             columns='$id,$total,$date', limit=2)
        assert r['error'] is None
        # Plain json.dumps without default= must succeed.
        json.dumps(r)
        # Spot-check the coercion: Decimal becomes str, date becomes
        # ISO string.
        for row in r['rows']:
            if row.get('total') is not None:
                assert isinstance(row['total'], str)
            if row.get('date') is not None:
                assert isinstance(row['date'], str)

    def test_rejects_statement_timeout_ms(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        with pytest.raises(TypeError):
            engine.run_query('invc.customer',
                             columns='$id', limit=1,
                             statement_timeout_ms=100)


# ---------------------------------------------------------------------------
# partition_kwargs (live test on real partitioned tables)
# ---------------------------------------------------------------------------

class TestPartition:

    def test_partition_single_value(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        # invc.invoice declares partition_customer_state='invc_state'
        # Get a known state code first
        states_r = engine.run_query(
            'invc.state', columns='$code', limit=10)
        assert states_r['rowcount'] > 0
        target = states_r['rows'][0]['code']
        # Filter invoices by that state
        rp = engine.run_query(
            'invc.invoice', columns='$id,$customer_state',
            partition_kwargs={'invc_state': target}, limit=9999)
        # All returned rows must have customer_state == target
        for row in rp['rows']:
            assert row.get('customer_state') == target

    def test_partition_list_value(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        states_r = engine.run_query(
            'invc.state', columns='$code', limit=10)
        chosen = [s['code'] for s in states_r['rows'][:2]]
        rp = engine.run_query(
            'invc.invoice', columns='$id,$customer_state',
            partition_kwargs={'invc_state': chosen}, limit=9999)
        for row in rp['rows']:
            assert row.get('customer_state') in chosen

    def test_partition_restores_env(self, db_sqlite):
        engine = ApiEngine(db_sqlite.application)
        before = engine.db.currentEnv.get('current_invc_state')
        engine.run_query('invc.invoice', columns='$id',
                         partition_kwargs={'invc_state': 'NSW'}, limit=1)
        after = engine.db.currentEnv.get('current_invc_state')
        assert after == before


# ---------------------------------------------------------------------------
# SQL fragment blacklist
# ---------------------------------------------------------------------------

class TestSqlBlacklist:
    """Reject SQL fragments carrying injection-style patterns on
    columns/where/having/order_by/group_by. sqlparams and structured
    inputs are not subject to the blacklist."""

    def _expect_rejected(self, engine, **kwargs):
        kwargs.setdefault('limit', 1)
        with pytest.raises(ApiEngineError, match='Rejected'):
            engine.run_query('invc.customer', **kwargs)

    # -- statement injection / comments --------------------------------

    def test_semicolon_in_where_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id IS NULL; DROP TABLE x')

    def test_line_comment_in_columns_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              columns='$id -- evil')

    def test_block_comment_in_where_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id IS NULL /* hide */')

    def test_null_byte_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id\x00')

    # -- DDL / DML keywords --------------------------------------------

    def test_drop_keyword_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id IN (DROP TABLE x)')

    def test_insert_keyword_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id IS NULL INSERT')

    def test_update_keyword_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              order_by='UPDATE')

    def test_delete_keyword_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              having='DELETE')

    # -- UNION / nested SELECT -----------------------------------------

    def test_union_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id IS NULL UNION SELECT 1')

    def test_nested_select_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id IN (SELECT id FROM other)')

    # -- system catalogs / recon ---------------------------------------

    def test_information_schema_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              columns='information_schema.tables')

    def test_pg_catalog_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id IS NULL OR pg_catalog')

    def test_version_function_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              columns='version()')

    def test_current_user_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='$id = current_user')

    # -- DoS / sleep ---------------------------------------------------

    def test_pg_sleep_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='pg_sleep(2.0) IS NULL')

    def test_sleep_function_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='SLEEP(5) IS NULL')

    def test_waitfor_delay_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='WAITFOR DELAY')

    # -- tautologies ---------------------------------------------------

    def test_numeric_tautology_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='1=1')

    def test_string_tautology_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where="'a'='a'")

    # -- bypass tricks -------------------------------------------------

    def test_char_function_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              columns='CHAR(65)')

    def test_chr_function_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              columns='CHR(65)')

    # -- session statements --------------------------------------------

    def test_set_statement_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              where='SET statement_timeout = 0')

    def test_commit_keyword_rejected(self, db_sqlite):
        self._expect_rejected(ApiEngine(db_sqlite.application),
                              having='COMMIT')

    # -- false-positive guards (legitimate uses must pass) -------------

    def test_column_name_dropdown_is_accepted(self, db_sqlite):
        """`dropdown` is a legitimate identifier, must not trip DROP."""
        engine = ApiEngine(db_sqlite.application)
        # We don't run a real query (the column doesn't exist on the
        # test DB), we just check the blacklist does not reject it.
        # Use a column expression that survives the blacklist.
        # Should not raise
        _check_sql_fragment('$dropdown_field', 'columns')

    def test_column_name_update_at_is_accepted(self, db_sqlite):
        _check_sql_fragment('$update_at', 'columns')

    def test_column_name_selection_is_accepted(self, db_sqlite):
        _check_sql_fragment('$selection_id', 'columns')

    def test_legitimate_aggregate_accepted(self, db_sqlite):
        """SUM/COUNT/AVG and similar read-only aggregates pass."""
        _check_sql_fragment('count(*),sum($total),avg($total)', 'columns')

    def test_legitimate_function_accepted(self, db_sqlite):
        _check_sql_fragment('length($name),upper($name),coalesce($a,$b)',
                            'columns')

    def test_gnrsql_macro_accepted(self, db_sqlite):
        """gnrsql macros are safe by construction (expanded server-side)."""
        _check_sql_fragment('$date #IN_RANGE :range', 'where')

    def test_gnrsql_relation_path_accepted(self, db_sqlite):
        _check_sql_fragment('@customer_id.@state.name', 'columns')


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

def test_public_api_exports():
    """`from gnr.app.api_engine import ApiEngine` is the only public export."""
    import gnr.app.api_engine as mod
    assert hasattr(mod, 'ApiEngine')
    assert 'ApiEngine' in mod.__all__
