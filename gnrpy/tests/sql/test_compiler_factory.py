"""The compiler factory and the equivalence of the two SQL query compilers.

Two things are checked here.

1. ``queryCompilerClass`` picks the class the instance configuration asks for:
   the experimental flag ``<experimental><db next_sql_compiler="True"/></experimental>``
   selects ``SqlQueryCompilerNext``; a false or empty flag, the flag absent, or no
   application at all selects the legacy ``SqlQueryCompiler``.

2. The two classes compile the same query to the same SQL.  A corpus of queries
   on the ``test_invoice`` project is compiled twice, once with each class, and
   the SQL text, the bind parameters and the compiled metadata must match.
   While ``compiler_next.py`` is a copy of ``compiler.py`` this is trivially
   true; it stops being trivial as soon as the copy receives new work, which is
   exactly when the corpus has to keep the legacy behaviour honest.
"""

from contextlib import contextmanager

import pytest

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.gnrsqldata.compiler import SqlQueryCompiler
from gnr.sql.gnrsqldata.compiler_factory import queryCompilerClass
from gnr.sql.gnrsqldata.compiler_next import SqlQueryCompilerNext


@contextmanager
def next_sql_compiler_flag(db, value):
    """Set ``<experimental><db next_sql_compiler="..."/></experimental>`` on the
    application config, then restore it."""
    node = db.application.config.getNode('experimental.db', autocreate=True)
    previous = node.attr.get('next_sql_compiler')
    node.attr['next_sql_compiler'] = value
    try:
        yield
    finally:
        node.attr['next_sql_compiler'] = previous


# ===================================================================
# The corpus: every entry builds a fresh SqlQuery on a given db
# ===================================================================

def _q(table, **kwargs):
    """Build a query spec whose kwargs are all immutable."""
    def build(db):
        return db.table(table).query(**kwargs)
    return build


def _q_relation_dict(db):
    return db.table('invc.invoice').query(
        columns='$inv_number,$date',
        relationDict={'cust_name': '@customer_id.account_name',
                      'cust_state': '@customer_id.state'})


def _q_where_bag(db):
    tbl = db.table('invc.customer')
    wherebag = Bag()
    wherebag.setItem('c_1', 'NSW', column='state', op='equal')
    wherebag.setItem('c_2', 'A', column='account_name', op='startswith', jc='and')
    where, sqlargs = tbl.sqlWhereFromBag(wherebag)
    return tbl.query(columns='$account_name,$state', where=where, **sqlargs)


def _q_join_condition_one(db):
    query = db.table('invc.customer').query(columns='$id,@state.name')
    query.setJoinCondition(relation='@state',
                           condition="$tbl.code IS NOT NULL",
                           one_one=True)
    return query


def _q_join_condition_many(db):
    query = db.table('invc.customer').query(columns='$id,@invoices.total')
    query.setJoinCondition(relation='@invoices', condition='TRUE', one_one=True)
    return query


def _q_join_condition_global(db):
    query = db.table('invc.customer').query(columns='$id,$account_name')
    query.setJoinCondition(target_fld='*', from_fld='*',
                           condition='t0.account_name IS NOT NULL')
    return query


def _q_join_condition_kwarg(db):
    return db.table('invc.customer').query(
        columns='$id,@invoices.total',
        joinConditions={'@invoices': dict(condition='$tbl.total>:jc_min',
                                          params=dict(jc_min=100),
                                          one_one=None)})


QUERY_SPECS = {
    'plain_columns': _q('invc.customer', columns='$account_name,$email,$phone'),
    'all_columns': _q('invc.region', columns='*'),
    'relation_one_side': _q('invc.invoice',
                            columns='$inv_number,@customer_id.account_name'),
    'relation_one_side_deep': _q('invc.invoice_row',
                                 columns='$quantity,@invoice_id.@customer_id.account_name'),
    'relation_many_side': _q('invc.customer',
                             columns='$account_name,@invoices.inv_number'),
    'relation_many_side_distinct': _q('invc.customer',
                                      columns='@invoices.date', distinct=True),
    'alias_column': _q('invc.invoice', columns='$customer_name,$customer_state'),
    'alias_column_deep': _q('invc.invoice_row',
                            columns='$customer_region,$product_name'),
    'formula_column_select': _q('invc.invoice', columns='$inv_number,$row_count'),
    'formula_column_select_ordered': _q('invc.invoice',
                                        columns='$inv_number,$priority_note'),
    'formula_column_sql': _q('invc.invoice_row',
                             columns='$line_total,$line_gross,$is_expensive'),
    'formula_column_on_relation': _q('invc.invoice_row',
                                     columns='$pricing_analysis,$effective_price'),
    'where_param': _q('invc.customer', columns='$account_name',
                      where='$account_name LIKE :nm', nm='A%'),
    'where_relation': _q('invc.invoice', columns='$inv_number',
                         where='@customer_id.state=:st', st='NSW'),
    'where_two_params': _q('invc.invoice', columns='$inv_number',
                           where='$total>:mn AND $total<:mx', mn=10, mx=5000),
    'where_bag': _q_where_bag,
    'order_by': _q('invc.invoice', columns='$inv_number,$date',
                   order_by='$date DESC,$inv_number'),
    'order_by_relation': _q('invc.invoice', columns='$inv_number',
                            order_by='@customer_id.account_name'),
    'group_by_having': _q('invc.invoice_row',
                          columns='$product_id,SUM($quantity) AS tot_qty',
                          group_by='$product_id',
                          having='SUM($quantity)>:minq', minq=10),
    'group_by_relation': _q('invc.invoice_row',
                            columns='@invoice_id.@customer_id.state,COUNT(*) AS n_rows',
                            group_by='@invoice_id.@customer_id.state'),
    'limit_offset': _q('invc.customer', columns='$account_name',
                       order_by='$id', limit=10, offset=20),
    'distinct': _q('invc.customer', columns='$state', distinct=True),
    'for_update': _q('invc.invoice', columns='$inv_number', for_update=True),
    'exclude_logical_deleted_off': _q('invc.customer', columns='$account_name',
                                      excludeLogicalDeleted=False),
    'exclude_logical_deleted_mark': _q('invc.customer', columns='$account_name',
                                       excludeLogicalDeleted='mark'),
    'exclude_draft_off': _q('invc.customer', columns='$account_name',
                            excludeDraft=False),
    'no_pkey_column': _q('invc.customer', columns='$account_name',
                         addPkeyColumn=False),
    'ignore_table_order_by': _q('invc.invoice', columns='$inv_number',
                                ignoreTableOrderBy=True),
    'ignore_partition': _q('invc.invoice', columns='$inv_number',
                           ignorePartition=True),
    'relation_dict': _q_relation_dict,
    'join_condition_one_side': _q_join_condition_one,
    'join_condition_many_side': _q_join_condition_many,
    'join_condition_global': _q_join_condition_global,
    'join_condition_kwarg': _q_join_condition_kwarg,
    'star_relation_explicit': _q('invc.customer',
                                 columns='$account_name,*@invoices.(inv_number,date)'),
    'star_relation_all': _q('invc.invoice', columns='$inv_number,*@customer_id'),
    'star_prefix': _q('invc.invoice', columns='*inv_'),
    'subquery_formula': _q('invc.invoice', columns='$inv_number,$all_notes'),
    'join_column_relation': _q('invc.invoice',
                               columns='$inv_number,@discount_tier_id.min_amount'),
}

SPEC_NAMES = sorted(QUERY_SPECS)

COUNT_SPEC_NAMES = ['plain_columns', 'relation_many_side',
                    'where_param', 'group_by_having']


def _compile_query(db, builder, compiler_class, count=False):
    """Compile *builder*'s query with *compiler_class*, as SqlQuery.compileQuery does."""
    query = builder(db)
    compiler = compiler_class(query.dbtable.model,
                              joinConditions=query.joinConditions,
                              sqlContextName=query.sqlContextName,
                              sqlparams=query.sqlparams,
                              aliasPrefix=query.aliasPrefix,
                              locale=query.locale)
    cpl = compiler.compiledQuery(count=count,
                                 relationDict=query.relationDict,
                                 **query.querypars)
    return cpl, query.sqlparams


def _assert_same_compilation(db, builder, count=False):
    legacy_cpl, legacy_params = _compile_query(db, builder, SqlQueryCompiler,
                                               count=count)
    next_cpl, next_params = _compile_query(db, builder, SqlQueryCompilerNext,
                                           count=count)
    legacy_sql = legacy_cpl.get_sqltext(db)
    assert legacy_sql, 'the legacy compiler produced no sql'
    assert next_cpl.get_sqltext(db) == legacy_sql
    assert next_params == legacy_params
    assert next_cpl.explodingColumns == legacy_cpl.explodingColumns
    assert next_cpl.aggregateDict == legacy_cpl.aggregateDict
    assert next_cpl.relationDict == legacy_cpl.relationDict


def _compile_record(db, pkey, compiler_class):
    """Compile a record read with *compiler_class*, as SqlRecord.compileQuery does."""
    record = db.table('invc.invoice').record(pkey=pkey)
    compiler = compiler_class(record.dbtable.model,
                              sqlparams=record.sqlparams,
                              joinConditions=record.joinConditions,
                              sqlContextName=record.sqlContextName,
                              aliasPrefix=record.aliasPrefix)
    cpl = compiler.compiledRecordQuery(where='$pkey = :pkey',
                                       relationDict=record.relationDict,
                                       bagFields=record.bagFields,
                                       for_update=record.for_update,
                                       virtual_columns=record.virtual_columns,
                                       **record.relmodes)
    return cpl, record.sqlparams


def _assert_same_record_compilation(db):
    pkey = db.table('invc.invoice').query(columns='$id', limit=1).fetch()[0]['id']
    legacy_cpl, legacy_params = _compile_record(db, pkey, SqlQueryCompiler)
    next_cpl, next_params = _compile_record(db, pkey, SqlQueryCompilerNext)
    legacy_sql = legacy_cpl.get_sqltext(db)
    assert legacy_sql, 'the legacy compiler produced no sql'
    assert next_cpl.get_sqltext(db) == legacy_sql
    assert next_params == legacy_params
    assert next_cpl.explodingColumns == legacy_cpl.explodingColumns
    assert next_cpl.aggregateDict == legacy_cpl.aggregateDict
    assert next_cpl.relationDict == legacy_cpl.relationDict


# ===================================================================
# 1. The factory
# ===================================================================

class TestQueryCompilerClass:

    def test_setting_absent(self, db_sqlite):
        assert db_sqlite.application.experimentalValue('db', 'next_sql_compiler') is None
        assert queryCompilerClass(db_sqlite) is SqlQueryCompiler

    def test_setting_true(self, db_sqlite):
        with next_sql_compiler_flag(db_sqlite, 'True'):
            assert queryCompilerClass(db_sqlite) is SqlQueryCompilerNext
        assert queryCompilerClass(db_sqlite) is SqlQueryCompiler

    def test_setting_false(self, db_sqlite):
        with next_sql_compiler_flag(db_sqlite, 'False'):
            assert queryCompilerClass(db_sqlite) is SqlQueryCompiler

    def test_setting_empty_value(self, db_sqlite):
        with next_sql_compiler_flag(db_sqlite, ''):
            assert queryCompilerClass(db_sqlite) is SqlQueryCompiler

    def test_no_application(self):
        db = GnrSqlDb()
        assert db.application is None
        assert queryCompilerClass(db) is SqlQueryCompiler


class TestSwitchReachesTheQuery:
    """The two construction points honour the setting."""

    def test_query_uses_legacy_by_default(self, db_sqlite):
        cpl = db_sqlite.table('invc.invoice').query(columns='$inv_number').compiled
        assert type(cpl).__module__ == 'gnr.sql.gnrsqldata.compiler'

    def test_query_uses_next_when_selected(self, db_sqlite):
        with next_sql_compiler_flag(db_sqlite, 'True'):
            cpl = db_sqlite.table('invc.invoice').query(columns='$inv_number').compiled
        assert type(cpl).__module__ == 'gnr.sql.gnrsqldata.compiler_next'

    def test_record_uses_next_when_selected(self, db_sqlite):
        tbl = db_sqlite.table('invc.invoice')
        pkey = tbl.query(columns='$id', limit=1).fetch()[0]['id']
        with next_sql_compiler_flag(db_sqlite, 'True'):
            cpl = tbl.record(pkey=pkey).compiled
        assert type(cpl).__module__ == 'gnr.sql.gnrsqldata.compiler_next'

    def test_same_sql_through_the_switch(self, db_sqlite):
        tbl = db_sqlite.table('invc.invoice')
        legacy_sql = tbl.query(columns='$inv_number,@customer_id.account_name',
                               order_by='$date').sqltext
        with next_sql_compiler_flag(db_sqlite, 'True'):
            next_sql = tbl.query(columns='$inv_number,@customer_id.account_name',
                                 order_by='$date').sqltext
        assert next_sql == legacy_sql


# ===================================================================
# 2. The reference corpus
# ===================================================================

class TestCorpusSqlite:

    @pytest.mark.parametrize('spec_name', SPEC_NAMES)
    def test_same_compilation(self, db_sqlite, spec_name):
        _assert_same_compilation(db_sqlite, QUERY_SPECS[spec_name])

    @pytest.mark.parametrize('spec_name', COUNT_SPEC_NAMES)
    def test_same_count_compilation(self, db_sqlite, spec_name):
        _assert_same_compilation(db_sqlite, QUERY_SPECS[spec_name], count=True)

    def test_same_record_compilation(self, db_sqlite):
        _assert_same_record_compilation(db_sqlite)


class TestCorpusPostgres:

    @pytest.mark.parametrize('spec_name', SPEC_NAMES)
    def test_same_compilation(self, db_pg, spec_name):
        _assert_same_compilation(db_pg, QUERY_SPECS[spec_name])

    @pytest.mark.parametrize('spec_name', COUNT_SPEC_NAMES)
    def test_same_count_compilation(self, db_pg, spec_name):
        _assert_same_compilation(db_pg, QUERY_SPECS[spec_name], count=True)

    def test_same_record_compilation(self, db_pg):
        _assert_same_record_compilation(db_pg)
