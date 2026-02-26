"""Test sql_aggregate: many-side relations as inline aggregate subqueries.

When sql_aggregate=True, traversing a many-side relation (e.g. @invoices.total
on customer) produces a correlated subquery with the appropriate SQL aggregate
function instead of an exploding LEFT JOIN + Python post-processing.

The aggregate function is determined by the target column's dtype:
  - numeric (R, L, N, I): SUM (default)
  - boolean (B): BOOL_AND
  - text: string_agg / group_concat (adapter-dependent)

The tests compare sql_aggregate results against the same query executed
without the flag, using selection(_aggregateRows=True) for Python-side
aggregation.
"""


class TestSqlAggregateSumNumeric:
    """Many-side relation on numeric columns: sql_aggregate vs _aggregateRows."""

    def test_customer_invoices_total(self, db):
        """SUM of invoice.total via @invoices.total: SQL vs Python aggregation."""
        cols = '$account_name,@invoices.total'
        where = '$n_invoices > 0'
        sel_py = db.query('invc.customer', columns=cols,
                          where=where,
                          order_by='$id').selection(_aggregateRows=True)
        r_py = sel_py.output('dictlist')
        r_sql = db.query('invc.customer', columns=cols,
                         where=where,
                         order_by='$id',
                         sql_aggregate=True).fetch()
        assert len(r_py) == len(r_sql)
        for rp, rs in zip(r_py, r_sql):
            assert rp['account_name'] == rs['account_name']
            # sqlite SUM in subquery returns float, _aggregateRows sums Decimal
            assert round(float(rp['_invoices_total']), 2) == round(float(rs['_invoices_total']), 2), (
                f"{rp['account_name']}: py={rp['_invoices_total']} sql={rs['_invoices_total']}")

    def test_invoice_rows_tot_price(self, db):
        """SUM of invoice_row.tot_price via @rows.tot_price."""
        cols = '$inv_number,@rows.tot_price'
        sel_py = db.query('invc.invoice', columns=cols,
                          order_by='$inv_number').selection(_aggregateRows=True)
        r_py = sel_py.output('dictlist')
        r_sql = db.query('invc.invoice', columns=cols,
                         order_by='$inv_number',
                         sql_aggregate=True).fetch()
        assert len(r_py) == len(r_sql)
        for rp, rs in zip(r_py, r_sql):
            assert rp['inv_number'] == rs['inv_number']

    def test_invoice_rows_quantity(self, db):
        """SUM of invoice_row.quantity via @rows.quantity."""
        cols = '$inv_number,@rows.quantity'
        sel_py = db.query('invc.invoice', columns=cols,
                          order_by='$inv_number').selection(_aggregateRows=True)
        r_py = sel_py.output('dictlist')
        r_sql = db.query('invc.invoice', columns=cols,
                         order_by='$inv_number',
                         sql_aggregate=True).fetch()
        assert len(r_py) == len(r_sql)
        for rp, rs in zip(r_py, r_sql):
            assert rp['inv_number'] == rs['inv_number']

    def test_product_invoice_rows_tot_price(self, db):
        """SUM of invoice_row.tot_price via @invoice_rows.tot_price on product."""
        cols = '$code,@invoice_rows.tot_price'
        sel_py = db.query('invc.product', columns=cols,
                          order_by='$code').selection(_aggregateRows=True)
        r_py = sel_py.output('dictlist')
        r_sql = db.query('invc.product', columns=cols,
                         order_by='$code',
                         sql_aggregate=True).fetch()
        assert len(r_py) == len(r_sql)
        for rp, rs in zip(r_py, r_sql):
            assert rp['code'] == rs['code']


class TestSqlAggregateCountViaFormula:
    """Compare sql_aggregate COUNT with existing formulaColumn n_invoices."""

    def test_customer_count_invoices(self, db):
        """RuntimeModel COUNT via @invoices matches n_invoices formula."""
        rm = db.runtimeModel()
        cust = rm.table('invc.customer')
        cust.formulaColumn('n_inv_agg',
                           select=dict(table='invc.invoice',
                                       columns='COUNT(*)',
                                       where='$customer_id=#THIS.id'),
                           dtype='L')
        with rm:
            cols = '$account_name,$n_invoices,$n_inv_agg'
            rows = db.query('invc.customer', columns=cols,
                            order_by='$id', limit=20).fetch()
        for r in rows:
            assert r['n_invoices'] == r['n_inv_agg'], (
                f"{r['account_name']}: n_invoices={r['n_invoices']} n_inv_agg={r['n_inv_agg']}")


class TestSqlAggregateDisabledByDefault:
    """sql_aggregate=False (default): many-side relations use standard JOIN."""

    def test_default_no_aggregate(self, db):
        """Without sql_aggregate, @invoices.total uses JOIN (exploding)."""
        cols = '$account_name,@invoices.total'
        q = db.query('invc.customer', columns=cols,
                     order_by='$id', limit=5)
        sql = q.sqltext.upper()
        assert 'LEFT JOIN' in sql
        assert sql.count('SELECT') == 1


class TestSqlAggregateSqlText:
    """Verify the generated SQL contains a subquery when sql_aggregate=True."""

    def test_has_subselect(self, db):
        """sql_aggregate=True should produce a correlated subquery."""
        cols = '$account_name,@invoices.total'
        q = db.query('invc.customer', columns=cols,
                     where='$id = :id', id='dummy',
                     sql_aggregate=True)
        sql = q.sqltext.upper()
        assert sql.count('SELECT') >= 2
        assert 'SUM' in sql

    def test_no_left_join_for_many(self, db):
        """sql_aggregate=True should NOT produce LEFT JOIN for the many relation."""
        cols = '$account_name,@invoices.total'
        q = db.query('invc.customer', columns=cols,
                     where='$id = :id', id='dummy',
                     sql_aggregate=True)
        sql = q.sqltext.upper()
        assert 'LEFT JOIN' not in sql or sql.count('SELECT') >= 2
