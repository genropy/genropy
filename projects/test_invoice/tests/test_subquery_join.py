"""Test subquery inline vs LEFT JOIN via enable_sq_join=True.

Each test queries the same formulaColumn twice:
  1. inline (default)
  2. as LEFT JOIN (enable_sq_join=True)
and asserts the results match.

FormulaColumns already defined in the model (n_invoices, invoiced_total)
are tested directly. Additional columns (last_invoice_date, avg_invoice_total,
n_sold, total_sold, n_rows, row_total) are added via RuntimeModel.
"""


def _add_customer_extra(rm):
    """Add extra formulaColumns to customer via RuntimeModel."""
    cust = rm.table('invc.customer')
    cust.formulaColumn('last_invoice_date',
                       select=dict(table='invc.invoice',
                                   columns='MAX($date)',
                                   where='$customer_id=#THIS.id'),
                       dtype='D')
    cust.formulaColumn('avg_invoice_total',
                       select=dict(table='invc.invoice',
                                   columns='AVG($total)',
                                   where='$customer_id=#THIS.id'),
                       dtype='N')


def _add_product_extra(rm):
    """Add extra formulaColumns to product via RuntimeModel."""
    prod = rm.table('invc.product')
    prod.formulaColumn('n_sold',
                       select=dict(table='invc.invoice_row',
                                   columns='SUM($quantity)',
                                   where='$product_id=#THIS.id'),
                       dtype='L')
    prod.formulaColumn('total_sold',
                       select=dict(table='invc.invoice_row',
                                   columns='SUM($tot_price)',
                                   where='$product_id=#THIS.id'),
                       dtype='N')


def _add_invoice_extra(rm):
    """Add extra formulaColumns to invoice via RuntimeModel."""
    inv = rm.table('invc.invoice')
    inv.formulaColumn('n_rows',
                      select=dict(table='invc.invoice_row',
                                  columns='COUNT(*)',
                                  where='$invoice_id=#THIS.id'),
                      dtype='L')
    inv.formulaColumn('row_total',
                      select=dict(table='invc.invoice_row',
                                  columns='SUM($tot_price)',
                                  where='$invoice_id=#THIS.id'),
                      dtype='N')


class TestCustomerSubqueryJoin:
    """formulaColumn on customer: n_invoices, invoiced_total (model),
    last_invoice_date, avg_invoice_total (runtime)."""

    def test_n_invoices(self, db):
        cols = '$account_name,$n_invoices'
        r_inline = db.query('invc.customer', columns=cols,
                            order_by='$id', limit=20).fetch()
        r_join = db.query('invc.customer', columns=cols,
                          order_by='$id', limit=20,
                          enable_sq_join=True).fetch()
        assert len(r_inline) == len(r_join)
        for ri, rj in zip(r_inline, r_join):
            assert ri['n_invoices'] == rj['n_invoices'], (
                f"{ri['account_name']}: inline={ri['n_invoices']} join={rj['n_invoices']}")

    def test_invoiced_total(self, db):
        cols = '$account_name,$invoiced_total'
        r_inline = db.query('invc.customer', columns=cols,
                            order_by='$id', limit=20).fetch()
        r_join = db.query('invc.customer', columns=cols,
                          order_by='$id', limit=20,
                          enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['invoiced_total'] == rj['invoiced_total'], (
                f"{ri['account_name']}: inline={ri['invoiced_total']} join={rj['invoiced_total']}")

    def test_last_invoice_date(self, db):
        rm = db.runtimeModel()
        _add_customer_extra(rm)
        with rm:
            cols = '$account_name,$last_invoice_date'
            r_inline = db.query('invc.customer', columns=cols,
                                order_by='$id', limit=20).fetch()
            r_join = db.query('invc.customer', columns=cols,
                              order_by='$id', limit=20,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['last_invoice_date'] == rj['last_invoice_date'], (
                f"{ri['account_name']}: inline={ri['last_invoice_date']} join={rj['last_invoice_date']}")

    def test_avg_invoice_total(self, db):
        rm = db.runtimeModel()
        _add_customer_extra(rm)
        with rm:
            cols = '$account_name,$avg_invoice_total'
            r_inline = db.query('invc.customer', columns=cols,
                                order_by='$id', limit=20).fetch()
            r_join = db.query('invc.customer', columns=cols,
                              order_by='$id', limit=20,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            vi = ri['avg_invoice_total']
            vj = rj['avg_invoice_total']
            if vi is None and vj is None:
                continue
            assert abs(float(vi) - float(vj)) < 0.01, (
                f"{ri['account_name']}: inline={vi} join={vj}")

    def test_multiple_formulas_together(self, db):
        rm = db.runtimeModel()
        _add_customer_extra(rm)
        with rm:
            cols = '$account_name,$n_invoices,$invoiced_total,$last_invoice_date,$avg_invoice_total'
            r_inline = db.query('invc.customer', columns=cols,
                                order_by='$id', limit=10).fetch()
            r_join = db.query('invc.customer', columns=cols,
                              order_by='$id', limit=10,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['n_invoices'] == rj['n_invoices']
            assert ri['invoiced_total'] == rj['invoiced_total']
            assert ri['last_invoice_date'] == rj['last_invoice_date']


class TestProductSubqueryJoin:
    """formulaColumn on product: n_sold, total_sold (runtime)."""

    def test_n_sold(self, db):
        rm = db.runtimeModel()
        _add_product_extra(rm)
        with rm:
            cols = '$description,$n_sold'
            r_inline = db.query('invc.product', columns=cols,
                                order_by='$code', limit=20).fetch()
            r_join = db.query('invc.product', columns=cols,
                              order_by='$code', limit=20,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['n_sold'] == rj['n_sold'], (
                f"{ri['description']}: inline={ri['n_sold']} join={rj['n_sold']}")

    def test_total_sold(self, db):
        rm = db.runtimeModel()
        _add_product_extra(rm)
        with rm:
            cols = '$description,$total_sold'
            r_inline = db.query('invc.product', columns=cols,
                                order_by='$code', limit=20).fetch()
            r_join = db.query('invc.product', columns=cols,
                              order_by='$code', limit=20,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['total_sold'] == rj['total_sold'], (
                f"{ri['description']}: inline={ri['total_sold']} join={rj['total_sold']}")


class TestInvoiceSubqueryJoin:
    """formulaColumn on invoice: n_rows, row_total (runtime)."""

    def test_n_rows(self, db):
        rm = db.runtimeModel()
        _add_invoice_extra(rm)
        with rm:
            cols = '$inv_number,$n_rows'
            r_inline = db.query('invc.invoice', columns=cols,
                                order_by='$inv_number', limit=50).fetch()
            r_join = db.query('invc.invoice', columns=cols,
                              order_by='$inv_number', limit=50,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['n_rows'] == rj['n_rows'], (
                f"{ri['inv_number']}: inline={ri['n_rows']} join={rj['n_rows']}")

    def test_row_total(self, db):
        rm = db.runtimeModel()
        _add_invoice_extra(rm)
        with rm:
            cols = '$inv_number,$row_total'
            r_inline = db.query('invc.invoice', columns=cols,
                                order_by='$inv_number', limit=50).fetch()
            r_join = db.query('invc.invoice', columns=cols,
                              order_by='$inv_number', limit=50,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['row_total'] == rj['row_total'], (
                f"{ri['inv_number']}: inline={ri['row_total']} join={rj['row_total']}")


class TestSqlTextGeneration:
    """Verify the generated SQL contains LEFT JOIN when enable_sq_join=True."""

    def test_inline_has_subselect(self, db):
        q = db.query('invc.customer', columns='$account_name,$n_invoices',
                      where='$id = :id', id='dummy')
        sql = q.sqltext.upper()
        assert sql.count('SELECT') >= 2

    def test_join_has_left_join(self, db):
        q = db.query('invc.customer', columns='$account_name,$n_invoices',
                      where='$id = :id', id='dummy',
                      enable_sq_join=True)
        sql = q.sqltext
        assert 'LEFT JOIN' in sql
