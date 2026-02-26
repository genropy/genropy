"""Tests for RuntimeModel — temporary virtual columns and relations."""

import pytest


class TestRuntimeModelFactory:
    """Test db.runtimeModel() factory."""

    def test_factory_returns_runtime_model(self, db):
        rm = db.runtimeModel()
        from gnr.sql.gnrsql.runtime_model import RuntimeModel
        assert isinstance(rm, RuntimeModel)

    def test_table_proxy(self, db):
        rm = db.runtimeModel()
        proxy = rm.table('invc.customer')
        from gnr.sql.gnrsql.runtime_model import RuntimeTableProxy
        assert isinstance(proxy, RuntimeTableProxy)


class TestFormulaColumn:
    """Test runtime formulaColumn with subselect."""

    def test_count_formula(self, db):
        rm = db.runtimeModel()
        rm.table('invc.customer').formulaColumn(
            'rt_n_invoices', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where='$customer_id=#THIS.id'),
        )
        with rm:
            result = db.query(
                'invc.customer',
                columns='$account_name, $rt_n_invoices',
            ).fetch()
        assert len(result) > 0
        for row in result:
            assert 'rt_n_invoices' in row

    def test_sum_formula(self, db):
        rm = db.runtimeModel()
        rm.table('invc.customer').formulaColumn(
            'rt_total', dtype='N',
            select=dict(table='invc.invoice',
                        columns='SUM($total)',
                        where='$customer_id=#THIS.id'),
        )
        with rm:
            result = db.query(
                'invc.customer',
                columns='$account_name, $rt_total',
            ).fetch()
        assert len(result) > 0


class TestInvisibleOutside:
    """Runtime columns must not be visible outside the with block."""

    def test_invisible_outside(self, db):
        rm = db.runtimeModel()
        rm.table('invc.customer').formulaColumn(
            'rt_ghost', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where='$customer_id=#THIS.id'),
        )
        with rm:
            result = db.query(
                'invc.customer',
                columns='$account_name, $rt_ghost',
            ).fetch()
            assert len(result) > 0

        with pytest.raises(Exception):
            db.query(
                'invc.customer',
                columns='$account_name, $rt_ghost',
            ).fetch()


class TestNoModelPollution:
    """Static model must not be affected by runtime columns."""

    def test_static_model_unchanged(self, db):
        tbl_obj = db.model.table('customer', pkg='invc')
        static_vc = tbl_obj['virtual_columns']
        original_keys = set(static_vc.keys()) if static_vc else set()

        rm = db.runtimeModel()
        rm.table('invc.customer').formulaColumn(
            'rt_pollution_test', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where='$customer_id=#THIS.id'),
        )
        with rm:
            pass

        after_keys = set(static_vc.keys()) if static_vc else set()
        assert original_keys == after_keys


class TestReuseRuntimeModel:
    """Same RuntimeModel can be used in multiple with blocks."""

    def test_reuse(self, db):
        rm = db.runtimeModel()
        rm.table('invc.customer').formulaColumn(
            'rt_reuse', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where='$customer_id=#THIS.id'),
        )

        with rm:
            r1 = db.query(
                'invc.customer',
                columns='$account_name, $rt_reuse',
            ).fetch()

        with rm:
            r2 = db.query(
                'invc.customer',
                columns='$account_name, $rt_reuse',
            ).fetch()

        assert len(r1) == len(r2)


class TestTwoTables:
    """Runtime columns on multiple tables in the same RuntimeModel."""

    def test_two_tables(self, db):
        rm = db.runtimeModel()
        rm.table('invc.customer').formulaColumn(
            'rt_n_inv', dtype='L',
            select=dict(table='invc.invoice',
                        columns='COUNT(*)',
                        where='$customer_id=#THIS.id'),
        )
        rm.table('invc.product').formulaColumn(
            'rt_n_rows', dtype='L',
            select=dict(table='invc.invoice_row',
                        columns='COUNT(*)',
                        where='$product_id=#THIS.id'),
        )
        with rm:
            customers = db.query(
                'invc.customer',
                columns='$account_name, $rt_n_inv',
            ).fetch()
            products = db.query(
                'invc.product',
                columns='$description, $rt_n_rows',
            ).fetch()
        assert len(customers) > 0
        assert len(products) > 0


class TestSqlFormula:
    """Runtime columns with sql_formula instead of subselect."""

    def test_sql_formula(self, db):
        rm = db.runtimeModel()
        rm.table('invc.customer').formulaColumn(
            'rt_upper_name', dtype='T',
            sql_formula="UPPER($account_name)",
        )
        with rm:
            result = db.query(
                'invc.customer',
                columns='$account_name, $rt_upper_name',
            ).fetch()
        assert len(result) > 0
        for row in result:
            if row['account_name']:
                assert row['rt_upper_name'] == row['account_name'].upper()
