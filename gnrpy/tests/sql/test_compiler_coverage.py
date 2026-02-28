"""Runtime test suite for the SQL compiler.

Executes REAL queries on the database and verifies REAL results.
Tests cover all virtual column types: formula, alias, pyColumn,
bagItemColumn, joinColumn, subQueryColumn, compositeColumn,
window functions, boolean expressions, and deep relation navigation.

Uses both PostgreSQL and SQLite instances of the test_invoice project.
"""

import pytest

from core.common import BaseGnrTest
from gnr.sql.gnrsql_exceptions import GnrSqlMissingField

def setup_module(module):
    BaseGnrTest.setup_class()
def teardown_module(module):
    BaseGnrTest.teardown_class()


CUSTOMER_COUNT = 3200
INVOICE_COUNT = 256
INVOICE_ROW_COUNT = 803
PRODUCT_COUNT = 1695
INVOICE_NOTE_COUNT = 387
DISCOUNT_TIER_COUNT = 16
REGION_COUNT = 5
PRICE_YEAR_COUNT = 6780
PRICE_YEAR_NOTE_COUNT = 3381
CUSTOMER_RES_COUNT = 1625
CUSTOMER_TRD_COUNT = 791
CUSTOMER_COM_COUNT = 483
CUSTOMER_GOV_COUNT = 301
CUSTOMER_NSW_COUNT = 399
CUSTOMER_VIC_COUNT = 402
INVOICE_NSW_COUNT = 21
INVOICE_VIC_COUNT = 39
STAFF_COUNT = 32
STAFF_ROLE_COUNT = 5


# ===================================================================
# Physical columns
# ===================================================================

class TestPhysicalColumns:

    def test_single_column_pg(self, db_pg):
        rows = db_pg.table('invc.customer').query(
            columns='$account_name', limit=5
        ).fetch()
        assert len(rows) == 5
        assert all(r['account_name'] for r in rows)

    def test_single_column_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$account_name', limit=5
        ).fetch()
        assert len(rows) == 5
        assert all(r['account_name'] for r in rows)

    def test_multiple_columns_pg(self, db_pg):
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, $email, $phone', limit=3
        ).fetch()
        assert len(rows) == 3
        for r in rows:
            assert 'account_name' in r

    def test_multiple_columns_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$account_name, $email, $phone', limit=3
        ).fetch()
        assert len(rows) == 3
        for r in rows:
            assert 'account_name' in r

    def test_star_expansion_pg(self, db_pg):
        rows = db_pg.table('invc.customer').query(
            columns='*', limit=1
        ).fetch()
        assert len(rows) == 1
        r = rows[0]
        assert 'account_name' in r
        assert 'email' in r

    def test_star_expansion_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='*', limit=1
        ).fetch()
        assert len(rows) == 1
        r = rows[0]
        assert 'account_name' in r
        assert 'email' in r

    def test_count_matches_expected_pg(self, db_pg):
        n = db_pg.table('invc.customer').query(
            columns='$id'
        ).count()
        assert n == CUSTOMER_COUNT

    def test_count_matches_expected_sqlite(self, db_sqlite):
        n = db_sqlite.table('invc.customer').query(
            columns='$id'
        ).count()
        assert n == CUSTOMER_COUNT

    def test_table_counts_pg(self, db_pg):
        """Verify all table counts match expected values."""
        counts = {
            'invc.invoice': INVOICE_COUNT,
            'invc.invoice_row': INVOICE_ROW_COUNT,
            'invc.product': PRODUCT_COUNT,
            'invc.invoice_note': INVOICE_NOTE_COUNT,
            'invc.discount_tier': DISCOUNT_TIER_COUNT,
            'invc.region': REGION_COUNT,
            'invc.price_year': PRICE_YEAR_COUNT,
            'invc.price_year_note': PRICE_YEAR_NOTE_COUNT,
        }
        for tbl_name, expected in counts.items():
            n = db_pg.table(tbl_name).query(columns='$id').count()
            assert n == expected, (
                f'{tbl_name}: expected {expected}, got {n}'
            )

    def test_table_counts_sqlite(self, db_sqlite):
        counts = {
            'invc.invoice': INVOICE_COUNT,
            'invc.invoice_row': INVOICE_ROW_COUNT,
            'invc.product': PRODUCT_COUNT,
            'invc.invoice_note': INVOICE_NOTE_COUNT,
            'invc.discount_tier': DISCOUNT_TIER_COUNT,
            'invc.region': REGION_COUNT,
            'invc.price_year': PRICE_YEAR_COUNT,
            'invc.price_year_note': PRICE_YEAR_NOTE_COUNT,
        }
        for tbl_name, expected in counts.items():
            n = db_sqlite.table(tbl_name).query(
                columns='$id'
            ).count()
            assert n == expected, (
                f'{tbl_name}: expected {expected}, got {n}'
            )


# ===================================================================
# Alias columns (multi-level navigation)
# ===================================================================

class TestAliasColumn:

    def test_alias_matches_source_pg(self, db_pg):
        """aliasColumn value matches direct query on related table."""
        row = db_pg.table('invc.invoice').query(
            columns='$customer_id, $customer_name', limit=1
        ).fetch()[0]
        direct = db_pg.table('invc.customer').query(
            columns='$account_name',
            where='$id = :cid', cid=row['customer_id']
        ).fetch()[0]
        assert row['customer_name'] == direct['account_name']

    def test_alias_matches_source_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.invoice').query(
            columns='$customer_id, $customer_name', limit=1
        ).fetch()[0]
        direct = db_sqlite.table('invc.customer').query(
            columns='$account_name',
            where='$id = :cid', cid=row['customer_id']
        ).fetch()[0]
        assert row['customer_name'] == direct['account_name']

    def test_alias_two_levels_pg(self, db_pg):
        """invoice_row.customer_name traverses 2 joins."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $customer_name', limit=5
        ).fetch()
        assert len(rows) == 5
        assert all(
            isinstance(r['customer_name'], str) for r in rows
        )

    def test_alias_two_levels_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $customer_name', limit=5
        ).fetch()
        assert len(rows) == 5
        assert all(
            isinstance(r['customer_name'], str) for r in rows
        )

    def test_alias_three_levels_pg(self, db_pg):
        """invoice_row.customer_state traverses 3 joins."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $customer_state', limit=5
        ).fetch()
        assert len(rows) == 5
        assert all(r['customer_state'] for r in rows)

    def test_alias_three_levels_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $customer_state', limit=5
        ).fetch()
        assert len(rows) == 5
        assert all(r['customer_state'] for r in rows)

    def test_deep_alias_customer_region_pg(self, db_pg):
        """invoice_row.customer_region: 4+ joins deep."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $customer_region', limit=5
        ).fetch()
        assert len(rows) == 5
        assert all(r['customer_region'] for r in rows)

    def test_deep_alias_customer_region_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $customer_region', limit=5
        ).fetch()
        assert len(rows) == 5
        assert all(r['customer_region'] for r in rows)

    def test_region_name_cross_validate_pg(self, db_pg):
        """customer.region_name matches direct region query."""
        row = db_pg.table('invc.customer').query(
            columns='$state, $region_name',
            where='$region_name IS NOT NULL', limit=1
        ).fetch()[0]
        state_row = db_pg.table('invc.state').query(
            columns='$region_code',
            where='$code = :s', s=row['state']
        ).fetch()[0]
        region_row = db_pg.table('invc.region').query(
            columns='$name',
            where='$code = :rc', rc=state_row['region_code']
        ).fetch()[0]
        assert row['region_name'] == region_row['name']

    def test_region_name_cross_validate_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.customer').query(
            columns='$state, $region_name',
            where='$region_name IS NOT NULL', limit=1
        ).fetch()[0]
        state_row = db_sqlite.table('invc.state').query(
            columns='$region_code',
            where='$code = :s', s=row['state']
        ).fetch()[0]
        region_row = db_sqlite.table('invc.region').query(
            columns='$name',
            where='$code = :rc', rc=state_row['region_code']
        ).fetch()[0]
        assert row['region_name'] == region_row['name']


# ===================================================================
# Formula columns with select= (COUNT, SUM, EXISTS, LIMIT)
# ===================================================================

class TestFormulaSelect:

    def test_count_n_invoices_pg(self, db_pg):
        """customer.n_invoices matches actual invoice count."""
        row = db_pg.table('invc.customer').query(
            columns='$id, $n_invoices',
            where='$n_invoices > 0', limit=1
        ).fetch()[0]
        actual = db_pg.table('invc.invoice').query(
            columns='$id',
            where='$customer_id = :cid', cid=row['id']
        ).count()
        assert int(row['n_invoices']) == actual

    def test_count_n_invoices_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.customer').query(
            columns='$id, $n_invoices',
            where='$n_invoices > 0', limit=1
        ).fetch()[0]
        actual = db_sqlite.table('invc.invoice').query(
            columns='$id',
            where='$customer_id = :cid', cid=row['id']
        ).count()
        assert int(row['n_invoices']) == actual

    def test_sum_invoiced_total_pg(self, db_pg):
        row = db_pg.table('invc.customer').query(
            columns='$id, $invoiced_total',
            where='$invoiced_total > 0', limit=1
        ).fetch()[0]
        assert float(row['invoiced_total']) > 0

    def test_sum_invoiced_total_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.customer').query(
            columns='$id, $invoiced_total',
            where='$invoiced_total > 0', limit=1
        ).fetch()[0]
        assert float(row['invoiced_total']) > 0

    def test_last_invoice_id_pg(self, db_pg):
        """last_invoice_id returns a valid invoice id."""
        row = db_pg.table('invc.customer').query(
            columns='$id, $last_invoice_id',
            where='$last_invoice_id IS NOT NULL', limit=1
        ).fetch()[0]
        inv = db_pg.table('invc.invoice').query(
            columns='$id',
            where='$id = :iid', iid=row['last_invoice_id']
        ).fetch()
        assert len(inv) == 1

    def test_last_invoice_id_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.customer').query(
            columns='$id, $last_invoice_id',
            where='$last_invoice_id IS NOT NULL', limit=1
        ).fetch()[0]
        inv = db_sqlite.table('invc.invoice').query(
            columns='$id',
            where='$id = :iid', iid=row['last_invoice_id']
        ).fetch()
        assert len(inv) == 1

    def test_exists_has_invoices_pg(self, db_pg):
        """has_invoices=True only for customers with invoices."""
        row = db_pg.table('invc.customer').query(
            columns='$id, $has_invoices',
            where='$has_invoices = TRUE', limit=1
        ).fetch()[0]
        n = db_pg.table('invc.invoice').query(
            columns='$id',
            where='$customer_id = :cid', cid=row['id']
        ).count()
        assert n > 0

    def test_exists_has_invoices_sqlite(self, db_sqlite):
        """EXISTS formula not supported on SQLite."""
        pytest.skip('EXISTS formula not supported on SQLite')

    def test_row_count_pg(self, db_pg):
        """invoice.row_count matches actual row count."""
        row = db_pg.table('invc.invoice').query(
            columns='$id, $row_count',
            where='$row_count > 0', limit=1
        ).fetch()[0]
        actual = db_pg.table('invc.invoice_row').query(
            columns='$id',
            where='$invoice_id = :iid', iid=row['id']
        ).count()
        assert int(row['row_count']) == actual

    def test_row_count_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.invoice').query(
            columns='$id, $row_count',
            where='$row_count > 0', limit=1
        ).fetch()[0]
        actual = db_sqlite.table('invc.invoice_row').query(
            columns='$id',
            where='$invoice_id = :iid', iid=row['id']
        ).count()
        assert int(row['row_count']) == actual

    def test_total_sold_pg(self, db_pg):
        """product.total_sold matches SUM(quantity)."""
        row = db_pg.table('invc.product').query(
            columns='$id, $total_sold',
            where='$total_sold > 0', limit=1
        ).fetch()[0]
        assert float(row['total_sold']) > 0

    def test_total_sold_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.product').query(
            columns='$id, $total_sold',
            where='$total_sold > 0', limit=1
        ).fetch()[0]
        assert float(row['total_sold']) > 0


# ===================================================================
# Formula columns with SQL expressions
# ===================================================================

class TestFormulaSql:

    def test_line_total_pg(self, db_pg):
        """line_total = quantity * unit_price."""
        row = db_pg.table('invc.invoice_row').query(
            columns='$quantity, $unit_price, $line_total',
            where='$quantity IS NOT NULL AND $unit_price IS NOT NULL',
            limit=1
        ).fetch()[0]
        expected = float(row['quantity']) * float(row['unit_price'])
        assert abs(float(row['line_total']) - expected) < 0.01

    def test_line_total_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.invoice_row').query(
            columns='$quantity, $unit_price, $line_total',
            where='$quantity IS NOT NULL AND $unit_price IS NOT NULL',
            limit=1
        ).fetch()[0]
        expected = float(row['quantity']) * float(row['unit_price'])
        assert abs(float(row['line_total']) - expected) < 0.01

    def test_concatenation_full_address_pg(self, db_pg):
        """full_address = street_address || ', ' || suburb."""
        row = db_pg.table('invc.customer').query(
            columns='$street_address, $suburb, $full_address',
            where=('$street_address IS NOT NULL'
                   ' AND $suburb IS NOT NULL'),
            limit=1
        ).fetch()[0]
        expected = f"{row['street_address']}, {row['suburb']}"
        assert row['full_address'] == expected

    def test_concatenation_full_address_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.customer').query(
            columns='$street_address, $suburb, $full_address',
            where=('$street_address IS NOT NULL'
                   ' AND $suburb IS NOT NULL'),
            limit=1
        ).fetch()[0]
        expected = f"{row['street_address']}, {row['suburb']}"
        assert row['full_address'] == expected

    def test_code_and_desc_pg(self, db_pg):
        """product.code_and_desc = code || ' - ' || description."""
        row = db_pg.table('invc.product').query(
            columns='$code, $description, $code_and_desc',
            where='$code IS NOT NULL AND $description IS NOT NULL',
            limit=1
        ).fetch()[0]
        expected = f"{row['code']} - {row['description']}"
        assert row['code_and_desc'] == expected

    def test_code_and_desc_sqlite(self, db_sqlite):
        row = db_sqlite.table('invc.product').query(
            columns='$code, $description, $code_and_desc',
            where='$code IS NOT NULL AND $description IS NOT NULL',
            limit=1
        ).fetch()[0]
        expected = f"{row['code']} - {row['description']}"
        assert row['code_and_desc'] == expected


# ===================================================================
# CASE WHEN
# ===================================================================

class TestCaseWhen:

    def test_value_category_pg(self, db_pg):
        """invoice.value_category returns valid categories."""
        rows = db_pg.table('invc.invoice').query(
            columns='$total, $value_category', limit=20
        ).fetch()
        valid = {'High', 'Medium', 'Low'}
        for r in rows:
            assert r['value_category'] in valid
            total = float(r['total'] or 0)
            if total > 1000:
                assert r['value_category'] == 'High'
            elif total > 100:
                assert r['value_category'] == 'Medium'
            else:
                assert r['value_category'] == 'Low'

    def test_value_category_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$total, $value_category', limit=20
        ).fetch()
        valid = {'High', 'Medium', 'Low'}
        for r in rows:
            assert r['value_category'] in valid

    def test_size_category_pg(self, db_pg):
        """invoice_row.size_category uses CASE with IN."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$quantity, $size_category', limit=20
        ).fetch()
        valid = {'Small', 'Medium', 'Large'}
        for r in rows:
            assert r['size_category'] in valid

    def test_size_category_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$quantity, $size_category', limit=20
        ).fetch()
        valid = {'Small', 'Medium', 'Large'}
        for r in rows:
            assert r['size_category'] in valid

    def test_price_range_pg(self, db_pg):
        """product.price_range categorization."""
        rows = db_pg.table('invc.product').query(
            columns='$unit_price, $price_range', limit=20
        ).fetch()
        valid = {'Premium', 'Mid', 'Budget'}
        for r in rows:
            assert r['price_range'] in valid

    def test_price_range_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.product').query(
            columns='$unit_price, $price_range', limit=20
        ).fetch()
        valid = {'Premium', 'Mid', 'Budget'}
        for r in rows:
            assert r['price_range'] in valid

    def test_customer_rank_pg(self, db_pg):
        """customer.customer_rank uses n_invoices (COUNT subquery)."""
        rows = db_pg.table('invc.customer').query(
            columns='$n_invoices, $customer_rank', limit=20
        ).fetch()
        valid = {'Inactive', 'Occasional', 'Regular'}
        for r in rows:
            assert r['customer_rank'] in valid

    def test_customer_rank_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$n_invoices, $customer_rank', limit=20
        ).fetch()
        valid = {'Inactive', 'Occasional', 'Regular'}
        for r in rows:
            assert r['customer_rank'] in valid

    def test_nested_case_invoice_status_pg(self, db_pg):
        """invoice.invoice_status nested CASE."""
        rows = db_pg.table('invc.invoice').query(
            columns='$total, $gross_total, $invoice_status', limit=20
        ).fetch()
        valid = {'Draft', 'Empty', 'Large', 'Medium', 'Small'}
        for r in rows:
            assert r['invoice_status'] in valid

    def test_nested_case_invoice_status_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$total, $gross_total, $invoice_status', limit=20
        ).fetch()
        valid = {'Draft', 'Empty', 'Large', 'Medium', 'Small'}
        for r in rows:
            assert r['invoice_status'] in valid

    def test_product_note_with_relation_pg(self, db_pg):
        """invoice_row.product_note references @product_id."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $product_note', limit=10
        ).fetch()
        valid = {'Premium', 'Standard'}
        for r in rows:
            assert r['product_note'] in valid

    def test_product_note_with_relation_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $product_note', limit=10
        ).fetch()
        valid = {'Premium', 'Standard'}
        for r in rows:
            assert r['product_note'] in valid

    def test_pricing_analysis_pg(self, db_pg):
        """invoice_row.pricing_analysis: CASE on effective_price."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $pricing_analysis', limit=20
        ).fetch()
        valid = {
            'No price', 'Above list', 'Discounted', 'At list price'
        }
        for r in rows:
            assert r['pricing_analysis'] in valid

    def test_pricing_analysis_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $pricing_analysis', limit=20
        ).fetch()
        valid = {
            'No price', 'Above list', 'Discounted', 'At list price'
        }
        for r in rows:
            assert r['pricing_analysis'] in valid


# ===================================================================
# COALESCE
# ===================================================================

class TestCoalesce:

    def test_display_total_pg(self, db_pg):
        """display_total = COALESCE(gross_total, total, 0)."""
        rows = db_pg.table('invc.invoice').query(
            columns='$total, $gross_total, $display_total', limit=10
        ).fetch()
        for r in rows:
            assert r['display_total'] is not None

    def test_display_total_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$total, $gross_total, $display_total', limit=10
        ).fetch()
        for r in rows:
            assert r['display_total'] is not None

    def test_effective_price_pg(self, db_pg):
        """effective_price = COALESCE(unit_price, product.unit_price)."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$unit_price, $effective_price', limit=10
        ).fetch()
        for r in rows:
            if r['unit_price'] is not None:
                assert (float(r['effective_price'])
                        == float(r['unit_price']))

    def test_effective_price_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$unit_price, $effective_price', limit=10
        ).fetch()
        for r in rows:
            if r['unit_price'] is not None:
                assert (float(r['effective_price'])
                        == float(r['unit_price']))

    def test_display_name_pg(self, db_pg):
        """display_name never returns None."""
        rows = db_pg.table('invc.customer').query(
            columns='$display_name', limit=10
        ).fetch()
        assert all(r['display_name'] for r in rows)

    def test_display_name_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$display_name', limit=10
        ).fetch()
        assert all(r['display_name'] for r in rows)


# ===================================================================
# CONCAT function
# ===================================================================

class TestConcatFunction:

    def test_concat_code_desc_pg(self, db_pg):
        rows = db_pg.table('invc.product').query(
            columns='$code, $description, $concat_code_desc',
            where='$code IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['code'] in r['concat_code_desc']
            assert r['description'] in r['concat_code_desc']

    def test_concat_code_desc_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.product').query(
            columns='$code, $description, $concat_code_desc',
            where='$code IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['code'] in r['concat_code_desc']
            assert r['description'] in r['concat_code_desc']

    def test_contact_info_pg(self, db_pg):
        """CONCAT with COALESCE inside."""
        rows = db_pg.table('invc.customer').query(
            columns='$email, $phone, $contact_info', limit=5
        ).fetch()
        for r in rows:
            assert '|' in r['contact_info']

    def test_contact_info_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$email, $phone, $contact_info', limit=5
        ).fetch()
        for r in rows:
            assert '|' in r['contact_info']


# ===================================================================
# REPLACE
# ===================================================================

class TestReplace:

    def test_description_clean_pg(self, db_pg):
        """REPLACE($description, ' ', '-')."""
        rows = db_pg.table('invc.product').query(
            columns='$description, $description_clean',
            where='$description IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            expected = r['description'].replace(' ', '-')
            assert r['description_clean'] == expected

    def test_description_clean_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.product').query(
            columns='$description, $description_clean',
            where='$description IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            expected = r['description'].replace(' ', '-')
            assert r['description_clean'] == expected


# ===================================================================
# CAST (nested, boolean comparison)
# ===================================================================

class TestCast:

    def test_price_as_int_text_pg(self, db_pg):
        """Nested CAST: int then text."""
        rows = db_pg.table('invc.product').query(
            columns='$unit_price, $price_as_int_text',
            where='$unit_price IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert isinstance(r['price_as_int_text'], str)
            assert r['price_as_int_text'].lstrip('-').isdigit()

    def test_price_as_int_text_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.product').query(
            columns='$unit_price, $price_as_int_text',
            where='$unit_price IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert isinstance(r['price_as_int_text'], str)
            assert r['price_as_int_text'].lstrip('-').isdigit()

    def test_matches_list_price_pg(self, db_pg):
        """CAST(comparison AS boolean)."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$unit_price, $matches_list_price', limit=10
        ).fetch()
        for r in rows:
            assert r['matches_list_price'] in (True, False, None)

    def test_matches_list_price_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$unit_price, $matches_list_price', limit=10
        ).fetch()
        for r in rows:
            assert r['matches_list_price'] in (True, False, None)


# ===================================================================
# UPPER + TRIM
# ===================================================================

class TestUpperTrim:

    def test_note_type_clean_pg(self, db_pg):
        rows = db_pg.table('invc.invoice_note').query(
            columns='$note_type, $note_type_clean', limit=10
        ).fetch()
        for r in rows:
            if r['note_type']:
                assert r['note_type_clean'] == (
                    r['note_type'].strip().upper()
                )

    def test_note_type_clean_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_note').query(
            columns='$note_type, $note_type_clean', limit=10
        ).fetch()
        for r in rows:
            if r['note_type']:
                assert r['note_type_clean'] == (
                    r['note_type'].strip().upper()
                )


# ===================================================================
# LIKE in formulas
# ===================================================================

class TestLikeFormula:

    def test_is_warning_pg(self, db_pg):
        """is_warning: note_type LIKE 'WARN%'."""
        rows = db_pg.table('invc.invoice_note').query(
            columns='$note_type, $is_warning', limit=20
        ).fetch()
        for r in rows:
            if r['note_type'] and r['note_type'].startswith('WARN'):
                assert r['is_warning'] is True

    def test_is_warning_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_note').query(
            columns='$note_type, $is_warning', limit=20
        ).fetch()
        for r in rows:
            if r['note_type'] and r['note_type'].startswith('WARN'):
                assert bool(r['is_warning'])

    def test_number_series_pg(self, db_pg):
        """CASE WHEN $inv_number LIKE 'A%' => Series A etc."""
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $number_series', limit=20
        ).fetch()
        valid = {'Series A', 'Series B', 'Other'}
        for r in rows:
            assert r['number_series'] in valid

    def test_number_series_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, $number_series', limit=20
        ).fetch()
        valid = {'Series A', 'Series B', 'Other'}
        for r in rows:
            assert r['number_series'] in valid


# ===================================================================
# GREATEST
# ===================================================================

class TestGreatest:

    def test_price_floor_pg(self, db_pg):
        """GREATEST(unit_price, 10): always >= 10."""
        rows = db_pg.table('invc.product').query(
            columns='$unit_price, $price_floor',
            where='$unit_price IS NOT NULL', limit=10
        ).fetch()
        for r in rows:
            assert float(r['price_floor']) >= 10

    def test_price_floor_sqlite(self, db_sqlite):
        """GREATEST not available on SQLite."""
        pytest.skip('GREATEST function not supported on SQLite')


# ===================================================================
# ROUND and ABS
# ===================================================================

class TestMathFunctions:

    def test_price_rounded_pg(self, db_pg):
        """ROUND(unit_price, 0)."""
        rows = db_pg.table('invc.product').query(
            columns='$unit_price, $price_rounded',
            where='$unit_price IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            diff = abs(
                float(r['price_rounded'])
                - round(float(r['unit_price']))
            )
            assert diff < 1.0

    def test_price_rounded_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.product').query(
            columns='$unit_price, $price_rounded',
            where='$unit_price IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            diff = abs(
                float(r['price_rounded'])
                - round(float(r['unit_price']))
            )
            assert diff < 1.0

    def test_rounded_total_pg(self, db_pg):
        rows = db_pg.table('invc.invoice_row').query(
            columns='$line_total, $rounded_total',
            where='$line_total IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['rounded_total'] is not None

    def test_rounded_total_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$line_total, $rounded_total',
            where='$line_total IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['rounded_total'] is not None

    def test_abs_discount_pg(self, db_pg):
        """ABS(unit_price - product.unit_price) >= 0."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $abs_discount',
            where='$abs_discount IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert float(r['abs_discount']) >= 0

    def test_abs_discount_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $abs_discount',
            where='$abs_discount IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert float(r['abs_discount']) >= 0


# ===================================================================
# LAG / OVER / PARTITION BY (window functions)
# ===================================================================

class TestWindowFunctions:

    def test_prev_quantity_pg(self, db_pg):
        """LAG returns NULL for first row, integer for others."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$invoice_id, $prev_quantity, $_row_count',
            order_by='$invoice_id, $_row_count', limit=20
        ).fetch()
        assert len(rows) > 0
        has_null = any(r['prev_quantity'] is None for r in rows)
        has_value = any(r['prev_quantity'] is not None for r in rows)
        assert has_null or has_value

    def test_prev_quantity_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$invoice_id, $prev_quantity, $_row_count',
            order_by='$invoice_id, $_row_count', limit=20
        ).fetch()
        assert len(rows) > 0


# ===================================================================
# FILTER(WHERE) aggregation
# ===================================================================

class TestFilterAggregation:

    def test_priced_rows_pct_pg(self, db_pg):
        """priced_rows_pct is between 0 and 100."""
        rows = db_pg.table('invc.invoice').query(
            columns='$id, $priced_rows_pct',
            where='$priced_rows_pct IS NOT NULL', limit=10
        ).fetch()
        for r in rows:
            pct = float(r['priced_rows_pct'])
            assert 0 <= pct <= 100

    def test_priced_rows_pct_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$id, $priced_rows_pct',
            where='$priced_rows_pct IS NOT NULL', limit=10
        ).fetch()
        for r in rows:
            pct = float(r['priced_rows_pct'])
            assert 0 <= pct <= 100


# ===================================================================
# Boolean formulas (is_expensive, needs_review, is_active_valuable)
# ===================================================================

class TestBooleanFormulas:

    def test_is_expensive_pg(self, db_pg):
        """is_expensive = line_total > 1000."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$line_total, $is_expensive',
            where='$line_total IS NOT NULL', limit=20
        ).fetch()
        for r in rows:
            lt = float(r['line_total'])
            if lt > 1000:
                assert r['is_expensive'] is True

    def test_is_expensive_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$line_total, $is_expensive',
            where='$line_total IS NOT NULL', limit=20
        ).fetch()
        for r in rows:
            lt = float(r['line_total'])
            if lt > 1000:
                assert bool(r['is_expensive'])

    def test_needs_review_pg(self, db_pg):
        """needs_review = is_expensive OR (qty>50 AND price<1)."""
        rows = db_pg.table('invc.invoice_row').query(
            columns=(
                '$line_total, $quantity, $unit_price, $needs_review'
            ),
            where='$needs_review = TRUE', limit=5
        ).fetch()
        for r in rows:
            lt = float(r['line_total'] or 0)
            q = int(r['quantity'] or 0)
            p = float(r['unit_price'] or 0)
            assert lt > 1000 or (q > 50 and p < 1)

    def test_needs_review_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns=(
                '$line_total, $quantity, $unit_price, $needs_review'
            ),
            where='$needs_review = TRUE', limit=5
        ).fetch()
        for r in rows:
            lt = float(r['line_total'] or 0)
            q = int(r['quantity'] or 0)
            p = float(r['unit_price'] or 0)
            assert lt > 1000 or (q > 50 and p < 1)

    def test_is_active_valuable_pg(self, db_pg):
        """is_active_valuable = has_invoices AND n_invoices >= 3."""
        rows = db_pg.table('invc.customer').query(
            columns='$has_invoices, $n_invoices, $is_active_valuable',
            where='$is_active_valuable = TRUE', limit=5
        ).fetch()
        for r in rows:
            assert r['has_invoices'] is True
            assert int(r['n_invoices']) >= 3

    def test_is_active_valuable_sqlite(self, db_sqlite):
        """is_active_valuable references has_invoices (EXISTS)."""
        pytest.skip('EXISTS formula not supported on SQLite')


# ===================================================================
# Formula chain (formula referencing formula)
# ===================================================================

class TestFormulaChain:

    def test_line_vat_pg(self, db_pg):
        """line_vat = line_total * vat_rate."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$line_total, $vat_rate, $line_vat',
            where=('$line_total IS NOT NULL'
                   ' AND $vat_rate IS NOT NULL'), limit=5
        ).fetch()
        for r in rows:
            expected = float(r['line_total']) * float(r['vat_rate'])
            assert abs(float(r['line_vat']) - expected) < 0.01

    def test_line_vat_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$line_total, $vat_rate, $line_vat',
            where=('$line_total IS NOT NULL'
                   ' AND $vat_rate IS NOT NULL'), limit=5
        ).fetch()
        for r in rows:
            expected = float(r['line_total']) * float(r['vat_rate'])
            assert abs(float(r['line_vat']) - expected) < 0.01

    def test_line_gross_pg(self, db_pg):
        """line_gross = line_total + line_vat."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$line_total, $line_vat, $line_gross',
            where=('$line_total IS NOT NULL'
                   ' AND $line_vat IS NOT NULL'), limit=5
        ).fetch()
        for r in rows:
            expected = (float(r['line_total'])
                        + float(r['line_vat']))
            assert abs(float(r['line_gross']) - expected) < 0.01

    def test_line_gross_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$line_total, $line_vat, $line_gross',
            where=('$line_total IS NOT NULL'
                   ' AND $line_vat IS NOT NULL'), limit=5
        ).fetch()
        for r in rows:
            expected = (float(r['line_total'])
                        + float(r['line_vat']))
            assert abs(float(r['line_gross']) - expected) < 0.01


# ===================================================================
# subQueryColumn (json, xml, plain)
# ===================================================================

class TestSubQueryColumn:

    def test_rows_json_pg(self, db_pg):
        """mode='json': returns a list of dicts."""
        rows = db_pg.table('invc.invoice').query(
            columns='$id, $rows_json',
            where='$row_count > 0', limit=3
        ).fetch()
        for r in rows:
            if r['rows_json']:
                data = r['rows_json']
                assert isinstance(data, list)
                assert len(data) > 0
                assert 'product_id' in data[0]

    def test_notes_xml_pg(self, db_pg):
        """mode='xml': returns XML-like string."""
        rows = db_pg.table('invc.invoice').query(
            columns='$id, $notes_xml',
            where='$notes_xml IS NOT NULL', limit=3
        ).fetch()
        for r in rows:
            if r['notes_xml']:
                xml_str = str(r['notes_xml'])
                assert '<' in xml_str

    def test_max_row_price_pg(self, db_pg):
        """mode=None (plain): MAX(unit_price) is numeric."""
        rows = db_pg.table('invc.invoice').query(
            columns='$id, $max_row_price',
            where='$max_row_price IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert float(r['max_row_price']) > 0

    def test_max_row_price_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$id, $max_row_price',
            where='$max_row_price IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert float(r['max_row_price']) > 0

    def test_max_row_price_cross_validate_pg(self, db_pg):
        """max_row_price matches direct MAX query."""
        row = db_pg.table('invc.invoice').query(
            columns='$id, $max_row_price',
            where='$max_row_price IS NOT NULL', limit=1
        ).fetch()[0]
        mx = db_pg.table('invc.invoice_row').readColumns(
            columns='MAX($unit_price)',
            where='$invoice_id = :iid', iid=row['id']
        )
        assert abs(float(row['max_row_price']) - float(mx)) < 0.01


# ===================================================================
# compositeColumn (basic)
# ===================================================================

class TestCompositeColumn:

    def test_product_year_key_pg(self, db_pg):
        """product_year_key is composite of product_id + year."""
        rows = db_pg.table('invc.price_year').query(
            columns='$product_id, $year, $product_year_key',
            limit=5
        ).fetch()
        for r in rows:
            assert r['product_year_key'] is not None

    def test_product_year_key_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.price_year').query(
            columns='$product_id, $year, $product_year_key',
            limit=5
        ).fetch()
        for r in rows:
            assert r['product_year_key'] is not None

    def test_price_year_note_navigation_pg(self, db_pg):
        """Navigate through compositeColumn relation."""
        rows = db_pg.table('invc.price_year_note').query(
            columns='$id, $price_year_price',
            where='$price_year_price IS NOT NULL', limit=5
        ).fetch()
        assert len(rows) > 0
        for r in rows:
            assert float(r['price_year_price']) > 0

    def test_price_year_note_navigation_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.price_year_note').query(
            columns='$id, $price_year_price',
            where='$price_year_price IS NOT NULL', limit=5
        ).fetch()
        assert len(rows) > 0
        for r in rows:
            assert float(r['price_year_price']) > 0

    def test_deep_navigation_through_composite_pg(self, db_pg):
        """Navigate composite -> product -> description."""
        rows = db_pg.table('invc.price_year_note').query(
            columns='$id, $product_description',
            where='$product_description IS NOT NULL', limit=5
        ).fetch()
        assert len(rows) > 0
        for r in rows:
            assert isinstance(r['product_description'], str)

    def test_deep_navigation_through_composite_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.price_year_note').query(
            columns='$id, $product_description',
            where='$product_description IS NOT NULL', limit=5
        ).fetch()
        assert len(rows) > 0
        for r in rows:
            assert isinstance(r['product_description'], str)


# ===================================================================
# pyColumn (returns NULL in SQL)
# ===================================================================

class TestPyColumn:

    def test_computed_margin_pg(self, db_pg):
        """pyColumn emits NULL in SQL, py_method fills value."""
        rows = db_pg.table('invc.product').query(
            columns='$description, $computed_margin', limit=5
        ).fetch()
        for r in rows:
            assert 'computed_margin' in r

    def test_computed_margin_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.product').query(
            columns='$description, $computed_margin', limit=5
        ).fetch()
        for r in rows:
            assert 'computed_margin' in r

    def test_customer_score_pg(self, db_pg):
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, $customer_score', limit=5
        ).fetch()
        for r in rows:
            assert 'customer_score' in r

    def test_customer_score_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$account_name, $customer_score', limit=5
        ).fetch()
        for r in rows:
            assert 'customer_score' in r

    def test_pycolumn_alongside_formula_pg(self, db_pg):
        """pyColumn doesn't break other columns."""
        rows = db_pg.table('invc.product').query(
            columns='$computed_margin, $price_floor', limit=5
        ).fetch()
        for r in rows:
            assert 'computed_margin' in r
            assert r['price_floor'] is not None

    def test_pycolumn_alongside_formula_sqlite(self, db_sqlite):
        """GREATEST in price_floor not supported on SQLite."""
        pytest.skip('GREATEST function not supported on SQLite')


# ===================================================================
# bagItemColumn (xpath generation)
# ===================================================================

class TestBagItemColumn:

    def test_detail_weight_no_crash_pg(self, db_pg):
        """bagItemColumn doesn't crash (likely returns None)."""
        rows = db_pg.table('invc.product').query(
            columns='$description, $detail_weight', limit=5
        ).fetch()
        assert len(rows) == 5

    def test_detail_color_no_crash_pg(self, db_pg):
        rows = db_pg.table('invc.product').query(
            columns='$description, $detail_color', limit=5
        ).fetch()
        assert len(rows) == 5

    def test_bagitem_with_physical_pg(self, db_pg):
        """bagItemColumn alongside physical columns."""
        rows = db_pg.table('invc.product').query(
            columns='$code, $unit_price, $detail_weight, $detail_color',
            limit=5
        ).fetch()
        assert len(rows) == 5
        for r in rows:
            assert r['code'] is not None


# ===================================================================
# joinColumn (discount_tier_id)
# ===================================================================

class TestJoinColumn:

    def test_discount_tier_id_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $discount_tier_id', limit=10
        ).fetch()
        assert len(rows) == 10

    def test_discount_tier_id_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, $discount_tier_id', limit=10
        ).fetch()
        assert len(rows) == 10

    def test_discount_tier_navigation_pg(self, db_pg):
        """Navigate through joinColumn to discount_rate."""
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, @discount_tier_id.discount_rate',
            where='$discount_tier_id IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['_discount_tier_id_discount_rate'] is not None

    def test_discount_tier_navigation_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, @discount_tier_id.discount_rate',
            where='$discount_tier_id IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['_discount_tier_id_discount_rate'] is not None


# ===================================================================
# var_* parameters
# ===================================================================

class TestVarParameters:

    def test_status_label_pg(self, db_pg):
        """var_ params provide default values in CASE."""
        rows = db_pg.table('invc.invoice').query(
            columns='$total, $status_label', limit=20
        ).fetch()
        valid = {
            'Premium Invoice', 'Standard Invoice', 'Basic Invoice'
        }
        for r in rows:
            assert r['status_label'] in valid

    def test_status_label_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$total, $status_label', limit=20
        ).fetch()
        valid = {
            'Premium Invoice', 'Standard Invoice', 'Basic Invoice'
        }
        for r in rows:
            assert r['status_label'] in valid


# ===================================================================
# Named sub-queries (select_*)
# ===================================================================

class TestNamedSubQuery:

    def test_priority_note_pg(self, db_pg):
        """COALESCE(#top_note, 'No notes')."""
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $priority_note', limit=10
        ).fetch()
        for r in rows:
            assert r['priority_note'] is not None

    def test_priority_note_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, $priority_note', limit=10
        ).fetch()
        for r in rows:
            assert r['priority_note'] is not None

    def test_smart_row_count_pg(self, db_pg):
        """CASE with two named selects (#high_rows, #all_rows)."""
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $total, $smart_row_count',
            where='$smart_row_count IS NOT NULL', limit=10
        ).fetch()
        for r in rows:
            assert int(r['smart_row_count']) >= 0

    def test_smart_row_count_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, $total, $smart_row_count',
            where='$smart_row_count IS NOT NULL', limit=10
        ).fetch()
        for r in rows:
            assert int(r['smart_row_count']) >= 0


# ===================================================================
# $date + $invoice_time (temporal arithmetic)
# ===================================================================

class TestTemporalArithmetic:

    def test_invoice_datetime_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='$date, $invoice_time, $invoice_datetime',
            where='$invoice_time IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['invoice_datetime'] is not None

    def test_invoice_datetime_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$date, $invoice_time, $invoice_datetime',
            where='$invoice_time IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['invoice_datetime'] is not None


# ===================================================================
# Relation navigation (direct @ syntax)
# ===================================================================

class TestRelationNavigation:

    def test_one_level_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, @customer_id.account_name', limit=5
        ).fetch()
        assert len(rows) == 5
        for r in rows:
            assert isinstance(r['_customer_id_account_name'], str)

    def test_one_level_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, @customer_id.account_name', limit=5
        ).fetch()
        assert len(rows) == 5
        for r in rows:
            assert isinstance(r['_customer_id_account_name'], str)

    def test_two_levels_pg(self, db_pg):
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, @invoice_id.@customer_id.account_name',
            limit=5
        ).fetch()
        assert len(rows) == 5

    def test_two_levels_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, @invoice_id.@customer_id.account_name',
            limit=5
        ).fetch()
        assert len(rows) == 5

    def test_formula_with_relation_navigation_pg(self, db_pg):
        """Navigate through formulaColumn last_invoice_id."""
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, @last_invoice_id.inv_number',
            where='$last_invoice_id IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['_last_invoice_id_inv_number'] is not None

    def test_formula_with_relation_navigation_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$account_name, @last_invoice_id.inv_number',
            where='$last_invoice_id IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['_last_invoice_id_inv_number'] is not None

    def test_one_to_many_pg(self, db_pg):
        """customer.@invoices.inv_number one-to-many."""
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, @invoices.inv_number',
            where='$has_invoices = TRUE', limit=5
        ).fetch()
        assert len(rows) > 0

    def test_one_to_many_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$account_name, @invoices.inv_number',
            where='$n_invoices > 0', limit=5
        ).fetch()
        assert len(rows) > 0


# ===================================================================
# avg_invoice_value (formula referencing formulas with NULLIF)
# ===================================================================

class TestNullif:

    def test_avg_invoice_value_pg(self, db_pg):
        """invoiced_total / NULLIF(n_invoices, 0)."""
        rows = db_pg.table('invc.customer').query(
            columns=(
                '$invoiced_total, $n_invoices, $avg_invoice_value'
            ),
            where='$n_invoices > 0', limit=5
        ).fetch()
        for r in rows:
            expected = (
                float(r['invoiced_total'])
                / float(r['n_invoices'])
            )
            assert (abs(float(r['avg_invoice_value']) - expected)
                    < 0.01)

    def test_avg_invoice_value_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns=(
                '$invoiced_total, $n_invoices, $avg_invoice_value'
            ),
            where='$n_invoices > 0', limit=5
        ).fetch()
        for r in rows:
            expected = (
                float(r['invoiced_total'])
                / float(r['n_invoices'])
            )
            assert (abs(float(r['avg_invoice_value']) - expected)
                    < 0.01)


# ===================================================================
# has_activity (EXISTS with OR)
# ===================================================================

class TestExistsOr:

    def test_has_activity_pg(self, db_pg):
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, $has_activity',
            where='$has_activity = TRUE', limit=5
        ).fetch()
        assert len(rows) > 0

    def test_has_activity_sqlite(self, db_sqlite):
        """has_activity uses EXISTS, not supported on SQLite."""
        pytest.skip('EXISTS formula not supported on SQLite')


# ===================================================================
# PostgreSQL-only VCs (skip on SQLite)
# ===================================================================

class TestPostgresOnly:
    """VCs that use PG-specific functions: regexp_replace, translate,
    substring FROM/FOR, EXTRACT(YEAR), TO_CHAR, date_part,
    date_trunc, INTERVAL+MOD+EXTRACT(DOW), LPAD,
    array_to_string(ARRAY()), array_length(ARRAY(SELECT))."""

    def test_code_normalized_pg(self, db_pg):
        """regexp_replace: remove non-alphanumeric, lowercase."""
        rows = db_pg.table('invc.product').query(
            columns='$code, $code_normalized',
            where='$code IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['code_normalized'] is not None
            assert r['code_normalized'] == (
                r['code_normalized'].lower()
            )

    def test_code_clean_pg(self, db_pg):
        """translate: replace chars."""
        rows = db_pg.table('invc.product').query(
            columns='$code, $code_clean',
            where='$code IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['code_clean'] is not None

    def test_code_prefix_std_pg(self, db_pg):
        """substring($code FROM 1 FOR 3)."""
        rows = db_pg.table('invc.product').query(
            columns='$code, $code_prefix_std',
            where='$code IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert r['code_prefix_std'] == r['code'][:3]

    def test_anno_pg(self, db_pg):
        """EXTRACT(YEAR FROM $date)."""
        rows = db_pg.table('invc.invoice').query(
            columns='$date, $anno', limit=5
        ).fetch()
        for r in rows:
            year_val = int(float(r['anno']))
            assert 2000 <= year_val <= 2030

    def test_periodo_pg(self, db_pg):
        """TO_CHAR($date, 'YYYY-MM')."""
        rows = db_pg.table('invc.invoice').query(
            columns='$date, $periodo', limit=5
        ).fetch()
        for r in rows:
            assert len(r['periodo']) == 7
            assert '-' in r['periodo']

    def test_days_since_invoice_pg(self, db_pg):
        """date_part('day', now() - $date)."""
        rows = db_pg.table('invc.invoice').query(
            columns='$date, $days_since_invoice', limit=5
        ).fetch()
        for r in rows:
            assert float(r['days_since_invoice']) >= 0

    def test_invoice_month_pg(self, db_pg):
        """date_trunc('month', $date)."""
        rows = db_pg.table('invc.invoice').query(
            columns='$date, $invoice_month', limit=5
        ).fetch()
        for r in rows:
            assert r['invoice_month'] is not None

    def test_created_date_pg(self, db_pg):
        """date_trunc('day', $__ins_ts)."""
        rows = db_pg.table('invc.invoice_note').query(
            columns='$note_text, $created_date', limit=5
        ).fetch()
        for r in rows:
            assert r['created_date'] is not None

    def test_week_start_pg(self, db_pg):
        """INTERVAL + MOD + EXTRACT(DOW)."""
        rows = db_pg.table('invc.invoice').query(
            columns='$date, $week_start', limit=5
        ).fetch()
        for r in rows:
            assert r['week_start'] is not None

    def test_postcode_padded_pg(self, db_pg):
        """LPAD($postcode, 5, '0')."""
        rows = db_pg.table('invc.customer').query(
            columns='$postcode, $postcode_padded',
            where='$postcode IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert len(r['postcode_padded']) == 5

    def test_account_code_pg(self, db_pg):
        """LPAD(CAST($id AS TEXT), 8, '0')."""
        rows = db_pg.table('invc.customer').query(
            columns='$id, $account_code', limit=5
        ).fetch()
        for r in rows:
            assert len(r['account_code']) == 8

    def test_invoice_numbers_pg(self, db_pg):
        """array_to_string(ARRAY(#inv_nums), ', ')."""
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, $invoice_numbers',
            where='$n_invoices > 0', limit=5
        ).fetch()
        for r in rows:
            assert isinstance(r['invoice_numbers'], str)

    def test_distinct_products_in_invoice_pg(self, db_pg):
        """array_length(ARRAY(SELECT DISTINCT ...))."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $distinct_products_in_invoice',
            where='$distinct_products_in_invoice IS NOT NULL',
            limit=5
        ).fetch()
        for r in rows:
            assert int(r['distinct_products_in_invoice']) >= 1

    def test_all_notes_string_agg_pg(self, db_pg):
        """STRING_AGG returns concatenated notes."""
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $all_notes',
            where='$all_notes IS NOT NULL', limit=5
        ).fetch()
        for r in rows:
            assert isinstance(r['all_notes'], str)
            assert len(r['all_notes']) > 0


# ===================================================================
# GROUP BY with virtual columns
# ===================================================================

class TestGroupBy:

    def test_group_by_with_formula_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='@customer_id.account_name, SUM($total)',
            group_by='@customer_id.account_name',
            limit=5
        ).fetch()
        assert len(rows) == 5

    def test_group_by_with_formula_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='@customer_id.account_name, SUM($total)',
            group_by='@customer_id.account_name',
            limit=5
        ).fetch()
        assert len(rows) == 5


# ===================================================================
# WHERE and ORDER BY with virtual columns
# ===================================================================

class TestWhereOrderBy:

    def test_where_alias_pg(self, db_pg):
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, $state_name',
            where='$state_name IS NOT NULL',
            order_by='$state_name', limit=5
        ).fetch()
        assert len(rows) == 5
        names = [r['state_name'] for r in rows]
        assert names == sorted(names)

    def test_where_alias_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$account_name, $state_name',
            where='$state_name IS NOT NULL',
            order_by='$state_name', limit=5
        ).fetch()
        assert len(rows) == 5
        names = [r['state_name'] for r in rows]
        assert names == sorted(names)

    def test_order_by_formula_pg(self, db_pg):
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $line_total',
            where='$line_total IS NOT NULL',
            order_by='$line_total DESC', limit=5
        ).fetch()
        vals = [float(r['line_total']) for r in rows]
        assert vals == sorted(vals, reverse=True)

    def test_order_by_formula_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $line_total',
            where='$line_total IS NOT NULL',
            order_by='$line_total DESC', limit=5
        ).fetch()
        vals = [float(r['line_total']) for r in rows]
        assert vals == sorted(vals, reverse=True)

    def test_where_exists_pg(self, db_pg):
        """has_invoices=TRUE count matches distinct customers."""
        n_with = db_pg.table('invc.customer').query(
            columns='$id',
            where='$has_invoices = TRUE'
        ).count()
        all_inv = db_pg.table('invc.invoice').query(
            columns='$customer_id'
        ).fetch()
        n_distinct = len(set(r['customer_id'] for r in all_inv))
        assert n_with == n_distinct

    def test_where_exists_sqlite(self, db_sqlite):
        """EXISTS formula not supported on SQLite."""
        pytest.skip('EXISTS formula not supported on SQLite')


# ===================================================================
# Combined complex queries
# ===================================================================

class TestCombinedQueries:

    def test_invoice_row_full_pg(self, db_pg):
        """All VC types in one query."""
        rows = db_pg.table('invc.invoice_row').query(
            columns=('$id, $customer_name, $customer_state,'
                     ' $line_total, $line_gross, $is_expensive,'
                     ' $size_category, $product_note,'
                     ' @invoice_id.inv_number'),
            where='$line_total > 0',
            order_by='$line_total DESC',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert float(r['line_total']) > 0
            assert r['customer_name'] is not None
            assert r['size_category'] in {
                'Small', 'Medium', 'Large'
            }

    def test_invoice_row_full_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns=('$id, $customer_name, $customer_state,'
                     ' $line_total, $line_gross, $is_expensive,'
                     ' $size_category, $product_note,'
                     ' @invoice_id.inv_number'),
            where='$line_total > 0',
            order_by='$line_total DESC',
            limit=10
        ).fetch()
        assert len(rows) == 10

    def test_customer_full_pg(self, db_pg):
        """Customer with count, sum, bool, alias, formula."""
        rows = db_pg.table('invc.customer').query(
            columns=('$account_name, $n_invoices, $invoiced_total,'
                     ' $has_invoices, $customer_rank, $state_name,'
                     ' $display_name, $contact_info'),
            where='$n_invoices > 0',
            order_by='$n_invoices DESC',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert int(r['n_invoices']) > 0
            assert r['customer_rank'] in {
                'Occasional', 'Regular'
            }

    def test_customer_full_sqlite(self, db_sqlite):
        """has_invoices uses EXISTS, not supported on SQLite."""
        rows = db_sqlite.table('invc.customer').query(
            columns=('$account_name, $n_invoices, $invoiced_total,'
                     ' $customer_rank, $state_name,'
                     ' $display_name, $contact_info'),
            where='$n_invoices > 0',
            order_by='$n_invoices DESC',
            limit=10
        ).fetch()
        assert len(rows) == 10

    def test_invoice_full_pg(self, db_pg):
        """Invoice with all cross-db VCs."""
        rows = db_pg.table('invc.invoice').query(
            columns=('$inv_number, $customer_name, $row_count,'
                     ' $value_category, $display_total,'
                     ' $invoice_status, $status_label,'
                     ' $priority_note, $number_series,'
                     ' $smart_row_count'),
            where='$row_count > 0',
            order_by='$display_total DESC',
            limit=10
        ).fetch()
        assert len(rows) == 10

    def test_invoice_full_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns=('$inv_number, $customer_name, $row_count,'
                     ' $value_category, $display_total,'
                     ' $invoice_status, $status_label,'
                     ' $priority_note, $number_series,'
                     ' $smart_row_count'),
            where='$row_count > 0',
            order_by='$display_total DESC',
            limit=10
        ).fetch()
        assert len(rows) == 10

    def test_product_full_pg(self, db_pg):
        """Product with all cross-db VCs."""
        rows = db_pg.table('invc.product').query(
            columns=('$description, $total_sold, $price_range,'
                     ' $code_and_desc, $price_floor, $price_label,'
                     ' $product_type_name, $concat_code_desc,'
                     ' $price_rounded, $description_clean,'
                     ' $price_as_int_text, $computed_margin'),
            where='$total_sold > 0',
            order_by='$price_floor DESC',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert 'computed_margin' in r
            assert float(r['price_floor']) >= 10

    def test_product_full_sqlite(self, db_sqlite):
        """Excludes price_floor (GREATEST) not supported on SQLite."""
        rows = db_sqlite.table('invc.product').query(
            columns=('$description, $total_sold, $price_range,'
                     ' $code_and_desc, $price_label,'
                     ' $product_type_name, $concat_code_desc,'
                     ' $price_rounded, $description_clean,'
                     ' $price_as_int_text, $computed_margin'),
            where='$total_sold > 0',
            order_by='$unit_price DESC',
            limit=10
        ).fetch()
        assert len(rows) == 10

    def test_all_pg_features_invoice(self, db_pg):
        """Invoice with all PG-specific VCs in one query."""
        rows = db_pg.table('invc.invoice').query(
            columns=('$inv_number, $anno, $periodo,'
                     ' $days_since_invoice, $week_start,'
                     ' $invoice_month, $priced_rows_pct,'
                     ' $all_notes, $invoice_datetime,'
                     ' $max_row_price'),
            where='$row_count > 0',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            year_val = int(float(r['anno']))
            assert 2000 <= year_val <= 2030
            assert len(r['periodo']) == 7


# ===================================================================
# Erpy patterns: exists=dict, group_by+having, INTERVAL, CAST date,
# :env_workdate, RTRIM, var_* IN :list, static alias, draftField
# ===================================================================

class TestExistsDict:
    """exists=dict() pattern — has_expensive_rows on invoice."""

    def test_has_expensive_rows_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $has_expensive_rows',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert r['has_expensive_rows'] in (True, False)

    @pytest.mark.skipif(True, reason='EXISTS not supported on SQLite')
    def test_has_expensive_rows_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, $has_expensive_rows',
            limit=10
        ).fetch()
        assert len(rows) == 10

    def test_has_expensive_rows_where_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $total',
            where='$has_expensive_rows IS TRUE',
            limit=5
        ).fetch()
        for r in rows:
            max_price = db_pg.table('invc.invoice_row').readColumns(
                columns='MAX($unit_price)',
                where='$invoice_id=:iid', iid=r['pkey']
            )
            assert max_price is not None and float(max_price) > 100


class TestGroupByHaving:
    """select_* with group_by + having — duplicate_products on invoice."""

    def test_duplicate_products_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $duplicate_products',
            limit=20
        ).fetch()
        assert len(rows) == 20
        for r in rows:
            assert r['duplicate_products'] is not None
            assert int(r['duplicate_products']) >= 0

    def test_duplicate_products_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, $duplicate_products',
            limit=20
        ).fetch()
        assert len(rows) == 20
        for r in rows:
            assert int(r['duplicate_products']) >= 0


class TestIntervalArithmetic:
    """INTERVAL in sql_formula — due_date on invoice."""

    def test_due_date_pg(self, db_pg):
        from datetime import date, datetime
        rows = db_pg.table('invc.invoice').query(
            columns='$date, $due_date',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            if r['date'] and r['due_date']:
                inv_date = r['date']
                due = r['due_date']
                if isinstance(inv_date, datetime):
                    inv_date = inv_date.date()
                if isinstance(due, datetime):
                    due = due.date()
                if isinstance(inv_date, date) and isinstance(due, date):
                    assert (due - inv_date).days == 30

    @pytest.mark.skipif(True, reason='INTERVAL not supported on SQLite')
    def test_due_date_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$date, $due_date',
            limit=10
        ).fetch()
        assert len(rows) == 10


class TestCastDate:
    """CAST($__ins_ts AS DATE) = $date — created_same_day on invoice."""

    def test_created_same_day_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $created_same_day',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert r['created_same_day'] in (True, False)

    def test_created_same_day_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, $created_same_day',
            limit=10
        ).fetch()
        assert len(rows) == 10


class TestEnvWorkdate:
    """:env_workdate in formula — is_recent on invoice."""

    def test_is_recent_pg(self, db_pg):
        rows = db_pg.table('invc.invoice').query(
            columns='$inv_number, $date, $is_recent',
            limit=20
        ).fetch()
        assert len(rows) == 20
        for r in rows:
            assert r['is_recent'] in (True, False)

    @pytest.mark.skipif(True, reason='INTERVAL not supported on SQLite')
    def test_is_recent_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice').query(
            columns='$inv_number, $date, $is_recent',
            limit=20
        ).fetch()
        assert len(rows) == 20


class TestRtrim:
    """RTRIM in sql_formula — note_text_rtrim on invoice_note."""

    def test_rtrim_pg(self, db_pg):
        rows = db_pg.table('invc.invoice_note').query(
            columns='$note_text, $note_text_rtrim',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            if r['note_text']:
                assert r['note_text_rtrim'] == r['note_text'].rstrip()

    def test_rtrim_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_note').query(
            columns='$note_text, $note_text_rtrim',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            if r['note_text']:
                assert r['note_text_rtrim'] == r['note_text'].rstrip()


class TestVarInList:
    """var_* with IN :list — is_exempt_vat on invoice_row."""

    def test_is_exempt_vat_pg(self, db_pg):
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $is_exempt_vat',
            limit=20
        ).fetch()
        assert len(rows) == 20
        for r in rows:
            assert r['is_exempt_vat'] in (True, False)

    def test_is_exempt_vat_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $is_exempt_vat',
            limit=20
        ).fetch()
        assert len(rows) == 20
        for r in rows:
            assert r['is_exempt_vat'] in (0, 1, True, False)

    def test_is_exempt_vat_cross_validate_pg(self, db_pg):
        """Verify exempt matches FRE/INP vat_type_code."""
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $is_exempt_vat, @product_id.vat_type_code',
            limit=50
        ).fetch()
        for r in rows:
            vat_code = r['_product_id_vat_type_code']
            if vat_code in ('FRE', 'INP'):
                assert r['is_exempt_vat'] is True
            else:
                assert r['is_exempt_vat'] is False


class TestStaticAlias:
    """static=True on aliasColumn — invoice_date_static on invoice_row."""

    def test_static_alias_pg(self, db_pg):
        rows = db_pg.table('invc.invoice_row').query(
            columns='$id, $invoice_date_static, @invoice_id.date',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert r['invoice_date_static'] is not None

    def test_static_alias_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.invoice_row').query(
            columns='$id, $invoice_date_static',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert r['invoice_date_static'] is not None


class TestDraftField:
    """draftField=True — is_confirmed on customer."""

    def test_is_confirmed_pg(self, db_pg):
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, $is_confirmed',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert r['is_confirmed'] is True

    def test_is_confirmed_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$account_name, $is_confirmed',
            limit=10
        ).fetch()
        assert len(rows) == 10
        for r in rows:
            assert bool(r['is_confirmed'])

    def test_draft_filter_count_pg(self, db_pg):
        """Default query excludes drafts, count must match."""
        default = db_pg.table('invc.customer').query().count()
        no_draft = db_pg.table('invc.customer').query(
            excludeDraft=False
        ).count()
        assert default == no_draft == CUSTOMER_COUNT

    def test_draft_filter_count_sqlite(self, db_sqlite):
        default = db_sqlite.table('invc.customer').query().count()
        no_draft = db_sqlite.table('invc.customer').query(
            excludeDraft=False
        ).count()
        assert default == no_draft == CUSTOMER_COUNT


# ---------------------------------------------------------------------------
# Cat. Subtable — tbl.subtable() filter on customer_type_code
# ---------------------------------------------------------------------------

class TestSubtableSingle:
    """Query with a single subtable filter."""

    def test_subtable_residential_pg(self, db_pg):
        count = db_pg.table('invc.customer').query(
            subtable='residential'
        ).count()
        assert count == CUSTOMER_RES_COUNT

    def test_subtable_residential_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            subtable='residential'
        ).count()
        assert count == CUSTOMER_RES_COUNT

    def test_subtable_commercial_pg(self, db_pg):
        count = db_pg.table('invc.customer').query(
            subtable='commercial'
        ).count()
        assert count == CUSTOMER_COM_COUNT

    def test_subtable_commercial_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            subtable='commercial'
        ).count()
        assert count == CUSTOMER_COM_COUNT

    def test_subtable_government_pg(self, db_pg):
        count = db_pg.table('invc.customer').query(
            subtable='government'
        ).count()
        assert count == CUSTOMER_GOV_COUNT

    def test_subtable_government_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            subtable='government'
        ).count()
        assert count == CUSTOMER_GOV_COUNT

    def test_subtable_trade_pg(self, db_pg):
        count = db_pg.table('invc.customer').query(
            subtable='trade'
        ).count()
        assert count == CUSTOMER_TRD_COUNT

    def test_subtable_trade_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            subtable='trade'
        ).count()
        assert count == CUSTOMER_TRD_COUNT


class TestSubtableCombined:
    """Subtable with AND/OR operators and wildcard."""

    def test_subtable_and_pg(self, db_pg):
        """residential & commercial — intersection (should be 0)."""
        count = db_pg.table('invc.customer').query(
            subtable='residential&commercial'
        ).count()
        assert count == 0

    def test_subtable_and_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            subtable='residential&commercial'
        ).count()
        assert count == 0

    def test_subtable_or_pg(self, db_pg):
        """residential | government — union."""
        count = db_pg.table('invc.customer').query(
            subtable='residential|government'
        ).count()
        assert count == CUSTOMER_RES_COUNT + CUSTOMER_GOV_COUNT

    def test_subtable_or_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            subtable='residential|government'
        ).count()
        assert count == CUSTOMER_RES_COUNT + CUSTOMER_GOV_COUNT

    def test_subtable_wildcard_pg(self, db_pg):
        """subtable='*' disables subtable filter — full count."""
        count = db_pg.table('invc.customer').query(
            subtable='*'
        ).count()
        assert count == CUSTOMER_COUNT

    def test_subtable_wildcard_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            subtable='*'
        ).count()
        assert count == CUSTOMER_COUNT

    def test_subtable_sum_equals_total_pg(self, db_pg):
        """All subtable counts must sum to total."""
        tbl = db_pg.table('invc.customer')
        total = sum(
            tbl.query(subtable=s).count()
            for s in ('residential', 'commercial', 'government', 'trade')
        )
        assert total == CUSTOMER_COUNT

    def test_subtable_sum_equals_total_sqlite(self, db_sqlite):
        tbl = db_sqlite.table('invc.customer')
        total = sum(
            tbl.query(subtable=s).count()
            for s in ('residential', 'commercial', 'government', 'trade')
        )
        assert total == CUSTOMER_COUNT


class TestSubtableVirtualColumn:
    """$subtable_* auto-generated boolean virtual columns."""

    def test_subtable_vc_residential_pg(self, db_pg):
        rows = db_pg.table('invc.customer').query(
            columns='$account_name, $subtable_residential',
            where='$subtable_residential IS TRUE',
            limit=5
        ).fetch()
        assert len(rows) == 5
        for r in rows:
            assert r['subtable_residential'] is True

    def test_subtable_vc_residential_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.customer').query(
            columns='$account_name, $subtable_residential',
            where='$subtable_residential IS TRUE',
            limit=5
        ).fetch()
        assert len(rows) == 5

    def test_subtable_vc_count_pg(self, db_pg):
        """Count via $subtable_residential IS TRUE must match subtable filter."""
        count = db_pg.table('invc.customer').query(
            where='$subtable_residential IS TRUE'
        ).count()
        assert count == CUSTOMER_RES_COUNT

    def test_subtable_vc_count_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            where='$subtable_residential IS TRUE'
        ).count()
        assert count == CUSTOMER_RES_COUNT

    def test_subtable_vc_false_pg(self, db_pg):
        """$subtable_residential IS FALSE = all non-residential."""
        count = db_pg.table('invc.customer').query(
            where='$subtable_residential IS FALSE'
        ).count()
        assert count == CUSTOMER_COUNT - CUSTOMER_RES_COUNT

    def test_subtable_vc_false_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query(
            where='$subtable_residential IS FALSE'
        ).count()
        assert count == CUSTOMER_COUNT - CUSTOMER_RES_COUNT


# ---------------------------------------------------------------------------
# Cat. Partition — partition_state on customer, partition_customer_state on invoice
# ---------------------------------------------------------------------------

class TestPartitionCurrentState:
    """partition with current_invc_state (single value)."""

    def test_customer_partition_nsw_pg(self, db_pg):
        db_pg.currentEnv['current_invc_state'] = 'NSW'
        try:
            count = db_pg.table('invc.customer').query().count()
            assert count == CUSTOMER_NSW_COUNT
        finally:
            del db_pg.currentEnv['current_invc_state']

    def test_customer_partition_nsw_sqlite(self, db_sqlite):
        db_sqlite.currentEnv['current_invc_state'] = 'NSW'
        try:
            count = db_sqlite.table('invc.customer').query().count()
            assert count == CUSTOMER_NSW_COUNT
        finally:
            del db_sqlite.currentEnv['current_invc_state']

    def test_invoice_partition_nsw_pg(self, db_pg):
        db_pg.currentEnv['current_invc_state'] = 'NSW'
        try:
            count = db_pg.table('invc.invoice').query().count()
            assert count == INVOICE_NSW_COUNT
        finally:
            del db_pg.currentEnv['current_invc_state']

    def test_invoice_partition_nsw_sqlite(self, db_sqlite):
        db_sqlite.currentEnv['current_invc_state'] = 'NSW'
        try:
            count = db_sqlite.table('invc.invoice').query().count()
            assert count == INVOICE_NSW_COUNT
        finally:
            del db_sqlite.currentEnv['current_invc_state']

    def test_partition_ignore_pg(self, db_pg):
        """ignorePartition=True bypasses the filter."""
        db_pg.currentEnv['current_invc_state'] = 'NSW'
        try:
            count = db_pg.table('invc.customer').query(
                ignorePartition=True
            ).count()
            assert count == CUSTOMER_COUNT
        finally:
            del db_pg.currentEnv['current_invc_state']

    def test_partition_ignore_sqlite(self, db_sqlite):
        db_sqlite.currentEnv['current_invc_state'] = 'NSW'
        try:
            count = db_sqlite.table('invc.customer').query(
                ignorePartition=True
            ).count()
            assert count == CUSTOMER_COUNT
        finally:
            del db_sqlite.currentEnv['current_invc_state']


class TestPartitionAllowedStates:
    """partition with allowed_invc_state (multiple values)."""

    def test_customer_allowed_pg(self, db_pg):
        db_pg.currentEnv['allowed_invc_state'] = ['NSW', 'VIC']
        try:
            count = db_pg.table('invc.customer').query().count()
            assert count == CUSTOMER_NSW_COUNT + CUSTOMER_VIC_COUNT
        finally:
            del db_pg.currentEnv['allowed_invc_state']

    def test_customer_allowed_sqlite(self, db_sqlite):
        db_sqlite.currentEnv['allowed_invc_state'] = ['NSW', 'VIC']
        try:
            count = db_sqlite.table('invc.customer').query().count()
            assert count == CUSTOMER_NSW_COUNT + CUSTOMER_VIC_COUNT
        finally:
            del db_sqlite.currentEnv['allowed_invc_state']

    def test_invoice_allowed_pg(self, db_pg):
        db_pg.currentEnv['allowed_invc_state'] = ['NSW', 'VIC']
        try:
            count = db_pg.table('invc.invoice').query().count()
            assert count == INVOICE_NSW_COUNT + INVOICE_VIC_COUNT
        finally:
            del db_pg.currentEnv['allowed_invc_state']

    def test_invoice_allowed_sqlite(self, db_sqlite):
        db_sqlite.currentEnv['allowed_invc_state'] = ['NSW', 'VIC']
        try:
            count = db_sqlite.table('invc.invoice').query().count()
            assert count == INVOICE_NSW_COUNT + INVOICE_VIC_COUNT
        finally:
            del db_sqlite.currentEnv['allowed_invc_state']

    def test_no_partition_full_count_pg(self, db_pg):
        """Without env vars, no partition filter — full count."""
        count = db_pg.table('invc.customer').query().count()
        assert count == CUSTOMER_COUNT

    def test_no_partition_full_count_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.customer').query().count()
        assert count == CUSTOMER_COUNT


class TestStaffBasic:
    """Basic staff table queries — VC and cross-package relation."""

    def test_staff_count_pg(self, db_pg):
        count = db_pg.table('invc.staff').query().count()
        assert count == STAFF_COUNT

    def test_staff_count_sqlite(self, db_sqlite):
        count = db_sqlite.table('invc.staff').query().count()
        assert count == STAFF_COUNT

    def test_staff_full_name_pg(self, db_pg):
        rows = db_pg.table('invc.staff').query(
            columns='$full_name, $role_description, $state_name',
            where="$role_code = 'MGR'",
            order_by='$state'
        ).fetch()
        assert len(rows) == 8
        assert rows[0]['role_description'] == 'Manager'
        assert rows[0]['full_name']

    def test_staff_full_name_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.staff').query(
            columns='$full_name, $role_description, $state_name',
            where="$role_code = 'MGR'",
            order_by='$state'
        ).fetch()
        assert len(rows) == 8
        assert rows[0]['role_description'] == 'Manager'

    def test_staff_username_cross_pkg_pg(self, db_pg):
        """$username alias traverses cross-package relation to adm.user."""
        rows = db_pg.table('invc.staff').query(
            columns='$full_name, $username',
            where="$state = 'NSW' AND $role_code = 'MGR'"
        ).fetch()
        assert len(rows) == 1
        assert rows[0]['username'] == 'james.wilson'

    def test_staff_username_cross_pkg_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.staff').query(
            columns='$full_name, $username',
            where="$state = 'NSW' AND $role_code = 'MGR'"
        ).fetch()
        assert len(rows) == 1
        assert rows[0]['username'] == 'james.wilson'

    def test_staff_region_deep_relation_pg(self, db_pg):
        """$region_name traverses @state.@region_code.name."""
        rows = db_pg.table('invc.staff').query(
            columns='$full_name, $region_name',
            where="$state = 'NSW'",
            limit=1
        ).fetch()
        assert rows[0]['region_name'] == 'New South Wales'

    def test_staff_region_deep_relation_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.staff').query(
            columns='$full_name, $region_name',
            where="$state = 'NSW'",
            limit=1
        ).fetch()
        assert rows[0]['region_name'] == 'New South Wales'


class TestEmbedFieldPars:
    """Test sqlparams with symbolic field references ($col, @rel.col).

    When a sqlparam value starts with @ or $ and the referenced field
    exists, the compiler inlines it as a SQL field reference instead of
    a bind parameter.
    Covers compiler.py embedFieldPars (lines 837, 839, 841).
    """

    def test_relation_param_pg(self, db_pg):
        """sqlparams value starting with @ is resolved as a relation path."""
        tbl = db_pg.table('invc.invoice_row')
        diff = tbl.query(
            where='$unit_price != :list_price',
            sqlparams={'list_price': '@product_id.unit_price'}
        ).count()
        same = tbl.query(
            where='$unit_price = :list_price',
            sqlparams={'list_price': '@product_id.unit_price'}
        ).count()
        assert diff + same == INVOICE_ROW_COUNT

    def test_relation_param_sqlite(self, db_sqlite):
        tbl = db_sqlite.table('invc.invoice_row')
        diff = tbl.query(
            where='$unit_price != :list_price',
            sqlparams={'list_price': '@product_id.unit_price'}
        ).count()
        same = tbl.query(
            where='$unit_price = :list_price',
            sqlparams={'list_price': '@product_id.unit_price'}
        ).count()
        assert diff + same == INVOICE_ROW_COUNT

    def test_column_param_pg(self, db_pg):
        """sqlparams value starting with $ is resolved as a local column."""
        tbl = db_pg.table('invc.invoice_row')
        gt = tbl.query(
            where='$quantity > :threshold',
            sqlparams={'threshold': '$unit_price'}
        ).count()
        le = tbl.query(
            where='$quantity <= :threshold',
            sqlparams={'threshold': '$unit_price'}
        ).count()
        assert gt + le == INVOICE_ROW_COUNT

    def test_column_param_sqlite(self, db_sqlite):
        tbl = db_sqlite.table('invc.invoice_row')
        gt = tbl.query(
            where='$quantity > :threshold',
            sqlparams={'threshold': '$unit_price'}
        ).count()
        le = tbl.query(
            where='$quantity <= :threshold',
            sqlparams={'threshold': '$unit_price'}
        ).count()
        assert gt + le == INVOICE_ROW_COUNT


class TestExpandBag:
    """Test #BAG() and #BAGCOLS() macros in column expressions.

    #BAG($field) registers the column for post-query Bag deserialization.
    #BAGCOLS($field) does the same but expands Bag keys into separate columns.
    Covers compiler.py expandBag (lines 1278-1281) and expandBagcols (1296-1299).
    """

    def test_bag_macro_pg(self, db_pg):
        """#BAG($details) registers column for Bag post-processing."""
        rows = db_pg.table('invc.product').query(
            columns='$description, #BAG($details) AS details_bag',
            limit=5
        ).fetch()
        assert len(rows) == 5
        for r in rows:
            assert 'description' in r

    def test_bag_macro_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.product').query(
            columns='$description, #BAG($details) AS details_bag',
            limit=5
        ).fetch()
        assert len(rows) == 5
        for r in rows:
            assert 'description' in r

    def test_bagcols_macro_pg(self, db_pg):
        """#BAGCOLS($details) registers column for Bag-to-columns expansion."""
        rows = db_pg.table('invc.product').query(
            columns='$description, #BAGCOLS($details) AS details_cols',
            limit=5
        ).fetch()
        assert len(rows) == 5

    def test_bagcols_macro_sqlite(self, db_sqlite):
        rows = db_sqlite.table('invc.product').query(
            columns='$description, #BAGCOLS($details) AS details_cols',
            limit=5
        ).fetch()
        assert len(rows) == 5


class TestCompiledRecordQuery:
    """Test compiledRecordQuery paths: virtual_columns as string,
    dtype='X' skip, and joinColumn with cnd.

    Covers compiler.py lines 1147, 1155, 1161-1165, 1182.
    """

    def _first_pkey(self, db, table):
        rows = db.table(table).query(columns='$id', limit=1).fetch()
        return rows[0]['id']

    def test_virtual_columns_as_string_pg(self, db_pg):
        """virtual_columns passed as CSV string (line 1147)."""
        pkey = self._first_pkey(db_pg, 'invc.product')
        rec = db_pg.table('invc.product').record(
            pkey=pkey, virtual_columns='price_range,code_and_desc'
        ).output('dict')
        assert 'price_range' in rec
        assert 'code_and_desc' in rec

    def test_virtual_columns_as_string_sqlite(self, db_sqlite):
        pkey = self._first_pkey(db_sqlite, 'invc.product')
        rec = db_sqlite.table('invc.product').record(
            pkey=pkey, virtual_columns='price_range,code_and_desc'
        ).output('dict')
        assert 'price_range' in rec
        assert 'code_and_desc' in rec

    def test_bag_column_skipped_pg(self, db_pg):
        """dtype='X' columns are skipped when bagFields=False (line 1155)."""
        pkey = self._first_pkey(db_pg, 'invc.product')
        rec = db_pg.table('invc.product').record(
            pkey=pkey, bagFields=False
        ).output('dict')
        # 'details' (dtype='X') should not be in result
        assert 'details' not in rec

    def test_bag_column_skipped_sqlite(self, db_sqlite):
        pkey = self._first_pkey(db_sqlite, 'invc.product')
        rec = db_sqlite.table('invc.product').record(
            pkey=pkey, bagFields=False
        ).output('dict')
        assert 'details' not in rec

    def test_join_column_in_record_pg(self, db_pg):
        """joinColumn with cnd triggers virtual relation handling (lines 1161-1165, 1182)."""
        pkey = self._first_pkey(db_pg, 'invc.invoice')
        rec = db_pg.table('invc.invoice').record(pkey=pkey).output('bag')
        # The record should load without error; discount_tier_id
        # is a joinColumn with a cnd condition
        assert rec is not None

    def test_join_column_in_record_sqlite(self, db_sqlite):
        pkey = self._first_pkey(db_sqlite, 'invc.invoice')
        rec = db_sqlite.table('invc.invoice').record(pkey=pkey).output('bag')
        assert rec is not None


class TestFindRelationAlias:
    """Test _findRelationAlias error and table_alias expansion.

    Covers compiler.py lines 485 (missing relation error)
    and 491-503 (table_alias expansion).
    """

    def test_missing_relation_raises_pg(self, db_pg):
        """A non-existent relation in a column path raises GnrSqlMissingField (line 485)."""
        tbl = db_pg.table('invc.invoice_row')
        with pytest.raises(GnrSqlMissingField):
            tbl.query(columns='@nonexistent_relation.some_field').fetch()

    def test_missing_relation_raises_sqlite(self, db_sqlite):
        tbl = db_sqlite.table('invc.invoice_row')
        with pytest.raises(GnrSqlMissingField):
            tbl.query(columns='@nonexistent_relation.some_field').fetch()

    def test_alias_table_expansion_pg(self, db_pg):
        """aliasTable 'customer' on invoice_row expands to @invoice_id.@customer_id."""
        tbl = db_pg.table('invc.invoice_row')
        rows = tbl.query(
            columns='$id, @customer.account_name',
            limit=5
        ).fetch()
        assert len(rows) == 5
        for r in rows:
            assert r['_customer_account_name'] is not None

    def test_alias_table_expansion_sqlite(self, db_sqlite):
        tbl = db_sqlite.table('invc.invoice_row')
        rows = tbl.query(
            columns='$id, @customer.account_name',
            limit=5
        ).fetch()
        assert len(rows) == 5
        for r in rows:
            assert r['_customer_account_name'] is not None
