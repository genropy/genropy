"""Torture tests for the SQL compiler.

These tests exercise the most complex scenarios possible to stress-test
the compiler before introducing CTE and LATERAL optimizations.

Every test runs the same query with and without enable_lazy_subquery
and asserts identical results — proving the IR layer is transparent.

Categories:
  1. Nested formula columns (formula referencing another formula)
  2. Deep relation traversal (2+ levels of @relation)
  3. Formula columns in WHERE clauses
  4. Formula columns in ORDER BY
  5. Formula columns with LIMIT 1 + ORDER BY (top-N pattern)
  6. Multiple formula columns from different tables in same query
  7. Formula result used to navigate further relations
  8. Temporal filters (EXTRACT-based formula columns)
  9. Combinations of all the above
  10. JOIN mode torture (enable_sq_join=True)
  11. No placeholder leak verification
"""
import pytest
from decimal import Decimal


def _compare_rows(r_eager, r_lazy, keys, label_key=None):
    """Helper: assert that two result sets are identical on given keys."""
    assert len(r_eager) == len(r_lazy), (
        f"Row count mismatch: eager={len(r_eager)} lazy={len(r_lazy)}")
    for i, (re_, rl) in enumerate(zip(r_eager, r_lazy)):
        for k in keys:
            ve, vl = re_[k], rl[k]
            if isinstance(ve, Decimal) and isinstance(vl, Decimal):
                assert abs(ve - vl) < Decimal('0.01'), (
                    f"Row {i} key={k}: eager={ve} lazy={vl}")
            else:
                assert ve == vl, (
                    f"Row {i} key={k}: eager={ve} lazy={vl}")


# =====================================================================
#  1. NESTED FORMULA COLUMNS
#     customer.top_product_n_sold depends on customer.top_product_id
# =====================================================================

class TestNestedFormula:
    """Formula column that references another formula column via #THIS."""

    @pytest.mark.xfail(reason='Placeholder leak: #THIS.formula_col inside nested subquery — fix pending')
    def test_top_product_n_sold_uses_top_product_id(self, db):
        """top_product_n_sold WHERE contains #THIS.top_product_id."""
        cols = '$account_name,$top_product_id,$top_product_n_sold'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id', 'top_product_n_sold'])

    @pytest.mark.xfail(reason='Placeholder leak: #THIS.formula_col inside nested subquery — fix pending')
    def test_nested_formula_with_join_mode(self, db):
        """Same as above but with enable_sq_join=True."""
        cols = '$account_name,$top_product_id,$top_product_n_sold'
        kw = dict(columns=cols, order_by='$id', limit=20, enable_sq_join=True)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id', 'top_product_n_sold'])

    @pytest.mark.xfail(reason='Placeholder leak: #THIS.formula_col inside nested subquery — fix pending')
    def test_nested_formula_full_dataset(self, db):
        """All customers — nested formula on full dataset."""
        cols = '$account_name,$top_product_id,$top_product_n_sold'
        kw = dict(columns=cols, order_by='$id')
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id', 'top_product_n_sold'])


# =====================================================================
#  2. DEEP RELATION TRAVERSAL
#     product.top_state navigates @invoice_id.@customer_id.state (2 hops)
#     state.top_customer_id navigates @invoice_id.@customer_id.state
# =====================================================================

class TestDeepRelationTraversal:
    """Formula columns that traverse 2+ relation levels."""

    def test_product_top_state_two_hops(self, db):
        """product.top_state goes through invoice_row → invoice → customer → state."""
        cols = '$code,$description,$top_state'
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.product', **kw).fetch()
        r_lazy = db.query('invc.product', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_state'])

    def test_state_top_customer_two_hops(self, db):
        """state.top_customer_id goes through invoice_row → invoice → customer."""
        cols = '$code,$name,$top_customer_id'
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.state', **kw).fetch()
        r_lazy = db.query('invc.state', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_customer_id'])

    def test_state_top_product_via_invoice_row(self, db):
        """state.top_product_id traverses invoice_row with customer filter."""
        cols = '$code,$top_product_id'
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.state', **kw).fetch()
        r_lazy = db.query('invc.state', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id'])

    def test_state_both_tops_together(self, db):
        """Both top_customer_id AND top_product_id in same query."""
        cols = '$code,$name,$top_customer_id,$top_product_id'
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.state', **kw).fetch()
        r_lazy = db.query('invc.state', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_customer_id', 'top_product_id'])


# =====================================================================
#  3. FORMULA COLUMNS IN WHERE
# =====================================================================

class TestFormulaInWhere:
    """Filtering on formula column values."""

    def test_where_n_invoices_gt_zero(self, db):
        """Only customers with at least one invoice."""
        cols = '$account_name,$n_invoices'
        kw = dict(columns=cols, where='$n_invoices > 0', order_by='$id')
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['n_invoices'])
        assert all(r['n_invoices'] > 0 for r in r_eager)

    def test_where_invoiced_total_gt_threshold(self, db):
        """Customers with invoiced_total above threshold."""
        cols = '$account_name,$invoiced_total'
        kw = dict(columns=cols, where='$invoiced_total > :threshold',
                  threshold=1000, order_by='$invoiced_total DESC')
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['invoiced_total'])

    def test_where_multiple_formulas(self, db):
        """WHERE combining two different formula columns."""
        cols = '$account_name,$n_invoices,$invoiced_total'
        kw = dict(columns=cols,
                  where='$n_invoices > :min_inv AND $invoiced_total > :min_total',
                  min_inv=2, min_total=500, order_by='$id')
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['n_invoices', 'invoiced_total'])

    def test_where_on_product_n_sold(self, db):
        """Products with zero sales."""
        cols = '$code,$description,$n_sold'
        kw = dict(columns=cols, where='$n_sold = 0', order_by='$code')
        r_eager = db.query('invc.product', **kw).fetch()
        r_lazy = db.query('invc.product', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['n_sold'])

    def test_where_formula_and_physical_combined(self, db):
        """WHERE mixing formula column and physical column."""
        cols = '$account_name,$state,$n_invoices'
        kw = dict(columns=cols,
                  where='$n_invoices > 0 AND $state IS NOT NULL',
                  order_by='$id')
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['n_invoices', 'state'])


# =====================================================================
#  4. FORMULA COLUMNS IN ORDER BY
# =====================================================================

class TestFormulaInOrderBy:
    """Ordering by formula column values."""

    def test_order_by_n_invoices_desc(self, db):
        cols = '$account_name,$n_invoices'
        kw = dict(columns=cols, order_by='$n_invoices DESC', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['account_name', 'n_invoices'])

    def test_order_by_invoiced_total_asc(self, db):
        cols = '$account_name,$invoiced_total'
        kw = dict(columns=cols, order_by='$invoiced_total ASC', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['account_name', 'invoiced_total'])

    def test_order_by_formula_with_where(self, db):
        """ORDER BY formula + WHERE on same formula."""
        cols = '$account_name,$n_invoices'
        kw = dict(columns=cols, where='$n_invoices > 0',
                  order_by='$n_invoices DESC', limit=10)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['account_name', 'n_invoices'])

    def test_order_by_product_total_sold(self, db):
        cols = '$description,$total_sold'
        kw = dict(columns=cols, order_by='$total_sold DESC', limit=10)
        r_eager = db.query('invc.product', **kw).fetch()
        r_lazy = db.query('invc.product', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['description', 'total_sold'])


# =====================================================================
#  5. FORMULA WITH LIMIT 1 + ORDER BY (top-N pattern)
# =====================================================================

class TestTopNFormulas:
    """Formula columns using GROUP BY + ORDER BY + LIMIT 1."""

    def test_customer_top_product_id(self, db):
        """customer.top_product_id: best-selling product per customer."""
        cols = '$account_name,$top_product_id'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id'])

    def test_customer_last_invoice_id(self, db):
        """customer.last_invoice_id: most recent invoice per customer."""
        cols = '$account_name,$last_invoice_id'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['last_invoice_id'])

    def test_product_top_customer_id(self, db):
        """product.top_customer_id: best customer per product."""
        cols = '$code,$top_customer_id'
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.product', **kw).fetch()
        r_lazy = db.query('invc.product', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_customer_id'])

    @pytest.mark.xfail(reason='Placeholder leak: top_product_n_sold references #THIS.top_product_id')
    def test_all_top_n_formulas_on_customer(self, db):
        """All top-N formulas together on customer."""
        cols = '$account_name,$top_product_id,$top_product_n_sold,$last_invoice_id'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['top_product_id', 'top_product_n_sold', 'last_invoice_id'])


# =====================================================================
#  6. FORMULA RESULT AS RELATION STARTING POINT
#     Navigate FROM a formula column result INTO the related table
# =====================================================================

class TestFormulaAsRelationBase:
    """Use formula column result to navigate further relations."""

    def test_customer_top_product_description(self, db):
        """Navigate customer → @top_product_id.description."""
        cols = '$account_name,$top_product_id,@top_product_id.description'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id', '_top_product_id_description'])

    def test_customer_top_product_unit_price(self, db):
        """Navigate customer → @top_product_id.unit_price."""
        cols = '$account_name,$top_product_id,@top_product_id.unit_price'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id', '_top_product_id_unit_price'])

    def test_customer_top_product_code(self, db):
        """Navigate customer → @top_product_id.code."""
        cols = '$account_name,$top_product_id,@top_product_id.code'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id', '_top_product_id_code'])

    def test_state_top_customer_account_name(self, db):
        """Navigate state → @top_customer_id.account_name."""
        cols = '$code,$top_customer_id,@top_customer_id.account_name'
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.state', **kw).fetch()
        r_lazy = db.query('invc.state', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_customer_id', '_top_customer_id_account_name'])

    def test_state_top_product_description(self, db):
        """Navigate state → @top_product_id.description."""
        cols = '$code,$top_product_id,@top_product_id.description'
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.state', **kw).fetch()
        r_lazy = db.query('invc.state', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['top_product_id', '_top_product_id_description'])


# =====================================================================
#  7. TEMPORAL FILTERS (EXTRACT-based formula columns)
# =====================================================================

class TestTemporalFormulas:
    """Formula columns with EXTRACT(YEAR FROM ...) filters."""

    def test_invoiced_per_year(self, db):
        """All yearly totals together."""
        cols = '$account_name,$invoiced_2022,$invoiced_2023,$invoiced_2024,$invoiced_2025'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['invoiced_2022', 'invoiced_2023', 'invoiced_2024', 'invoiced_2025'])

    def test_n_invoices_per_year(self, db):
        """All yearly counts together."""
        cols = '$account_name,$n_invoices_2022,$n_invoices_2023,$n_invoices_2024,$n_invoices_2025'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['n_invoices_2022', 'n_invoices_2023', 'n_invoices_2024', 'n_invoices_2025'])

    def test_temporal_in_where(self, db):
        """Filter on temporal formula column."""
        cols = '$account_name,$invoiced_2024'
        kw = dict(columns=cols, where='$invoiced_2024 > :min_total',
                  min_total=0, order_by='$invoiced_2024 DESC')
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['invoiced_2024'])

    def test_temporal_mixed_with_totals(self, db):
        """Yearly formulas together with global totals."""
        cols = '$account_name,$n_invoices,$invoiced_total,$invoiced_2024,$n_invoices_2024'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['n_invoices', 'invoiced_total', 'invoiced_2024', 'n_invoices_2024'])


# =====================================================================
#  8. KITCHEN SINK — maximum complexity combinations
# =====================================================================

class TestKitchenSink:
    """Extreme combinations of all features."""

    def test_all_aggregations_together(self, db):
        """Every aggregation formula on customer in one query."""
        cols = ('$account_name,$n_invoices,$invoiced_total,$last_invoice_date,'
                '$avg_invoice_total,$max_invoice,$min_invoice')
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['n_invoices', 'invoiced_total', 'last_invoice_date',
                       'avg_invoice_total', 'max_invoice', 'min_invoice'])

    @pytest.mark.xfail(reason='Placeholder leak: top_product_n_sold references #THIS.top_product_id')
    def test_aggregations_plus_top_n_plus_temporal(self, db):
        """Aggregations + top-N + temporal — maximum formula count."""
        cols = ('$account_name,$n_invoices,$invoiced_total,$top_product_id,'
                '$top_product_n_sold,$last_invoice_id,$invoiced_2024,$n_invoices_2024')
        kw = dict(columns=cols, order_by='$id', limit=15)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['n_invoices', 'invoiced_total', 'top_product_id',
                       'top_product_n_sold', 'last_invoice_id',
                       'invoiced_2024', 'n_invoices_2024'])

    def test_formula_where_order_limit_combined(self, db):
        """WHERE + ORDER BY + LIMIT all on formula columns."""
        cols = '$account_name,$n_invoices,$invoiced_total'
        kw = dict(columns=cols,
                  where='$n_invoices > :min_inv AND $invoiced_total > :min_total',
                  min_inv=1, min_total=100,
                  order_by='$invoiced_total DESC',
                  limit=10)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['account_name', 'n_invoices', 'invoiced_total'])

    def test_relation_plus_formula_on_related_table(self, db):
        """Invoice with physical relation to customer AND formula on invoice."""
        cols = '$inv_number,$date,$total,@customer_id.account_name,@customer_id.state,$n_rows,$row_total'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.invoice', **kw).fetch()
        r_lazy = db.query('invc.invoice', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['inv_number', 'total', '_customer_id_account_name',
                       '_customer_id_state', 'n_rows', 'row_total'])

    def test_product_all_formulas_with_deep_traversal(self, db):
        """All product formulas including 2-hop top_state."""
        cols = '$code,$description,$n_sold,$total_sold,$top_customer_id,$top_state'
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.product', **kw).fetch()
        r_lazy = db.query('invc.product', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['n_sold', 'total_sold', 'top_customer_id', 'top_state'])

    def test_formula_navigation_then_filter(self, db):
        """Navigate formula relation + filter on result."""
        cols = '$account_name,$top_product_id,@top_product_id.description,@top_product_id.unit_price'
        kw = dict(columns=cols,
                  where='$top_product_id IS NOT NULL',
                  order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['top_product_id', '_top_product_id_description', '_top_product_id_unit_price'])

    def test_state_full_torture(self, db):
        """State: both top formulas + navigation into related tables."""
        cols = ('$code,$name,$top_customer_id,@top_customer_id.account_name,'
                '$top_product_id,@top_product_id.description')
        kw = dict(columns=cols, order_by='$code')
        r_eager = db.query('invc.state', **kw).fetch()
        r_lazy = db.query('invc.state', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['top_customer_id', '_top_customer_id_account_name',
                       'top_product_id', '_top_product_id_description'])


# =====================================================================
#  9. JOIN MODE TORTURE (enable_sq_join=True combinations)
# =====================================================================

class TestJoinModeTorture:
    """All the above but with subquery-as-join enabled."""

    def test_all_aggregations_join_mode(self, db):
        cols = ('$account_name,$n_invoices,$invoiced_total,$last_invoice_date,'
                '$avg_invoice_total,$max_invoice,$min_invoice')
        kw = dict(columns=cols, order_by='$id', limit=20, enable_sq_join=True)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['n_invoices', 'invoiced_total', 'last_invoice_date',
                       'avg_invoice_total', 'max_invoice', 'min_invoice'])

    def test_temporal_join_mode(self, db):
        cols = '$account_name,$invoiced_2023,$invoiced_2024,$n_invoices_2023,$n_invoices_2024'
        kw = dict(columns=cols, order_by='$id', limit=20, enable_sq_join=True)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['invoiced_2023', 'invoiced_2024', 'n_invoices_2023', 'n_invoices_2024'])

    def test_product_all_join_mode(self, db):
        cols = '$code,$n_sold,$total_sold,$top_customer_id,$top_state'
        kw = dict(columns=cols, order_by='$code', enable_sq_join=True)
        r_eager = db.query('invc.product', **kw).fetch()
        r_lazy = db.query('invc.product', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['n_sold', 'total_sold', 'top_customer_id', 'top_state'])

    def test_where_order_limit_join_mode(self, db):
        cols = '$account_name,$n_invoices,$invoiced_total'
        kw = dict(columns=cols,
                  where='$n_invoices > :min_inv',
                  min_inv=1,
                  order_by='$invoiced_total DESC',
                  limit=10,
                  enable_sq_join=True)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['account_name', 'n_invoices', 'invoiced_total'])


# =====================================================================
#  10. DEEP CROSS-JOIN — both sides traverse relations
#      remote: invoice_row → product → product_type → production_state
#      local:  customer → postcode → state
# =====================================================================

class TestDeepCrossJoin:
    """Formula where BOTH sides of the correlation traverse relations."""

    def test_sales_from_local_state_basic(self, db):
        """sales_from_local_state: 3-hop remote + 2-hop local via #THIS."""
        cols = '$account_name,$state,$sales_from_local_state'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['sales_from_local_state'])

    def test_sales_from_local_state_full_dataset(self, db):
        """All customers — deep cross-join on full dataset."""
        cols = '$account_name,$sales_from_local_state'
        kw = dict(columns=cols, order_by='$id')
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['sales_from_local_state'])

    def test_sales_from_local_state_with_other_formulas(self, db):
        """Deep cross-join + other formula columns in same query."""
        cols = '$account_name,$n_invoices,$invoiced_total,$sales_from_local_state'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['n_invoices', 'invoiced_total', 'sales_from_local_state'])

    def test_sales_from_local_state_in_where(self, db):
        """Filter on deep cross-join formula."""
        cols = '$account_name,$sales_from_local_state'
        kw = dict(columns=cols,
                  where='$sales_from_local_state > :min_sales',
                  min_sales=100000,
                  order_by='$sales_from_local_state DESC')
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['sales_from_local_state'])
        assert all(r['sales_from_local_state'] > 100000 for r in r_eager)

    def test_sales_from_local_state_order_by(self, db):
        """Order by deep cross-join formula."""
        cols = '$account_name,$sales_from_local_state'
        kw = dict(columns=cols,
                  order_by='$sales_from_local_state DESC',
                  limit=10)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['account_name', 'sales_from_local_state'])

    def test_sales_from_local_state_with_postcode_navigation(self, db):
        """Deep cross-join + explicit navigation to postcode state."""
        cols = '$account_name,$state,@postcode_id.state,$sales_from_local_state'
        kw = dict(columns=cols, order_by='$id', limit=20)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy,
                      ['state', '_postcode_id_state', 'sales_from_local_state'])

    @pytest.mark.xfail(reason='Requires LATERAL JOIN: subquery references outer table via #THIS.@relation path')
    def test_sales_from_local_state_join_mode(self, db):
        """Deep cross-join with enable_sq_join=True — needs LATERAL."""
        cols = '$account_name,$sales_from_local_state'
        kw = dict(columns=cols, order_by='$id', limit=20, enable_sq_join=True)
        r_eager = db.query('invc.customer', **kw).fetch()
        r_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).fetch()
        _compare_rows(r_eager, r_lazy, ['sales_from_local_state'])


# =====================================================================
#  11. SQL TEXT VERIFICATION — no placeholders leak
# =====================================================================

class TestNoPlaceholderLeak:
    """Verify that no __sq_ placeholder ever appears in final SQL."""

    def _assert_no_placeholder(self, db, table, **kw):
        q = db.query(table, enable_lazy_subquery=True, **kw)
        sql = q.sqltext
        assert '__sq_' not in sql, f"Placeholder leak in SQL:\n{sql}"

    def test_customer_simple(self, db):
        self._assert_no_placeholder(db, 'invc.customer',
            columns='$account_name,$n_invoices', where='$id=:id', id='x')

    @pytest.mark.xfail(reason='Placeholder leak: top_product_n_sold references #THIS.top_product_id')
    def test_customer_all_formulas(self, db):
        self._assert_no_placeholder(db, 'invc.customer',
            columns=('$account_name,$n_invoices,$invoiced_total,$top_product_id,'
                     '$top_product_n_sold,$last_invoice_id,$invoiced_2024'),
            where='$id=:id', id='x')

    def test_product_deep_traversal(self, db):
        self._assert_no_placeholder(db, 'invc.product',
            columns='$code,$n_sold,$total_sold,$top_customer_id,$top_state',
            where='$id=:id', id='x')

    def test_state_with_navigation(self, db):
        self._assert_no_placeholder(db, 'invc.state',
            columns='$code,$top_customer_id,@top_customer_id.account_name,$top_product_id',
            where='$code=:code', code='x')

    def test_invoice_with_formulas(self, db):
        self._assert_no_placeholder(db, 'invc.invoice',
            columns='$inv_number,$n_rows,$row_total,@customer_id.account_name',
            where='$id=:id', id='x')

    def test_join_mode_no_placeholder(self, db):
        self._assert_no_placeholder(db, 'invc.customer',
            columns='$account_name,$n_invoices,$invoiced_total',
            where='$id=:id', id='x', enable_sq_join=True)

    def test_deep_cross_join_no_placeholder(self, db):
        self._assert_no_placeholder(db, 'invc.customer',
            columns='$account_name,$sales_from_local_state',
            where='$id=:id', id='x')
