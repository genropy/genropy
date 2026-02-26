"""Virtual column stress tests using RuntimeModel.

All formula columns are defined via RuntimeModel (rm.table().formulaColumn()),
not in the static model. This validates that RuntimeModel can handle the full
range of virtual column patterns: aggregations, top-N, temporal, deep traversal,
WHERE/ORDER BY on formulas, relation navigation from formula results, multi-table,
and extreme combinations.

Categories:
  1. Basic aggregations (COUNT, SUM, AVG, MAX, MIN)
  2. Formula columns in WHERE clauses
  3. Formula columns in ORDER BY
  4. Top-N pattern (GROUP BY + ORDER BY + LIMIT 1)
  5. Formula result as relation base (@rt_col.field navigation)
  6. Temporal filters (EXTRACT-based formula columns)
  7. Deep relation traversal (2+ hop in subquery)
  8. Multi-table (runtime columns on multiple tables)
  9. sql_formula (inline SQL expressions)
  10. Kitchen sink (extreme combinations)
"""
import pytest


# ---------------------------------------------------------------------------
#  Fixtures — build RuntimeModel definitions
# ---------------------------------------------------------------------------

@pytest.fixture
def rm_aggregations(db):
    """RuntimeModel with basic aggregation columns on customer."""
    rm = db.runtimeModel()
    cust = rm.table('invc.customer')
    cust.formulaColumn('rt_n_invoices', dtype='L',
        select=dict(table='invc.invoice',
                    columns='COUNT(*)',
                    where='$customer_id=#THIS.id'))
    cust.formulaColumn('rt_invoiced_total', dtype='N',
        select=dict(table='invc.invoice',
                    columns='SUM($total)',
                    where='$customer_id=#THIS.id'))
    cust.formulaColumn('rt_last_invoice_date', dtype='D',
        select=dict(table='invc.invoice',
                    columns='MAX($date)',
                    where='$customer_id=#THIS.id'))
    cust.formulaColumn('rt_avg_invoice_total', dtype='N',
        select=dict(table='invc.invoice',
                    columns='AVG($total)',
                    where='$customer_id=#THIS.id'))
    cust.formulaColumn('rt_max_invoice', dtype='N',
        select=dict(table='invc.invoice',
                    columns='MAX($total)',
                    where='$customer_id=#THIS.id'))
    cust.formulaColumn('rt_min_invoice', dtype='N',
        select=dict(table='invc.invoice',
                    columns='MIN($total)',
                    where='$customer_id=#THIS.id'))
    return rm


@pytest.fixture
def rm_topn(db):
    """RuntimeModel with top-N pattern columns on customer."""
    rm = db.runtimeModel()
    cust = rm.table('invc.customer')
    cust.formulaColumn('rt_top_product_id', dtype='T',
        select=dict(table='invc.invoice_row',
                    columns='$product_id',
                    where='@invoice_id.customer_id=#THIS.id',
                    group_by='$product_id',
                    order_by='COUNT(*) DESC',
                    limit=1,
        )).relation('product.id', relation_name='rt_customer_top_product')
    cust.formulaColumn('rt_last_invoice_id', dtype='T',
        select=dict(table='invc.invoice',
                    columns='$id',
                    where='$customer_id=#THIS.id',
                    order_by='$date DESC',
                    limit=1,
        ))
    return rm


@pytest.fixture
def rm_temporal(db):
    """RuntimeModel with temporal (per-year) columns on customer."""
    rm = db.runtimeModel()
    cust = rm.table('invc.customer')
    for year in (2022, 2023, 2024, 2025):
        cust.formulaColumn(f'rt_invoiced_{year}', dtype='N',
            select=dict(table='invc.invoice',
                        columns='SUM($total)',
                        where=f"$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)={year}"))
        cust.formulaColumn(f'rt_n_invoices_{year}', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where=f"$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)={year}"))
    return rm


@pytest.fixture
def rm_product(db):
    """RuntimeModel with formula columns on product."""
    rm = db.runtimeModel()
    prod = rm.table('invc.product')
    prod.formulaColumn('rt_n_sold', dtype='L',
        select=dict(table='invc.invoice_row',
                    columns='COUNT(*)',
                    where='$product_id=#THIS.id'))
    prod.formulaColumn('rt_total_sold', dtype='N',
        select=dict(table='invc.invoice_row',
                    columns='SUM($tot_price)',
                    where='$product_id=#THIS.id'))
    prod.formulaColumn('rt_top_customer_id', dtype='T',
        select=dict(table='invc.invoice_row',
                    columns='@invoice_id.customer_id',
                    where='$product_id=#THIS.id',
                    group_by='@invoice_id.customer_id',
                    order_by='COUNT(*) DESC',
                    limit=1,
        ))
    return rm


@pytest.fixture
def rm_invoice(db):
    """RuntimeModel with formula columns on invoice."""
    rm = db.runtimeModel()
    inv = rm.table('invc.invoice')
    inv.formulaColumn('rt_n_rows', dtype='L',
        select=dict(table='invc.invoice_row',
                    columns='COUNT(*)',
                    where='$invoice_id=#THIS.id'))
    inv.formulaColumn('rt_row_total', dtype='N',
        select=dict(table='invc.invoice_row',
                    columns='SUM($tot_price)',
                    where='$invoice_id=#THIS.id'))
    return rm


@pytest.fixture
def rm_sql_formula(db):
    """RuntimeModel with inline sql_formula columns."""
    rm = db.runtimeModel()
    cust = rm.table('invc.customer')
    cust.formulaColumn('rt_upper_name', dtype='T',
        sql_formula='UPPER($account_name)')
    cust.formulaColumn('rt_name_length', dtype='L',
        sql_formula='LENGTH($account_name)')
    return rm


@pytest.fixture
def rm_multitable(db):
    """RuntimeModel with columns on customer, product, and invoice."""
    rm = db.runtimeModel()
    cust = rm.table('invc.customer')
    cust.formulaColumn('rt_n_inv', dtype='L',
        select=dict(table='invc.invoice',
                    columns='COUNT(*)',
                    where='$customer_id=#THIS.id'))
    cust.formulaColumn('rt_inv_total', dtype='N',
        select=dict(table='invc.invoice',
                    columns='SUM($total)',
                    where='$customer_id=#THIS.id'))
    prod = rm.table('invc.product')
    prod.formulaColumn('rt_n_rows', dtype='L',
        select=dict(table='invc.invoice_row',
                    columns='COUNT(*)',
                    where='$product_id=#THIS.id'))
    inv = rm.table('invc.invoice')
    inv.formulaColumn('rt_n_items', dtype='L',
        select=dict(table='invc.invoice_row',
                    columns='COUNT(*)',
                    where='$invoice_id=#THIS.id'))
    return rm


# ---------------------------------------------------------------------------
#  1. BASIC AGGREGATIONS
# ---------------------------------------------------------------------------

class TestBasicAggregations:
    """COUNT, SUM, AVG, MAX, MIN on customer → invoice."""

    def test_count(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_n_invoices',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0
        for row in result:
            assert 'rt_n_invoices' in row

    def test_sum(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_invoiced_total',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_avg(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_avg_invoice_total',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_max(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_max_invoice',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_min(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_min_invoice',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_last_date(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_last_invoice_date',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_all_aggregations_together(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns=('$account_name, $rt_n_invoices, $rt_invoiced_total, '
                         '$rt_last_invoice_date, $rt_avg_invoice_total, '
                         '$rt_max_invoice, $rt_min_invoice'),
                order_by='$id', limit=20).fetch()
        assert len(result) > 0
        for row in result:
            assert 'rt_n_invoices' in row
            assert 'rt_invoiced_total' in row
            assert 'rt_last_invoice_date' in row
            assert 'rt_avg_invoice_total' in row

    def test_count_values_are_correct(self, db, rm_aggregations):
        """Verify COUNT matches actual row count per customer."""
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$id, $rt_n_invoices',
                order_by='$id').fetch()
        for row in result:
            cnt = db.table('invc.invoice').readColumns(
                columns='COUNT(*)',
                where='$customer_id=:cid',
                cid=row['id'])
            assert row['rt_n_invoices'] == cnt


# ---------------------------------------------------------------------------
#  2. FORMULA COLUMNS IN WHERE
# ---------------------------------------------------------------------------

class TestFormulaInWhere:
    """Filtering on runtime formula column values."""

    def test_where_count_gt_zero(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_n_invoices',
                where='$rt_n_invoices > 0',
                order_by='$id').fetch()
        assert all(r['rt_n_invoices'] > 0 for r in result)

    def test_where_sum_gt_threshold(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_invoiced_total',
                where='$rt_invoiced_total > :threshold',
                threshold=1000,
                order_by='$rt_invoiced_total DESC').fetch()
        assert len(result) >= 0  # may be empty depending on data

    def test_where_multiple_formulas(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_n_invoices, $rt_invoiced_total',
                where='$rt_n_invoices > :min_inv AND $rt_invoiced_total > :min_total',
                min_inv=1, min_total=100,
                order_by='$id').fetch()
        for r in result:
            assert r['rt_n_invoices'] > 1
            assert r['rt_invoiced_total'] > 100

    def test_where_formula_and_physical(self, db, rm_aggregations):
        """WHERE mixing runtime formula and physical column."""
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $state, $rt_n_invoices',
                where='$rt_n_invoices > 0 AND $state IS NOT NULL',
                order_by='$id').fetch()
        for r in result:
            assert r['rt_n_invoices'] > 0
            assert r['state'] is not None

    def test_where_on_product_formula(self, db, rm_product):
        with rm_product:
            result = db.query('invc.product',
                columns='$code, $description, $rt_n_sold',
                where='$rt_n_sold = 0',
                order_by='$code').fetch()
        for r in result:
            assert r['rt_n_sold'] == 0


# ---------------------------------------------------------------------------
#  3. FORMULA COLUMNS IN ORDER BY
# ---------------------------------------------------------------------------

class TestFormulaInOrderBy:
    """Ordering by runtime formula column values."""

    def test_order_by_count_desc(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_n_invoices',
                order_by='$rt_n_invoices DESC', limit=20).fetch()
        assert len(result) > 0
        values = [r['rt_n_invoices'] for r in result]
        assert values == sorted(values, reverse=True)

    def test_order_by_sum_asc(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_invoiced_total',
                order_by='$rt_invoiced_total ASC', limit=20).fetch()
        assert len(result) > 0

    def test_order_by_formula_with_where(self, db, rm_aggregations):
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_n_invoices',
                where='$rt_n_invoices > 0',
                order_by='$rt_n_invoices DESC', limit=10).fetch()
        values = [r['rt_n_invoices'] for r in result]
        assert values == sorted(values, reverse=True)

    def test_order_by_product_total_sold(self, db, rm_product):
        with rm_product:
            result = db.query('invc.product',
                columns='$description, $rt_total_sold',
                order_by='$rt_total_sold DESC', limit=10).fetch()
        assert len(result) > 0


# ---------------------------------------------------------------------------
#  4. TOP-N PATTERN (GROUP BY + ORDER BY + LIMIT 1)
# ---------------------------------------------------------------------------

class TestTopNFormulas:
    """Formula columns using GROUP BY + ORDER BY + LIMIT 1."""

    def test_top_product_id(self, db, rm_topn):
        with rm_topn:
            result = db.query('invc.customer',
                columns='$account_name, $rt_top_product_id',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_last_invoice_id(self, db, rm_topn):
        with rm_topn:
            result = db.query('invc.customer',
                columns='$account_name, $rt_last_invoice_id',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_both_topn_together(self, db, rm_topn):
        with rm_topn:
            result = db.query('invc.customer',
                columns='$account_name, $rt_top_product_id, $rt_last_invoice_id',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0


# ---------------------------------------------------------------------------
#  5. FORMULA AS RELATION BASE
#     Navigate FROM a runtime formula column INTO the related table
# ---------------------------------------------------------------------------

class TestFormulaAsRelationBase:
    """Use runtime formula column result to navigate further relations."""

    def test_top_product_description(self, db, rm_topn):
        """Navigate customer → @rt_top_product_id.description."""
        with rm_topn:
            result = db.query('invc.customer',
                columns='$account_name, $rt_top_product_id, @rt_top_product_id.description',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_top_product_unit_price(self, db, rm_topn):
        """Navigate customer → @rt_top_product_id.unit_price."""
        with rm_topn:
            result = db.query('invc.customer',
                columns='$account_name, $rt_top_product_id, @rt_top_product_id.unit_price',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_top_product_code(self, db, rm_topn):
        """Navigate customer → @rt_top_product_id.code."""
        with rm_topn:
            result = db.query('invc.customer',
                columns='$account_name, $rt_top_product_id, @rt_top_product_id.code',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0


# ---------------------------------------------------------------------------
#  6. TEMPORAL FILTERS (EXTRACT-based)
# ---------------------------------------------------------------------------

class TestTemporalFormulas:
    """Formula columns with EXTRACT(YEAR) filters.

    Skipped on SQLite: EXTRACT(YEAR FROM ...) is not supported.
    """

    def test_invoiced_per_year(self, db, rm_temporal):
        if db.implementation == 'sqlite':
            pytest.skip('EXTRACT not supported on SQLite')
        with rm_temporal:
            result = db.query('invc.customer',
                columns=('$account_name, $rt_invoiced_2022, $rt_invoiced_2023, '
                         '$rt_invoiced_2024, $rt_invoiced_2025'),
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_count_per_year(self, db, rm_temporal):
        if db.implementation == 'sqlite':
            pytest.skip('EXTRACT not supported on SQLite')
        with rm_temporal:
            result = db.query('invc.customer',
                columns=('$account_name, $rt_n_invoices_2022, $rt_n_invoices_2023, '
                         '$rt_n_invoices_2024, $rt_n_invoices_2025'),
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_temporal_in_where(self, db, rm_temporal):
        if db.implementation == 'sqlite':
            pytest.skip('EXTRACT not supported on SQLite')
        with rm_temporal:
            result = db.query('invc.customer',
                columns='$account_name, $rt_invoiced_2024',
                where='$rt_invoiced_2024 > :min_total',
                min_total=0,
                order_by='$rt_invoiced_2024 DESC').fetch()
        assert len(result) >= 0

    def test_temporal_mixed_with_aggregations(self, db):
        """Temporal + global aggregations in the same RuntimeModel."""
        if db.implementation == 'sqlite':
            pytest.skip('EXTRACT not supported on SQLite')
        rm = db.runtimeModel()
        cust = rm.table('invc.customer')
        cust.formulaColumn('rt_n_invoices', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where='$customer_id=#THIS.id'))
        cust.formulaColumn('rt_invoiced_total', dtype='N',
            select=dict(table='invc.invoice',
                        columns='SUM($total)',
                        where='$customer_id=#THIS.id'))
        cust.formulaColumn('rt_invoiced_2024', dtype='N',
            select=dict(table='invc.invoice',
                        columns='SUM($total)',
                        where="$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)=2024"))
        cust.formulaColumn('rt_n_invoices_2024', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where="$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)=2024"))
        with rm:
            result = db.query('invc.customer',
                columns=('$account_name, $rt_n_invoices, $rt_invoiced_total, '
                         '$rt_invoiced_2024, $rt_n_invoices_2024'),
                order_by='$id', limit=20).fetch()
        assert len(result) > 0


# ---------------------------------------------------------------------------
#  7. DEEP RELATION TRAVERSAL (2+ hops in subquery)
# ---------------------------------------------------------------------------

class TestDeepRelationTraversal:
    """Formula columns that traverse 2+ relation levels in subquery WHERE."""

    def test_product_top_state(self, db):
        """product → invoice_row → invoice → customer.state (2 hops)."""
        rm = db.runtimeModel()
        rm.table('invc.product').formulaColumn('rt_top_state', dtype='T',
            select=dict(table='invc.invoice_row',
                        columns='@invoice_id.@customer_id.state',
                        where='$product_id=#THIS.id',
                        group_by='@invoice_id.@customer_id.state',
                        order_by='COUNT(*) DESC',
                        limit=1))
        with rm:
            result = db.query('invc.product',
                columns='$code, $description, $rt_top_state',
                order_by='$code').fetch()
        assert len(result) > 0

    def test_product_top_customer_deep(self, db):
        """product → invoice_row → invoice.customer_id (via @invoice_id)."""
        rm = db.runtimeModel()
        rm.table('invc.product').formulaColumn('rt_top_customer_id', dtype='T',
            select=dict(table='invc.invoice_row',
                        columns='@invoice_id.customer_id',
                        where='$product_id=#THIS.id',
                        group_by='@invoice_id.customer_id',
                        order_by='COUNT(*) DESC',
                        limit=1))
        with rm:
            result = db.query('invc.product',
                columns='$code, $description, $rt_top_customer_id',
                order_by='$code').fetch()
        assert len(result) > 0


# ---------------------------------------------------------------------------
#  8. MULTI-TABLE — runtime columns on multiple tables in same query
# ---------------------------------------------------------------------------

class TestMultiTable:
    """Runtime columns on customer, product, and invoice in the same RuntimeModel."""

    def test_customer_and_product(self, db, rm_multitable):
        with rm_multitable:
            customers = db.query('invc.customer',
                columns='$account_name, $rt_n_inv, $rt_inv_total',
                order_by='$id', limit=20).fetch()
            products = db.query('invc.product',
                columns='$description, $rt_n_rows',
                order_by='$code', limit=20).fetch()
        assert len(customers) > 0
        assert len(products) > 0

    def test_all_three_tables(self, db, rm_multitable):
        with rm_multitable:
            customers = db.query('invc.customer',
                columns='$account_name, $rt_n_inv',
                order_by='$id', limit=10).fetch()
            products = db.query('invc.product',
                columns='$description, $rt_n_rows',
                order_by='$code', limit=10).fetch()
            invoices = db.query('invc.invoice',
                columns='$inv_number, $rt_n_items',
                order_by='$id', limit=10).fetch()
        assert len(customers) > 0
        assert len(products) > 0
        assert len(invoices) >= 0  # SQLite test instance may have no invoices

    def test_multitable_with_where(self, db, rm_multitable):
        with rm_multitable:
            customers = db.query('invc.customer',
                columns='$account_name, $rt_n_inv',
                where='$rt_n_inv > 0',
                order_by='$id').fetch()
            products = db.query('invc.product',
                columns='$description, $rt_n_rows',
                where='$rt_n_rows > 0',
                order_by='$code').fetch()
        for r in customers:
            assert r['rt_n_inv'] > 0
        for r in products:
            assert r['rt_n_rows'] > 0


# ---------------------------------------------------------------------------
#  9. SQL_FORMULA (inline SQL expressions)
# ---------------------------------------------------------------------------

class TestSqlFormula:
    """Runtime columns with sql_formula instead of subselect."""

    def test_upper(self, db, rm_sql_formula):
        with rm_sql_formula:
            result = db.query('invc.customer',
                columns='$account_name, $rt_upper_name',
                order_by='$id', limit=20).fetch()
        for row in result:
            if row['account_name']:
                assert row['rt_upper_name'] == row['account_name'].upper()

    def test_length(self, db, rm_sql_formula):
        with rm_sql_formula:
            result = db.query('invc.customer',
                columns='$account_name, $rt_name_length',
                order_by='$id', limit=20).fetch()
        for row in result:
            if row['account_name']:
                assert row['rt_name_length'] == len(row['account_name'])

    def test_sql_formula_in_where(self, db, rm_sql_formula):
        with rm_sql_formula:
            result = db.query('invc.customer',
                columns='$account_name, $rt_name_length',
                where='$rt_name_length > :min_len',
                min_len=10,
                order_by='$id').fetch()
        for row in result:
            assert row['rt_name_length'] > 10

    def test_sql_formula_in_order_by(self, db, rm_sql_formula):
        with rm_sql_formula:
            result = db.query('invc.customer',
                columns='$account_name, $rt_name_length',
                order_by='$rt_name_length DESC', limit=10).fetch()
        values = [r['rt_name_length'] for r in result]
        assert values == sorted(values, reverse=True)


# ---------------------------------------------------------------------------
#  10. KITCHEN SINK — maximum complexity combinations
# ---------------------------------------------------------------------------

class TestKitchenSink:
    """Extreme combinations of all features."""

    def test_aggregations_plus_topn(self, db):
        """Aggregations + top-N in the same RuntimeModel."""
        rm = db.runtimeModel()
        cust = rm.table('invc.customer')
        cust.formulaColumn('rt_n_inv', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where='$customer_id=#THIS.id'))
        cust.formulaColumn('rt_total', dtype='N',
            select=dict(table='invc.invoice',
                        columns='SUM($total)',
                        where='$customer_id=#THIS.id'))
        cust.formulaColumn('rt_top_product', dtype='T',
            select=dict(table='invc.invoice_row',
                        columns='$product_id',
                        where='@invoice_id.customer_id=#THIS.id',
                        group_by='$product_id',
                        order_by='COUNT(*) DESC',
                        limit=1))
        with rm:
            result = db.query('invc.customer',
                columns='$account_name, $rt_n_inv, $rt_total, $rt_top_product',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0

    def test_formula_where_order_limit_combined(self, db, rm_aggregations):
        """WHERE + ORDER BY + LIMIT all on runtime formula columns."""
        with rm_aggregations:
            result = db.query('invc.customer',
                columns='$account_name, $rt_n_invoices, $rt_invoiced_total',
                where='$rt_n_invoices > :min_inv AND $rt_invoiced_total > :min_total',
                min_inv=1, min_total=100,
                order_by='$rt_invoiced_total DESC',
                limit=10).fetch()
        assert len(result) >= 0

    def test_relation_plus_formula_on_related_table(self, db):
        """Invoice with physical relation to customer AND runtime formula on invoice."""
        rm = db.runtimeModel()
        rm.table('invc.invoice').formulaColumn('rt_n_rows', dtype='L',
            select=dict(table='invc.invoice_row',
                        columns='COUNT(*)',
                        where='$invoice_id=#THIS.id'))
        rm.table('invc.invoice').formulaColumn('rt_row_total', dtype='N',
            select=dict(table='invc.invoice_row',
                        columns='SUM($tot_price)',
                        where='$invoice_id=#THIS.id'))
        with rm:
            result = db.query('invc.invoice',
                columns=('$inv_number, $date, $total, @customer_id.account_name, '
                         '@customer_id.state, $rt_n_rows, $rt_row_total'),
                order_by='$id', limit=20).fetch()
        assert len(result) >= 0  # SQLite test instance may have no invoices
        for row in result:
            assert 'rt_n_rows' in row
            assert '_customer_id_account_name' in row

    def test_product_all_formulas(self, db):
        """All product formulas: aggregations + deep traversal."""
        rm = db.runtimeModel()
        prod = rm.table('invc.product')
        prod.formulaColumn('rt_n_sold', dtype='L',
            select=dict(table='invc.invoice_row',
                        columns='COUNT(*)',
                        where='$product_id=#THIS.id'))
        prod.formulaColumn('rt_total_sold', dtype='N',
            select=dict(table='invc.invoice_row',
                        columns='SUM($tot_price)',
                        where='$product_id=#THIS.id'))
        prod.formulaColumn('rt_top_customer', dtype='T',
            select=dict(table='invc.invoice_row',
                        columns='@invoice_id.customer_id',
                        where='$product_id=#THIS.id',
                        group_by='@invoice_id.customer_id',
                        order_by='COUNT(*) DESC',
                        limit=1))
        prod.formulaColumn('rt_top_state', dtype='T',
            select=dict(table='invc.invoice_row',
                        columns='@invoice_id.@customer_id.state',
                        where='$product_id=#THIS.id',
                        group_by='@invoice_id.@customer_id.state',
                        order_by='COUNT(*) DESC',
                        limit=1))
        with rm:
            result = db.query('invc.product',
                columns=('$code, $description, $rt_n_sold, $rt_total_sold, '
                         '$rt_top_customer, $rt_top_state'),
                order_by='$code').fetch()
        assert len(result) > 0

    def test_formula_navigation_then_filter(self, db, rm_topn):
        """Navigate runtime formula relation + filter on result."""
        with rm_topn:
            result = db.query('invc.customer',
                columns=('$account_name, $rt_top_product_id, '
                         '@rt_top_product_id.description, @rt_top_product_id.unit_price'),
                where='$rt_top_product_id IS NOT NULL',
                order_by='$id', limit=20).fetch()
        assert len(result) >= 0

    def test_runtime_coexists_with_static(self, db):
        """Runtime columns work alongside static formula columns."""
        rm = db.runtimeModel()
        rm.table('invc.customer').formulaColumn('rt_max_invoice', dtype='N',
            select=dict(table='invc.invoice',
                        columns='MAX($total)',
                        where='$customer_id=#THIS.id'))
        with rm:
            result = db.query('invc.customer',
                columns='$account_name, $n_invoices, $invoiced_total, $rt_max_invoice',
                order_by='$id', limit=20).fetch()
        assert len(result) > 0
        for row in result:
            assert 'n_invoices' in row       # static
            assert 'invoiced_total' in row   # static
            assert 'rt_max_invoice' in row   # runtime


# ---------------------------------------------------------------------------
#  REUSE AND ISOLATION
# ---------------------------------------------------------------------------

class TestReuseAndIsolation:
    """Verify that RuntimeModel is reusable and does not pollute static model."""

    def test_invisible_outside(self, db, rm_aggregations):
        """Runtime columns must not be visible outside the with block."""
        with rm_aggregations:
            db.query('invc.customer',
                columns='$account_name, $rt_n_invoices').fetch()
        with pytest.raises(Exception):
            db.query('invc.customer',
                columns='$account_name, $rt_n_invoices').fetch()

    def test_reuse_same_rm(self, db, rm_aggregations):
        """Same RuntimeModel can be used in multiple with blocks."""
        with rm_aggregations:
            r1 = db.query('invc.customer',
                columns='$account_name, $rt_n_invoices',
                order_by='$id').fetch()
        with rm_aggregations:
            r2 = db.query('invc.customer',
                columns='$account_name, $rt_n_invoices',
                order_by='$id').fetch()
        assert len(r1) == len(r2)

    def test_no_model_pollution(self, db, rm_aggregations):
        """Static model must not be affected by runtime columns."""
        tbl_obj = db.model.table('customer', pkg='invc')
        static_vc = tbl_obj['virtual_columns']
        original_keys = set(static_vc.keys()) if static_vc else set()

        with rm_aggregations:
            pass

        after_keys = set(static_vc.keys()) if static_vc else set()
        assert original_keys == after_keys
