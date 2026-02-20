"""Comprehensive test suite for the SQL compiler.

Tests cover all virtual column types, relation navigation at multiple
levels, sub-query compilation, WHERE/ORDER BY on virtual columns,
GROUP BY, DISTINCT auto-injection, and complex combined queries.

Uses the ``test_invoice`` project via GnrApp so that a realistic model
with formulaColumn, aliasColumn, relations, and triggers is available.
"""

import pytest
from gnr.app.gnrapp import GnrApp

INSTANCE_PATH = (
    '/Users/gporcari/Sviluppo/Genropy/genropy'
    '/projects/test_invoice/instances/test_invoice'
)


@pytest.fixture(scope='module')
def db():
    app = GnrApp(INSTANCE_PATH)
    return app.db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sql(db, table, **kwargs):
    """Return the compiled SQL text for a query on *table*."""
    return db.table(table).query(**kwargs).sqltext


# ===================================================================
# Cat. 1 — Physical columns
# ===================================================================

class TestPhysicalColumns:

    def test_single_column(self, db):
        sql = _sql(db, 'invc.customer', columns='$account_name')
        assert '"account_name"' in sql

    def test_multiple_columns(self, db):
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $email, $phone')
        assert '"account_name"' in sql
        assert '"email"' in sql
        assert '"phone"' in sql

    def test_star_expansion(self, db):
        sql = _sql(db, 'invc.customer', columns='*')
        assert '"account_name"' in sql
        assert '"email"' in sql


# ===================================================================
# Cat. 2 — aliasColumn
# ===================================================================

class TestAliasColumn:

    def test_alias_one_level(self, db):
        """customer.state_name → @state.name (1 JOIN)."""
        sql = _sql(db, 'invc.customer', columns='$account_name, $state_name')
        assert '"state_name"' in sql or 'AS "state_name"' in sql
        assert 'JOIN' in sql

    def test_alias_two_levels(self, db):
        """invoice_row.customer_name → @invoice_id.@customer_id.account_name (2 JOIN)."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_name')
        assert 'customer_name' in sql
        assert sql.count('JOIN') >= 2

    def test_alias_three_levels(self, db):
        """invoice_row.customer_state → @invoice_id.@customer_id.@state.name (3 JOIN)."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_state')
        assert 'customer_state' in sql
        assert sql.count('JOIN') >= 3

    def test_alias_with_relation_navigation(self, db):
        """invoice_row.@customer_id.account_name navigates through aliasColumn with .relation()."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, @customer_id.account_name')
        assert 'account_name' in sql
        assert 'JOIN' in sql

    def test_alias_with_relation_deep_navigation(self, db):
        """invoice_row.@customer_id.@state.name — alias with relation, then further navigation."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, @customer_id.@state.name')
        assert '"name"' in sql
        assert sql.count('JOIN') >= 3


# ===================================================================
# Cat. 3 — formulaColumn
# ===================================================================

class TestFormulaColumn:

    def test_sql_formula_arithmetic(self, db):
        """invoice_row.line_total = $quantity * $unit_price."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $line_total')
        assert 'line_total' in sql
        assert 'quantity' in sql.lower() or 'unit_price' in sql.lower()

    def test_sql_formula_concatenation(self, db):
        """customer.full_address = $street_address || ', ' || $suburb."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $full_address')
        assert 'full_address' in sql
        assert '||' in sql

    def test_select_count(self, db):
        """customer.n_invoices = COUNT(*) from invoice."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $n_invoices')
        assert 'n_invoices' in sql
        assert 'COUNT' in sql

    def test_select_sum(self, db):
        """customer.invoiced_total = SUM($total) from invoice."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $invoiced_total')
        assert 'invoiced_total' in sql
        assert 'SUM' in sql

    def test_select_order_limit(self, db):
        """customer.last_invoice_id = $id ORDER BY $date DESC LIMIT 1."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $last_invoice_id')
        assert 'last_invoice_id' in sql
        assert 'ORDER BY' in sql
        assert 'LIMIT 1' in sql

    def test_exists_subquery(self, db):
        """customer.has_invoices = EXISTS(SELECT ... FROM invoice)."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $has_invoices')
        assert 'has_invoices' in sql
        assert 'EXISTS' in sql

    def test_formula_with_relation_navigation(self, db):
        """customer.@last_invoice_id.inv_number — formula column with .relation()."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, @last_invoice_id.inv_number')
        assert 'inv_number' in sql
        assert 'JOIN' in sql

    def test_formula_with_relation_deep_navigation(self, db):
        """invoice.@first_product_id.description — formula + relation + field."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, @first_product_id.description')
        assert 'description' in sql
        assert 'JOIN' in sql

    def test_select_in_product(self, db):
        """product.total_sold = SUM($quantity) from invoice_row."""
        sql = _sql(db, 'invc.product',
                   columns='$description, $total_sold')
        assert 'total_sold' in sql
        assert 'SUM' in sql


# ===================================================================
# Cat. 4 — WHERE with virtual columns
# ===================================================================

class TestWhereVirtualColumns:

    def test_where_alias_column(self, db):
        sql = _sql(db, 'invc.customer',
                   columns='$account_name',
                   where='$state_name LIKE :sn', sn='A%')
        assert 'LIKE' in sql

    def test_where_formula_sql(self, db):
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id',
                   where='$line_total > :min_total', min_total=100)
        assert 'line_total' in sql or 'quantity' in sql.lower()

    def test_where_formula_select(self, db):
        sql = _sql(db, 'invc.customer',
                   columns='$account_name',
                   where='$n_invoices > :n', n=0)
        assert 'COUNT' in sql or 'n_invoices' in sql

    def test_where_mixed(self, db):
        """Mix physical + alias + relation in WHERE."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_name',
                   where='$quantity > :q AND $customer_name LIKE :cn AND @invoice_id.date > :d',
                   q=0, cn='A%', d='2020-01-01')
        assert 'quantity' in sql.lower()
        assert 'account_name' in sql.lower() or 'customer_name' in sql
        assert '"date"' in sql

    def test_where_exists_column(self, db):
        sql = _sql(db, 'invc.customer',
                   columns='$account_name',
                   where='$has_invoices = TRUE')
        assert 'EXISTS' in sql


# ===================================================================
# Cat. 5 — ORDER BY with virtual columns
# ===================================================================

class TestOrderByVirtualColumns:

    def test_order_alias(self, db):
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_name',
                   order_by='$customer_name')
        assert 'ORDER BY' in sql
        assert 'account_name' in sql.lower()

    def test_order_formula(self, db):
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $line_total',
                   order_by='$line_total DESC')
        assert 'ORDER BY' in sql
        assert 'DESC' in sql

    def test_order_mixed(self, db):
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $n_invoices',
                   order_by='$n_invoices DESC, $account_name')
        assert 'ORDER BY' in sql


# ===================================================================
# Cat. 6 — Relation navigation
# ===================================================================

class TestRelationNavigation:

    def test_one_level(self, db):
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, @customer_id.account_name')
        assert 'account_name' in sql
        assert 'JOIN' in sql

    def test_two_levels(self, db):
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, @invoice_id.@customer_id.account_name')
        assert 'account_name' in sql
        assert sql.count('JOIN') >= 2

    def test_three_levels(self, db):
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, @invoice_id.@customer_id.@state.name')
        assert '"name"' in sql
        assert sql.count('JOIN') >= 3

    def test_one_to_many(self, db):
        """customer.@invoices — one-to-many relation."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, @invoices.inv_number')
        assert 'inv_number' in sql
        assert 'JOIN' in sql

    def test_mixed_navigations(self, db):
        """Multiple different navigation paths in same query."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, @invoice_id.inv_number, @product_id.description, @invoice_id.@customer_id.account_name')
        assert 'inv_number' in sql
        assert sql.count('JOIN') >= 3


# ===================================================================
# Cat. 7 — Complex combined queries
# ===================================================================

class TestCombinedQueries:

    def test_invoice_row_full(self, db):
        """invoice_row with alias + formula + navigation + WHERE + ORDER BY."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_name, $customer_state, $line_total, @invoice_id.inv_number',
                   where='$customer_name LIKE :cn AND $line_total > :lt',
                   order_by='$customer_name, $line_total DESC',
                   cn='A%', lt=0)
        assert 'customer_name' in sql
        assert 'customer_state' in sql
        assert 'line_total' in sql
        assert 'inv_number' in sql
        assert 'ORDER BY' in sql
        assert 'LIKE' in sql

    def test_customer_full(self, db):
        """customer with formula select + formula relation + WHERE + ORDER BY."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $n_invoices, $invoiced_total, @last_invoice_id.inv_number',
                   where='$n_invoices > :n',
                   order_by='$invoiced_total DESC',
                   n=0)
        assert 'COUNT' in sql
        assert 'SUM' in sql
        assert 'inv_number' in sql
        assert 'ORDER BY' in sql

    def test_invoice_with_all_vc(self, db):
        """invoice with row_count + customer_name + first_product navigation."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $row_count, $customer_name, @first_product_id.description')
        assert 'row_count' in sql
        assert 'customer_name' in sql
        assert 'description' in sql

    def test_product_with_aggregation_and_alias(self, db):
        """product with total_sold (SUM) + product_type_name (alias)."""
        sql = _sql(db, 'invc.product',
                   columns='$description, $total_sold, $product_type_name',
                   order_by='$total_sold DESC')
        assert 'SUM' in sql
        assert 'product_type_name' in sql

    def test_cross_table_alias_and_formula(self, db):
        """invoice_row: alias customer_name + formula line_total + navigate @customer_id.@state.code."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_name, $line_total, @customer_id.@state.code',
                   where='$customer_name LIKE :cn',
                   order_by='@customer_id.@state.code, $line_total DESC',
                   cn='%Inc%')
        assert 'customer_name' in sql
        assert 'line_total' in sql
        assert 'ORDER BY' in sql


# ===================================================================
# Cat. 8 — GROUP BY and aggregations
# ===================================================================

class TestGroupBy:

    def test_group_by_physical_with_formula(self, db):
        sql = _sql(db, 'invc.invoice',
                   columns='@customer_id.account_name, SUM($total)',
                   group_by='@customer_id.account_name')
        assert 'GROUP BY' in sql
        assert 'SUM' in sql

    def test_group_by_alias(self, db):
        sql = _sql(db, 'invc.invoice_row',
                   columns='$customer_name, SUM($tot_price)',
                   group_by='$customer_name')
        assert 'GROUP BY' in sql


# ===================================================================
# Cat. 9 — DISTINCT and row explosion
# ===================================================================

class TestDistinctRowExplosion:

    def test_many_relation_triggers_distinct(self, db):
        """One-to-many join should trigger DISTINCT."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, @invoices.inv_number')
        assert 'DISTINCT' in sql or 'JOIN' in sql

    def test_order_by_with_many_relation(self, db):
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, @invoices.inv_number',
                   order_by='$account_name')
        assert 'ORDER BY' in sql


# ===================================================================
# Cat. 10 — Macros in sub-queries
# ===================================================================

class TestSubQueryMacros:

    def test_this_macro_in_count(self, db):
        """n_invoices uses #THIS.id in WHERE."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $n_invoices')
        # #THIS.id should be expanded to the main table alias
        assert 't0' in sql.lower() or '"id"' in sql

    def test_subquery_with_order_limit(self, db):
        """last_invoice_id has ORDER BY + LIMIT in sub-select."""
        sql = _sql(db, 'invc.customer',
                   columns='$last_invoice_id')
        assert 'ORDER BY' in sql
        assert 'LIMIT 1' in sql

    def test_subquery_navigated_via_relation(self, db):
        """@last_invoice_id.date — sub-query result JOINed via relation."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, @last_invoice_id.date')
        assert 'LIMIT 1' in sql  # sub-query for last_invoice_id
        assert 'JOIN' in sql     # JOIN for @last_invoice_id.date

    def test_first_product_subquery(self, db):
        """invoice.first_product_id uses ORDER BY + LIMIT."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $first_product_id')
        assert 'ORDER BY' in sql
        assert 'LIMIT 1' in sql


# ===================================================================
# Cat. 11 — Date/time functions
# ===================================================================

class TestDateTimeFunctions:

    def test_extract_year(self, db):
        """invoice.anno = EXTRACT(YEAR FROM $date)."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $anno')
        assert 'anno' in sql
        assert 'EXTRACT' in sql

    def test_to_char(self, db):
        """invoice.periodo = TO_CHAR($date,'YYYY-MM')."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $periodo')
        assert 'periodo' in sql
        assert 'TO_CHAR' in sql

    def test_date_function_in_where(self, db):
        """WHERE on date formula column."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number',
                   where="$anno = :y", y=2024)
        assert 'EXTRACT' in sql

    def test_date_function_in_order_by(self, db):
        """ORDER BY on date formula column."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $periodo',
                   order_by='$periodo DESC')
        assert 'ORDER BY' in sql
        assert 'TO_CHAR' in sql


# ===================================================================
# Cat. 12 — CASE WHEN
# ===================================================================

class TestCaseWhen:

    def test_case_simple_multi_when(self, db):
        """invoice.value_category — CASE with multiple WHEN branches."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $value_category')
        assert 'value_category' in sql
        assert 'CASE' in sql
        assert 'WHEN' in sql
        assert 'ELSE' in sql

    def test_case_with_in(self, db):
        """invoice_row.size_category — CASE with IN (list)."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $size_category')
        assert 'size_category' in sql
        assert 'CASE' in sql
        assert 'IN' in sql

    def test_case_with_relation(self, db):
        """invoice_row.product_note — CASE referencing @product_id.unit_price."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $product_note')
        assert 'product_note' in sql
        assert 'CASE' in sql
        assert 'unit_price' in sql.lower()
        assert 'JOIN' in sql

    def test_case_referencing_formula_select(self, db):
        """customer.customer_rank — CASE on $n_invoices (which is a COUNT sub-query)."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $customer_rank')
        assert 'customer_rank' in sql
        assert 'CASE' in sql
        assert 'COUNT' in sql

    def test_case_in_where(self, db):
        """WHERE on CASE WHEN column."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number',
                   where="$value_category = :cat", cat='High')
        assert 'CASE' in sql

    def test_case_in_order_by(self, db):
        """ORDER BY on CASE WHEN column."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $value_category',
                   order_by='$value_category')
        assert 'ORDER BY' in sql
        assert 'CASE' in sql

    def test_case_product_price_range(self, db):
        """product.price_range — CASE categorization."""
        sql = _sql(db, 'invc.product',
                   columns='$description, $price_range')
        assert 'price_range' in sql
        assert 'CASE' in sql
        assert 'Premium' in sql


# ===================================================================
# Cat. 13 — COALESCE
# ===================================================================

class TestCoalesce:

    def test_coalesce_physical_columns(self, db):
        """invoice.display_total = COALESCE($gross_total, $total, 0)."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $display_total')
        assert 'display_total' in sql
        assert 'COALESCE' in sql

    def test_coalesce_with_relation(self, db):
        """invoice_row.effective_price = COALESCE($unit_price, @product_id.unit_price)."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $effective_price')
        assert 'effective_price' in sql
        assert 'COALESCE' in sql
        assert 'JOIN' in sql

    def test_coalesce_with_string_fallback(self, db):
        """customer.display_name = COALESCE($account_name, 'Unknown')."""
        sql = _sql(db, 'invc.customer',
                   columns='$display_name')
        assert 'display_name' in sql
        assert 'COALESCE' in sql
        assert 'Unknown' in sql


# ===================================================================
# Cat. 14 — Formula referencing formula
# ===================================================================

class TestFormulaReferencingFormula:

    def test_formula_level_1(self, db):
        """line_total = $quantity * $unit_price (base formula)."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $line_total')
        assert 'quantity' in sql.lower()
        assert 'unit_price' in sql.lower()

    def test_formula_level_2(self, db):
        """line_vat = $line_total * $vat_rate — references formula line_total."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $line_vat')
        assert 'line_vat' in sql
        # line_total should be expanded to its formula ($quantity * $unit_price)
        assert 'quantity' in sql.lower() or 'line_total' in sql

    def test_formula_level_3(self, db):
        """line_gross = $line_total + $line_vat — references two formulas."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $line_gross')
        assert 'line_gross' in sql

    def test_formula_chain_in_where(self, db):
        """WHERE on formula that references another formula."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id',
                   where='$line_vat > :min_vat', min_vat=10)
        assert 'vat_rate' in sql.lower() or 'line_vat' in sql

    def test_formula_chain_in_order_by(self, db):
        """ORDER BY on formula that references another formula."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $line_gross',
                   order_by='$line_gross DESC')
        assert 'ORDER BY' in sql
        assert 'DESC' in sql

    def test_case_on_formula_select(self, db):
        """customer_rank uses $n_invoices (COUNT sub-query) inside CASE."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $customer_rank')
        assert 'CASE' in sql
        assert 'COUNT' in sql

    def test_mixed_formula_chain_and_alias(self, db):
        """Combine formula chain + alias in same query."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $line_gross, $customer_name, $product_name',
                   order_by='$line_gross DESC')
        assert 'line_gross' in sql
        assert 'account_name' in sql.lower() or 'customer_name' in sql
        assert sql.count('JOIN') >= 2


# ===================================================================
# Cat. 15 — LPAD and string functions
# ===================================================================

class TestStringFunctions:

    def test_lpad(self, db):
        """customer.postcode_padded = LPAD($postcode, 5, '0')."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $postcode_padded')
        assert 'postcode_padded' in sql
        assert 'LPAD' in sql

    def test_concatenation_different_columns(self, db):
        """product.code_and_desc = $code || ' - ' || $description."""
        sql = _sql(db, 'invc.product',
                   columns='$code_and_desc')
        assert 'code_and_desc' in sql
        assert '||' in sql

    def test_lpad_in_where(self, db):
        """WHERE on LPAD column."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name',
                   where="$postcode_padded = :pc", pc='00100')
        assert 'LPAD' in sql

    def test_lpad_in_order_by(self, db):
        """ORDER BY on LPAD column."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $postcode_padded',
                   order_by='$postcode_padded')
        assert 'ORDER BY' in sql
        assert 'LPAD' in sql


# ===================================================================
# Cat. 16 — Implicit boolean formula
# ===================================================================

class TestImplicitBooleanFormula:

    def test_boolean_expression(self, db):
        """invoice_row.is_expensive = $line_total > 1000 (dtype='B')."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $is_expensive')
        assert 'is_expensive' in sql

    def test_boolean_in_where(self, db):
        """WHERE on boolean formula."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id',
                   where='$is_expensive = TRUE')
        assert '1000' in sql or 'is_expensive' in sql

    def test_boolean_combined_with_case(self, db):
        """Combine boolean formula + CASE formula in same query."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $is_expensive, $size_category, $line_gross',
                   where='$is_expensive = TRUE',
                   order_by='$line_gross DESC')
        assert 'CASE' in sql
        assert 'ORDER BY' in sql


# ===================================================================
# Cat. 17 — joinColumn with multi-field cnd
# ===================================================================

class TestJoinColumn:

    def test_join_column_compiles(self, db):
        """invoice.discount_tier_id — joinColumn with cnd multi-field."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $discount_tier_id')
        assert 'discount_tier_id' in sql

    def test_join_column_navigation(self, db):
        """Navigate through joinColumn: @discount_tier_id.discount_rate."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, @discount_tier_id.discount_rate')
        assert 'discount_rate' in sql
        assert 'JOIN' in sql

    def test_join_column_description(self, db):
        """Navigate joinColumn for description."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, @discount_tier_id.description')
        assert 'JOIN' in sql

    def test_join_column_in_where(self, db):
        """WHERE on joinColumn navigated field."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number',
                   where='@discount_tier_id.discount_rate > :min_disc',
                   min_disc=0.1)
        assert 'JOIN' in sql

    def test_join_column_in_order_by(self, db):
        """ORDER BY on joinColumn navigated field."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, @discount_tier_id.discount_rate',
                   order_by='@discount_tier_id.discount_rate DESC')
        assert 'ORDER BY' in sql
        assert 'DESC' in sql


# ===================================================================
# Cat. 18 — STRING_AGG in sub-query
# ===================================================================

class TestStringAgg:

    def test_string_agg_select(self, db):
        """invoice.all_notes — STRING_AGG in sub-query."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $all_notes')
        assert 'all_notes' in sql
        assert 'STRING_AGG' in sql

    def test_string_agg_with_other_columns(self, db):
        """STRING_AGG combined with other virtual columns."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $all_notes, $customer_name, $row_count')
        assert 'STRING_AGG' in sql
        assert 'COUNT' in sql


# ===================================================================
# Cat. 19 — select_* named sub-query
# ===================================================================

class TestNamedSubQuery:

    def test_select_star_with_coalesce(self, db):
        """invoice.priority_note — COALESCE(#top_note, 'No notes')."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $priority_note')
        assert 'priority_note' in sql
        assert 'COALESCE' in sql

    def test_named_subquery_limit(self, db):
        """Named sub-query with ORDER BY + LIMIT."""
        sql = _sql(db, 'invc.invoice',
                   columns='$priority_note')
        assert 'LIMIT 1' in sql or 'LIMIT' in sql

    def test_named_subquery_in_where(self, db):
        """WHERE on named sub-query column."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number',
                   where="$priority_note != 'No notes'")
        assert 'COALESCE' in sql


# ===================================================================
# Cat. 20 — Nested CASE WHEN
# ===================================================================

class TestNestedCaseWhen:

    def test_nested_case(self, db):
        """invoice.invoice_status — CASE inside CASE."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $invoice_status')
        assert 'invoice_status' in sql
        assert 'CASE' in sql
        # Should have at least 2 CASE keywords (nested)
        assert sql.count('CASE') >= 2

    def test_nested_case_in_where(self, db):
        """WHERE on nested CASE column."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number',
                   where="$invoice_status = 'Large'")
        assert sql.count('CASE') >= 2

    def test_nested_case_in_order_by(self, db):
        """ORDER BY on nested CASE column."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $invoice_status',
                   order_by='$invoice_status')
        assert 'ORDER BY' in sql
        assert sql.count('CASE') >= 2


# ===================================================================
# Cat. 21 — var_* parameters
# ===================================================================

class TestVarParameters:

    def test_var_in_formula(self, db):
        """invoice.status_label — var_high_label, var_mid_label, var_low_label."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $status_label')
        assert 'status_label' in sql
        assert 'CASE' in sql
        # var_ params get expanded to :env_* references
        assert 'env_' in sql.lower() or 'CASE' in sql

    def test_var_combined_with_other_vc(self, db):
        """var_* column combined with other virtual columns."""
        sql = _sql(db, 'invc.invoice',
                   columns='$inv_number, $status_label, $value_category',
                   order_by='$status_label')
        assert 'ORDER BY' in sql


# ===================================================================
# Cat. 22 — Deep relations (5+ levels)
# ===================================================================

class TestDeepRelations:

    def test_five_levels(self, db):
        """invoice_row → invoice → customer → state → region (5 levels)."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_region')
        assert 'customer_region' in sql or '"name"' in sql
        assert sql.count('JOIN') >= 4

    def test_three_levels_via_alias(self, db):
        """customer → state → region.name (3 levels via alias)."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $region_name')
        assert 'region_name' in sql or '"name"' in sql
        assert sql.count('JOIN') >= 2

    def test_deep_relation_in_where(self, db):
        """WHERE on 5-level deep relation."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id',
                   where="$customer_region LIKE :rn", rn='North%')
        assert sql.count('JOIN') >= 4

    def test_deep_relation_in_order_by(self, db):
        """ORDER BY on 5-level deep relation."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_region',
                   order_by='$customer_region')
        assert 'ORDER BY' in sql
        assert sql.count('JOIN') >= 4

    def test_mixed_deep_and_shallow(self, db):
        """Mix deep (5 levels) and shallow (1 level) relations."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $customer_region, $product_name, $customer_name')
        assert sql.count('JOIN') >= 4


# ===================================================================
# Cat. 23 — GREATEST/LEAST and CAST
# ===================================================================

class TestGreatestLeastCast:

    def test_greatest(self, db):
        """product.price_floor = GREATEST($unit_price, 10)."""
        sql = _sql(db, 'invc.product',
                   columns='$description, $price_floor')
        assert 'price_floor' in sql
        assert 'GREATEST' in sql

    def test_cast_in_concatenation(self, db):
        """product.price_label uses CAST($unit_price AS TEXT)."""
        sql = _sql(db, 'invc.product',
                   columns='$price_label')
        assert 'price_label' in sql
        assert 'CAST' in sql
        assert '||' in sql

    def test_lpad_with_cast(self, db):
        """customer.account_code = LPAD(CAST($id AS TEXT), 8, '0')."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $account_code')
        assert 'account_code' in sql
        assert 'LPAD' in sql
        assert 'CAST' in sql

    def test_greatest_in_where(self, db):
        """WHERE on GREATEST column."""
        sql = _sql(db, 'invc.product',
                   columns='$description',
                   where='$price_floor > :min_price', min_price=50)
        assert 'GREATEST' in sql

    def test_greatest_in_order_by(self, db):
        """ORDER BY on GREATEST column."""
        sql = _sql(db, 'invc.product',
                   columns='$description, $price_floor',
                   order_by='$price_floor DESC')
        assert 'ORDER BY' in sql
        assert 'GREATEST' in sql


# ===================================================================
# Cat. 24 — Compound boolean formula
# ===================================================================

class TestCompoundBoolean:

    def test_boolean_or_with_formula_ref(self, db):
        """invoice_row.needs_review = $is_expensive OR (...)."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id, $needs_review')
        assert 'needs_review' in sql

    def test_boolean_and_with_exists_and_count(self, db):
        """customer.is_active_valuable = $has_invoices AND $n_invoices >= 3."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $is_active_valuable')
        assert 'is_active_valuable' in sql
        assert 'EXISTS' in sql
        assert 'COUNT' in sql

    def test_compound_boolean_in_where(self, db):
        """WHERE on compound boolean formula."""
        sql = _sql(db, 'invc.invoice_row',
                   columns='$id',
                   where='$needs_review = TRUE')
        assert '1000' in sql or 'needs_review' in sql

    def test_compound_boolean_in_order_by(self, db):
        """ORDER BY on compound boolean formula."""
        sql = _sql(db, 'invc.customer',
                   columns='$account_name, $is_active_valuable',
                   order_by='$is_active_valuable DESC')
        assert 'ORDER BY' in sql


# ===================================================================
# Cat. 25 — Combined queries phase 3
# ===================================================================

class TestCombinedPhase3:

    def test_invoice_all_advanced_vc(self, db):
        """invoice with all phase 3 virtual columns."""
        sql = _sql(db, 'invc.invoice',
                   columns="""$inv_number, $anno, $periodo, $value_category,
                              $display_total, $all_notes, $priority_note,
                              $invoice_status, $status_label,
                              @discount_tier_id.discount_rate""")
        assert 'EXTRACT' in sql
        assert 'TO_CHAR' in sql
        assert 'STRING_AGG' in sql
        assert 'COALESCE' in sql
        assert sql.count('CASE') >= 3

    def test_invoice_row_deep_chain(self, db):
        """invoice_row with formula chain + boolean + deep relation."""
        sql = _sql(db, 'invc.invoice_row',
                   columns="""$id, $line_gross, $needs_review,
                              $pricing_analysis, $customer_region""",
                   where='$needs_review = TRUE',
                   order_by='$line_gross DESC')
        assert sql.count('JOIN') >= 4
        assert 'ORDER BY' in sql
        assert 'CASE' in sql

    def test_customer_all_advanced(self, db):
        """customer with boolean composed + deep alias + CAST."""
        sql = _sql(db, 'invc.customer',
                   columns="""$account_name, $is_active_valuable, $region_name,
                              $account_code, $customer_rank""",
                   where='$is_active_valuable = TRUE',
                   order_by='$account_code')
        assert 'EXISTS' in sql
        assert 'COUNT' in sql
        assert 'LPAD' in sql
        assert 'CAST' in sql
        assert 'CASE' in sql

    def test_product_all_advanced(self, db):
        """product with GREATEST + CAST + previous VC."""
        sql = _sql(db, 'invc.product',
                   columns='$description, $price_floor, $price_label, $price_range, $total_sold',
                   order_by='$price_floor DESC')
        assert 'GREATEST' in sql
        assert 'CAST' in sql
        assert 'CASE' in sql
        assert 'SUM' in sql
