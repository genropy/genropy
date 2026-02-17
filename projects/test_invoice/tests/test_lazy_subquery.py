"""Test lazy subquery rendering via enable_lazy_subquery=True.

Each test queries the same columns twice:
  1. default (eager rendering — SQL generated immediately)
  2. lazy (enable_lazy_subquery=True — placeholder + deferred resolution)
and asserts the results are identical.

This validates that the intermediate representation (IR) produces
the exact same SQL output as the direct rendering path.
"""


class TestLazyFormulaInline:
    """Lazy rendering of formula columns with inline subquery."""

    def test_n_invoices(self, db):
        cols = '$account_name,$n_invoices'
        r_eager = db.query('invc.customer', columns=cols,
                           order_by='$id', limit=20).fetch()
        r_lazy = db.query('invc.customer', columns=cols,
                          order_by='$id', limit=20,
                          enable_lazy_subquery=True).fetch()
        assert len(r_eager) == len(r_lazy)
        for re_, rl in zip(r_eager, r_lazy):
            assert re_['n_invoices'] == rl['n_invoices'], (
                f"{re_['account_name']}: eager={re_['n_invoices']} lazy={rl['n_invoices']}")

    def test_invoiced_total(self, db):
        cols = '$account_name,$invoiced_total'
        r_eager = db.query('invc.customer', columns=cols,
                           order_by='$id', limit=20).fetch()
        r_lazy = db.query('invc.customer', columns=cols,
                          order_by='$id', limit=20,
                          enable_lazy_subquery=True).fetch()
        for re_, rl in zip(r_eager, r_lazy):
            assert re_['invoiced_total'] == rl['invoiced_total'], (
                f"{re_['account_name']}: eager={re_['invoiced_total']} lazy={rl['invoiced_total']}")

    def test_last_invoice_date(self, db):
        cols = '$account_name,$last_invoice_date'
        r_eager = db.query('invc.customer', columns=cols,
                           order_by='$id', limit=20).fetch()
        r_lazy = db.query('invc.customer', columns=cols,
                          order_by='$id', limit=20,
                          enable_lazy_subquery=True).fetch()
        for re_, rl in zip(r_eager, r_lazy):
            assert re_['last_invoice_date'] == rl['last_invoice_date'], (
                f"{re_['account_name']}: eager={re_['last_invoice_date']} lazy={rl['last_invoice_date']}")

    def test_multiple_formulas(self, db):
        cols = '$account_name,$n_invoices,$invoiced_total,$last_invoice_date'
        r_eager = db.query('invc.customer', columns=cols,
                           order_by='$id', limit=10).fetch()
        r_lazy = db.query('invc.customer', columns=cols,
                          order_by='$id', limit=10,
                          enable_lazy_subquery=True).fetch()
        for re_, rl in zip(r_eager, r_lazy):
            assert re_['n_invoices'] == rl['n_invoices']
            assert re_['invoiced_total'] == rl['invoiced_total']
            assert re_['last_invoice_date'] == rl['last_invoice_date']

    def test_product_n_sold(self, db):
        cols = '$description,$n_sold'
        r_eager = db.query('invc.product', columns=cols,
                           order_by='$code', limit=20).fetch()
        r_lazy = db.query('invc.product', columns=cols,
                          order_by='$code', limit=20,
                          enable_lazy_subquery=True).fetch()
        for re_, rl in zip(r_eager, r_lazy):
            assert re_['n_sold'] == rl['n_sold'], (
                f"{re_['description']}: eager={re_['n_sold']} lazy={rl['n_sold']}")

    def test_invoice_n_rows(self, db):
        cols = '$inv_number,$n_rows'
        r_eager = db.query('invc.invoice', columns=cols,
                           order_by='$id', limit=20).fetch()
        r_lazy = db.query('invc.invoice', columns=cols,
                          order_by='$id', limit=20,
                          enable_lazy_subquery=True).fetch()
        for re_, rl in zip(r_eager, r_lazy):
            assert re_['n_rows'] == rl['n_rows'], (
                f"{re_['inv_number']}: eager={re_['n_rows']} lazy={rl['n_rows']}")


class TestLazyFormulaJoin:
    """Lazy rendering of formula columns compiled as LEFT JOIN."""

    def test_n_invoices_join(self, db):
        cols = '$account_name,$n_invoices'
        r_eager = db.query('invc.customer', columns=cols,
                           order_by='$id', limit=20,
                           enable_sq_join=True).fetch()
        r_lazy = db.query('invc.customer', columns=cols,
                          order_by='$id', limit=20,
                          enable_sq_join=True,
                          enable_lazy_subquery=True).fetch()
        assert len(r_eager) == len(r_lazy)
        for re_, rl in zip(r_eager, r_lazy):
            assert re_['n_invoices'] == rl['n_invoices'], (
                f"{re_['account_name']}: eager={re_['n_invoices']} lazy={rl['n_invoices']}")

    def test_multiple_formulas_join(self, db):
        cols = '$account_name,$n_invoices,$invoiced_total,$last_invoice_date'
        r_eager = db.query('invc.customer', columns=cols,
                           order_by='$id', limit=10,
                           enable_sq_join=True).fetch()
        r_lazy = db.query('invc.customer', columns=cols,
                          order_by='$id', limit=10,
                          enable_sq_join=True,
                          enable_lazy_subquery=True).fetch()
        for re_, rl in zip(r_eager, r_lazy):
            assert re_['n_invoices'] == rl['n_invoices']
            assert re_['invoiced_total'] == rl['invoiced_total']
            assert re_['last_invoice_date'] == rl['last_invoice_date']


class TestLazySqlTextEquivalence:
    """Verify that lazy rendering produces identical SQL text."""

    def test_inline_sql_identical(self, db):
        kw = dict(columns='$account_name,$n_invoices',
                  where='$id = :id', id='dummy')
        sql_eager = db.query('invc.customer', **kw).sqltext
        sql_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).sqltext
        assert sql_eager == sql_lazy

    def test_join_sql_identical(self, db):
        kw = dict(columns='$account_name,$n_invoices',
                  where='$id = :id', id='dummy',
                  enable_sq_join=True)
        sql_eager = db.query('invc.customer', **kw).sqltext
        sql_lazy = db.query('invc.customer', enable_lazy_subquery=True, **kw).sqltext
        assert sql_eager == sql_lazy

    def test_no_placeholder_in_sql(self, db):
        q = db.query('invc.customer',
                     columns='$account_name,$n_invoices,$invoiced_total',
                     where='$id = :id', id='dummy',
                     enable_lazy_subquery=True)
        sql = q.sqltext
        assert '__sq_' not in sql, f"Placeholder residuo nel SQL: {sql}"


class TestLazyRegistryContents:
    """Verify the subquery_registry is populated correctly."""

    def test_registry_populated_when_lazy(self, db):
        q = db.query('invc.customer',
                     columns='$account_name,$n_invoices',
                     where='$id = :id', id='dummy',
                     enable_lazy_subquery=True)
        compiled = q.compiled
        assert len(compiled.subquery_registry) > 0

    def test_registry_empty_when_not_lazy(self, db):
        q = db.query('invc.customer',
                     columns='$account_name,$n_invoices',
                     where='$id = :id', id='dummy')
        compiled = q.compiled
        assert len(compiled.subquery_registry) == 0

    def test_registry_entry_has_formula_inline_origin(self, db):
        q = db.query('invc.customer',
                     columns='$account_name,$n_invoices',
                     where='$id = :id', id='dummy',
                     enable_lazy_subquery=True)
        compiled = q.compiled
        origins = [e.origin for e in compiled.subquery_registry]
        assert 'formula_inline' in origins

    def test_registry_entry_has_formula_join_origin(self, db):
        q = db.query('invc.customer',
                     columns='$account_name,$n_invoices',
                     where='$id = :id', id='dummy',
                     enable_sq_join=True,
                     enable_lazy_subquery=True)
        compiled = q.compiled
        origins = [e.origin for e in compiled.subquery_registry]
        assert 'formula_join' in origins
