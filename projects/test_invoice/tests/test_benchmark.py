"""Benchmark: subquery inline vs LEFT JOIN (enable_sq_join=True).

Ogni test misura il tempo di esecuzione della stessa query in modalità
inline e JOIN, stampando i risultati per confronto.

Eseguire con:  pytest test_benchmark.py -v -s
"""
import time


def timed_fetch(db, table, columns, order_by=None, limit=None, enable_sq_join=False, **kw):
    t0 = time.perf_counter()
    result = db.query(table, columns=columns, order_by=order_by,
                      limit=limit, enable_sq_join=enable_sq_join, **kw).fetch()
    elapsed = time.perf_counter() - t0
    return result, elapsed


def report(label, t_inline, t_join, n_rows):
    speedup = t_inline / t_join if t_join > 0 else float('inf')
    print(f'\n  {label}:')
    print(f'    rows={n_rows}  inline={t_inline:.4f}s  join={t_join:.4f}s  speedup={speedup:.2f}x')


class TestBenchmarkCustomer:
    """Benchmark su customer (3200 righe, subquery su 60K fatture)."""

    def test_n_invoices_all(self, db):
        cols = '$account_name,$n_invoices'
        _, t_inline = timed_fetch(db, 'invc.customer', cols, order_by='$account_name')
        _, t_join = timed_fetch(db, 'invc.customer', cols, order_by='$account_name',
                                enable_sq_join=True)
        report('customer.n_invoices (all)', t_inline, t_join, 3200)

    def test_invoiced_total_all(self, db):
        cols = '$account_name,$invoiced_total'
        _, t_inline = timed_fetch(db, 'invc.customer', cols, order_by='$account_name')
        _, t_join = timed_fetch(db, 'invc.customer', cols, order_by='$account_name',
                                enable_sq_join=True)
        report('customer.invoiced_total (all)', t_inline, t_join, 3200)

    def test_last_invoice_date_all(self, db):
        cols = '$account_name,$last_invoice_date'
        _, t_inline = timed_fetch(db, 'invc.customer', cols, order_by='$account_name')
        _, t_join = timed_fetch(db, 'invc.customer', cols, order_by='$account_name',
                                enable_sq_join=True)
        report('customer.last_invoice_date (all)', t_inline, t_join, 3200)

    def test_avg_invoice_total_all(self, db):
        cols = '$account_name,$avg_invoice_total'
        _, t_inline = timed_fetch(db, 'invc.customer', cols, order_by='$account_name')
        _, t_join = timed_fetch(db, 'invc.customer', cols, order_by='$account_name',
                                enable_sq_join=True)
        report('customer.avg_invoice_total (all)', t_inline, t_join, 3200)

    def test_multiple_formulas_all(self, db):
        cols = '$account_name,$n_invoices,$invoiced_total,$last_invoice_date,$avg_invoice_total'
        _, t_inline = timed_fetch(db, 'invc.customer', cols, order_by='$account_name')
        _, t_join = timed_fetch(db, 'invc.customer', cols, order_by='$account_name',
                                enable_sq_join=True)
        report('customer.4_formulas (all)', t_inline, t_join, 3200)

    def test_n_invoices_limit20(self, db):
        cols = '$account_name,$n_invoices'
        _, t_inline = timed_fetch(db, 'invc.customer', cols, order_by='$account_name', limit=20)
        _, t_join = timed_fetch(db, 'invc.customer', cols, order_by='$account_name', limit=20,
                                enable_sq_join=True)
        report('customer.n_invoices (limit 20)', t_inline, t_join, 20)


class TestBenchmarkProduct:
    """Benchmark su product (1695 righe, subquery su 410K invoice_row)."""

    def test_n_sold_all(self, db):
        cols = '$description,$n_sold'
        _, t_inline = timed_fetch(db, 'invc.product', cols, order_by='$code')
        _, t_join = timed_fetch(db, 'invc.product', cols, order_by='$code',
                                enable_sq_join=True)
        report('product.n_sold (all)', t_inline, t_join, 1695)

    def test_total_sold_all(self, db):
        cols = '$description,$total_sold'
        _, t_inline = timed_fetch(db, 'invc.product', cols, order_by='$code')
        _, t_join = timed_fetch(db, 'invc.product', cols, order_by='$code',
                                enable_sq_join=True)
        report('product.total_sold (all)', t_inline, t_join, 1695)

    def test_both_formulas_all(self, db):
        cols = '$description,$n_sold,$total_sold'
        _, t_inline = timed_fetch(db, 'invc.product', cols, order_by='$code')
        _, t_join = timed_fetch(db, 'invc.product', cols, order_by='$code',
                                enable_sq_join=True)
        report('product.n_sold+total_sold (all)', t_inline, t_join, 1695)


class TestBenchmarkInvoice:
    """Benchmark su invoice (60K righe, subquery su 410K invoice_row)."""

    def test_n_rows_all(self, db):
        cols = '$inv_number,$n_rows'
        _, t_inline = timed_fetch(db, 'invc.invoice', cols, order_by='$inv_number')
        _, t_join = timed_fetch(db, 'invc.invoice', cols, order_by='$inv_number',
                                enable_sq_join=True)
        report('invoice.n_rows (all 60K)', t_inline, t_join, 60179)

    def test_row_total_all(self, db):
        cols = '$inv_number,$row_total'
        _, t_inline = timed_fetch(db, 'invc.invoice', cols, order_by='$inv_number')
        _, t_join = timed_fetch(db, 'invc.invoice', cols, order_by='$inv_number',
                                enable_sq_join=True)
        report('invoice.row_total (all 60K)', t_inline, t_join, 60179)

    def test_n_rows_limit100(self, db):
        cols = '$inv_number,$n_rows'
        _, t_inline = timed_fetch(db, 'invc.invoice', cols,
                                  order_by='$inv_number', limit=100)
        _, t_join = timed_fetch(db, 'invc.invoice', cols,
                                order_by='$inv_number', limit=100,
                                enable_sq_join=True)
        report('invoice.n_rows (limit 100)', t_inline, t_join, 100)


class TestBenchmarkWhereOnFormula:
    """Benchmark: WHERE su formulaColumn."""

    def test_where_n_invoices_gt(self, db):
        cols = '$account_name,$n_invoices'
        kw = dict(where='$n_invoices > :min_inv', min_inv=25)
        r_inline, t_inline = timed_fetch(db, 'invc.customer', cols,
                                         order_by='$account_name', **kw)
        r_join, t_join = timed_fetch(db, 'invc.customer', cols,
                                     order_by='$account_name',
                                     enable_sq_join=True, **kw)
        report('WHERE n_invoices>25', t_inline, t_join, len(r_inline))

    def test_where_invoiced_total_gt(self, db):
        cols = '$account_name,$invoiced_total'
        kw = dict(where='$invoiced_total > :min_tot', min_tot=50000)
        r_inline, t_inline = timed_fetch(db, 'invc.customer', cols,
                                         order_by='$account_name', **kw)
        r_join, t_join = timed_fetch(db, 'invc.customer', cols,
                                     order_by='$account_name',
                                     enable_sq_join=True, **kw)
        report('WHERE invoiced_total>50K', t_inline, t_join, len(r_inline))

    def test_where_n_sold_gt(self, db):
        cols = '$code,$description,$n_sold'
        kw = dict(where='$n_sold > :min_sold', min_sold=100)
        r_inline, t_inline = timed_fetch(db, 'invc.product', cols,
                                         order_by='$code', **kw)
        r_join, t_join = timed_fetch(db, 'invc.product', cols,
                                     order_by='$code',
                                     enable_sq_join=True, **kw)
        report('WHERE n_sold>100', t_inline, t_join, len(r_inline))

    def test_where_combined_state_and_formula(self, db):
        cols = '$account_name,$state,$n_invoices'
        kw = dict(where='$state = :st AND $n_invoices > :min_inv', st='NSW', min_inv=10)
        r_inline, t_inline = timed_fetch(db, 'invc.customer', cols,
                                         order_by='$account_name', **kw)
        r_join, t_join = timed_fetch(db, 'invc.customer', cols,
                                     order_by='$account_name',
                                     enable_sq_join=True, **kw)
        report('WHERE state=NSW AND n_invoices>10', t_inline, t_join, len(r_inline))


class TestBenchmarkOrderByFormula:
    """Benchmark: ORDER BY su formulaColumn."""

    def test_order_by_n_invoices_desc_top20(self, db):
        cols = '$account_name,$n_invoices'
        r_inline, t_inline = timed_fetch(db, 'invc.customer', cols,
                                         order_by='$n_invoices DESC', limit=20)
        r_join, t_join = timed_fetch(db, 'invc.customer', cols,
                                     order_by='$n_invoices DESC', limit=20,
                                     enable_sq_join=True)
        report('ORDER BY n_invoices DESC LIMIT 20', t_inline, t_join, 20)

    def test_order_by_invoiced_total_desc_all(self, db):
        cols = '$account_name,$invoiced_total'
        r_inline, t_inline = timed_fetch(db, 'invc.customer', cols,
                                         order_by='$invoiced_total DESC')
        r_join, t_join = timed_fetch(db, 'invc.customer', cols,
                                     order_by='$invoiced_total DESC',
                                     enable_sq_join=True)
        report('ORDER BY invoiced_total DESC (all)', t_inline, t_join, len(r_inline))

    def test_order_by_n_sold_desc_top20(self, db):
        cols = '$code,$description,$n_sold'
        r_inline, t_inline = timed_fetch(db, 'invc.product', cols,
                                         order_by='$n_sold DESC', limit=20)
        r_join, t_join = timed_fetch(db, 'invc.product', cols,
                                     order_by='$n_sold DESC', limit=20,
                                     enable_sq_join=True)
        report('ORDER BY n_sold DESC LIMIT 20', t_inline, t_join, 20)

    def test_order_by_n_rows_desc_top50(self, db):
        cols = '$inv_number,$n_rows'
        r_inline, t_inline = timed_fetch(db, 'invc.invoice', cols,
                                         order_by='$n_rows DESC', limit=50)
        r_join, t_join = timed_fetch(db, 'invc.invoice', cols,
                                     order_by='$n_rows DESC', limit=50,
                                     enable_sq_join=True)
        report('ORDER BY n_rows DESC LIMIT 50', t_inline, t_join, 50)


class TestBenchmarkWhereAndOrderBy:
    """Benchmark: WHERE + ORDER BY entrambi su formulaColumn."""

    def test_where_gt_order_desc(self, db):
        cols = '$account_name,$n_invoices,$invoiced_total'
        kw = dict(where='$n_invoices > :min_inv', min_inv=15)
        r_inline, t_inline = timed_fetch(db, 'invc.customer', cols,
                                         order_by='$invoiced_total DESC', **kw)
        r_join, t_join = timed_fetch(db, 'invc.customer', cols,
                                     order_by='$invoiced_total DESC',
                                     enable_sq_join=True, **kw)
        report('WHERE n_inv>15 ORDER BY total DESC', t_inline, t_join, len(r_inline))

    def test_where_formula_order_formula_limit(self, db):
        cols = '$code,$description,$n_sold,$total_sold'
        kw = dict(where='$n_sold > :min_sold', min_sold=100)
        r_inline, t_inline = timed_fetch(db, 'invc.product', cols,
                                         order_by='$total_sold DESC', limit=10, **kw)
        r_join, t_join = timed_fetch(db, 'invc.product', cols,
                                     order_by='$total_sold DESC', limit=10,
                                     enable_sq_join=True, **kw)
        report('WHERE n_sold>100 ORDER BY total_sold LIMIT 10', t_inline, t_join, len(r_inline))


class TestBenchmarkTopFormulas:
    """Benchmark: formulaColumn con order_by+limit (ROW_NUMBER wrapping)."""

    def test_top_customer_id_all(self, db):
        cols = '$code,$top_customer_id'
        _, t_inline = timed_fetch(db, 'invc.product', cols, order_by='$code')
        _, t_join = timed_fetch(db, 'invc.product', cols, order_by='$code',
                                enable_sq_join=True)
        report('product.top_customer_id (all)', t_inline, t_join, 1695)

    def test_top_state_all(self, db):
        cols = '$code,$top_state'
        _, t_inline = timed_fetch(db, 'invc.product', cols, order_by='$code')
        _, t_join = timed_fetch(db, 'invc.product', cols, order_by='$code',
                                enable_sq_join=True)
        report('product.top_state (all)', t_inline, t_join, 1695)

    def test_top_customer_limit20(self, db):
        cols = '$code,$top_customer_id'
        _, t_inline = timed_fetch(db, 'invc.product', cols,
                                  order_by='$code', limit=20)
        _, t_join = timed_fetch(db, 'invc.product', cols,
                                order_by='$code', limit=20,
                                enable_sq_join=True)
        report('product.top_customer_id (limit 20)', t_inline, t_join, 20)
