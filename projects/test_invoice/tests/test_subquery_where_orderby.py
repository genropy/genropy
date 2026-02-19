"""Test subquery formulaColumn used in WHERE and ORDER BY clauses.

Verifica che inline e JOIN (enable_sq_join=True) producano gli stessi
risultati quando la formulaColumn è usata in WHERE o ORDER BY.

FormulaColumns already in the model (n_invoices, invoiced_total) are used
directly. Additional columns are added via RuntimeModel where needed.
"""


def _add_customer_extra(rm):
    cust = rm.table('invc.customer')
    cust.formulaColumn('last_invoice_date',
                       select=dict(table='invc.invoice',
                                   columns='MAX($date)',
                                   where='$customer_id=#THIS.id'),
                       dtype='D')


def _add_product_extra(rm):
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
    inv = rm.table('invc.invoice')
    inv.formulaColumn('n_rows',
                      select=dict(table='invc.invoice_row',
                                  columns='COUNT(*)',
                                  where='$invoice_id=#THIS.id'),
                      dtype='L')


class TestWhereOnFormulaColumn:
    """Usare formulaColumn con subquery nella clausola WHERE."""

    def test_where_n_invoices_gt(self, db):
        """Clienti con più di 25 fatture."""
        cols = '$account_name,$n_invoices'
        where = '$n_invoices > :min_inv'
        r_inline = db.query('invc.customer', columns=cols,
                            where=where, min_inv=25,
                            order_by='$id').fetch()
        r_join = db.query('invc.customer', columns=cols,
                          where=where, min_inv=25,
                          order_by='$id',
                          enable_sq_join=True).fetch()
        assert len(r_inline) == len(r_join)
        for ri, rj in zip(r_inline, r_join):
            assert ri['account_name'] == rj['account_name']
            assert ri['n_invoices'] == rj['n_invoices']

    def test_where_invoiced_total_gt(self, db):
        """Clienti con fatturato superiore a 50000."""
        cols = '$account_name,$invoiced_total'
        where = '$invoiced_total > :min_tot'
        r_inline = db.query('invc.customer', columns=cols,
                            where=where, min_tot=50000,
                            order_by='$id').fetch()
        r_join = db.query('invc.customer', columns=cols,
                          where=where, min_tot=50000,
                          order_by='$id',
                          enable_sq_join=True).fetch()
        assert len(r_inline) == len(r_join)
        for ri, rj in zip(r_inline, r_join):
            assert ri['account_name'] == rj['account_name']
            assert ri['invoiced_total'] == rj['invoiced_total']

    def test_where_n_sold_eq_zero(self, db):
        """Prodotti mai venduti (n_sold = 0)."""
        rm = db.runtimeModel()
        _add_product_extra(rm)
        with rm:
            cols = '$code,$description,$n_sold'
            where = '$n_sold = :val'
            r_inline = db.query('invc.product', columns=cols,
                                where=where, val=0,
                                order_by='$code').fetch()
            r_join = db.query('invc.product', columns=cols,
                              where=where, val=0,
                              order_by='$code',
                              enable_sq_join=True).fetch()
        assert len(r_inline) == len(r_join)
        for ri, rj in zip(r_inline, r_join):
            assert ri['code'] == rj['code']

    def test_where_combined_formula_and_column(self, db):
        """WHERE su colonna reale + formulaColumn."""
        cols = '$account_name,$state,$n_invoices'
        where = "$state = :st AND $n_invoices > :min_inv"
        r_inline = db.query('invc.customer', columns=cols,
                            where=where, st='NSW', min_inv=10,
                            order_by='$id').fetch()
        r_join = db.query('invc.customer', columns=cols,
                          where=where, st='NSW', min_inv=10,
                          order_by='$id',
                          enable_sq_join=True).fetch()
        assert len(r_inline) == len(r_join)
        for ri, rj in zip(r_inline, r_join):
            assert ri['account_name'] == rj['account_name']
            assert ri['n_invoices'] == rj['n_invoices']

    def test_where_last_invoice_date(self, db):
        """Clienti con ultima fattura dopo una certa data."""
        rm = db.runtimeModel()
        _add_customer_extra(rm)
        with rm:
            cols = '$account_name,$last_invoice_date'
            where = "$last_invoice_date > :cutoff"
            r_inline = db.query('invc.customer', columns=cols,
                                where=where, cutoff='2024-01-01',
                                order_by='$id').fetch()
            r_join = db.query('invc.customer', columns=cols,
                              where=where, cutoff='2024-01-01',
                              order_by='$id',
                              enable_sq_join=True).fetch()
        assert len(r_inline) == len(r_join)
        for ri, rj in zip(r_inline, r_join):
            assert ri['account_name'] == rj['account_name']
            assert ri['last_invoice_date'] == rj['last_invoice_date']


class TestOrderByFormulaColumn:
    """Usare formulaColumn con subquery nella clausola ORDER BY."""

    def test_order_by_n_invoices_desc(self, db):
        """Top 20 clienti per numero fatture."""
        cols = '$account_name,$n_invoices'
        r_inline = db.query('invc.customer', columns=cols,
                            order_by='$n_invoices DESC,$id', limit=20).fetch()
        r_join = db.query('invc.customer', columns=cols,
                          order_by='$n_invoices DESC,$id', limit=20,
                          enable_sq_join=True).fetch()
        assert len(r_inline) == 20
        assert len(r_join) == 20
        for ri, rj in zip(r_inline, r_join):
            assert ri['account_name'] == rj['account_name']
            assert ri['n_invoices'] == rj['n_invoices']

    def test_order_by_invoiced_total_desc(self, db):
        """Top 20 clienti per fatturato."""
        cols = '$account_name,$invoiced_total'
        r_inline = db.query('invc.customer', columns=cols,
                            order_by='$invoiced_total DESC,$id', limit=20).fetch()
        r_join = db.query('invc.customer', columns=cols,
                          order_by='$invoiced_total DESC,$id', limit=20,
                          enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['account_name'] == rj['account_name']
            assert ri['invoiced_total'] == rj['invoiced_total']

    def test_order_by_n_sold_desc(self, db):
        """Top 20 prodotti più venduti."""
        rm = db.runtimeModel()
        _add_product_extra(rm)
        with rm:
            cols = '$code,$description,$n_sold'
            r_inline = db.query('invc.product', columns=cols,
                                order_by='$n_sold DESC,$code', limit=20).fetch()
            r_join = db.query('invc.product', columns=cols,
                              order_by='$n_sold DESC,$code', limit=20,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['code'] == rj['code']
            assert ri['n_sold'] == rj['n_sold']

    def test_order_by_total_sold_asc(self, db):
        """Prodotti con meno vendite (ASC), primi 20."""
        rm = db.runtimeModel()
        _add_product_extra(rm)
        with rm:
            cols = '$code,$description,$total_sold'
            r_inline = db.query('invc.product', columns=cols,
                                order_by='$total_sold ASC,$code', limit=20).fetch()
            r_join = db.query('invc.product', columns=cols,
                              order_by='$total_sold ASC,$code', limit=20,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['code'] == rj['code']
            assert ri['total_sold'] == rj['total_sold']

    def test_order_by_n_rows_desc(self, db):
        """Top 50 fatture per numero righe."""
        rm = db.runtimeModel()
        _add_invoice_extra(rm)
        with rm:
            cols = '$inv_number,$n_rows'
            r_inline = db.query('invc.invoice', columns=cols,
                                order_by='$n_rows DESC,$inv_number', limit=50).fetch()
            r_join = db.query('invc.invoice', columns=cols,
                              order_by='$n_rows DESC,$inv_number', limit=50,
                              enable_sq_join=True).fetch()
        for ri, rj in zip(r_inline, r_join):
            assert ri['inv_number'] == rj['inv_number']
            assert ri['n_rows'] == rj['n_rows']


class TestWhereAndOrderByCombined:
    """WHERE + ORDER BY entrambi su formulaColumn."""

    def test_where_gt_order_desc(self, db):
        """Clienti con >15 fatture, ordinati per fatturato DESC."""
        cols = '$account_name,$n_invoices,$invoiced_total'
        where = '$n_invoices > :min_inv'
        r_inline = db.query('invc.customer', columns=cols,
                            where=where, min_inv=15,
                            order_by='$invoiced_total DESC,$id').fetch()
        r_join = db.query('invc.customer', columns=cols,
                          where=where, min_inv=15,
                          order_by='$invoiced_total DESC,$id',
                          enable_sq_join=True).fetch()
        assert len(r_inline) == len(r_join)
        for ri, rj in zip(r_inline, r_join):
            assert ri['account_name'] == rj['account_name']
            assert ri['n_invoices'] == rj['n_invoices']
            assert ri['invoiced_total'] == rj['invoiced_total']

    def test_where_formula_order_formula_limit(self, db):
        """Prodotti venduti >100 volte, ordinati per total_sold, top 10."""
        rm = db.runtimeModel()
        _add_product_extra(rm)
        with rm:
            cols = '$code,$description,$n_sold,$total_sold'
            where = '$n_sold > :min_sold'
            r_inline = db.query('invc.product', columns=cols,
                                where=where, min_sold=100,
                                order_by='$total_sold DESC,$code', limit=10).fetch()
            r_join = db.query('invc.product', columns=cols,
                              where=where, min_sold=100,
                              order_by='$total_sold DESC,$code', limit=10,
                              enable_sq_join=True).fetch()
        assert len(r_inline) == len(r_join)
        for ri, rj in zip(r_inline, r_join):
            assert ri['code'] == rj['code']
            assert ri['n_sold'] == rj['n_sold']
            assert ri['total_sold'] == rj['total_sold']
