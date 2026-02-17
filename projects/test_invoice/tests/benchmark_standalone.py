"""Genropy benchmark — same queries as Django/SQLAlchemy benchmark."""
import os
import time
from gnr.app.gnrapp import GnrApp

INSTANCE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'instances', 'test_invoice_pg')
)


def timed(label, fn, warmup=1, runs=3):
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - t0)
    avg = sum(times) / len(times)
    count = len(result) if result is not None else 0
    print(f"  {label:50s} {avg:.4f}s  ({count} rows)")
    return avg


def run():
    app = GnrApp(INSTANCE_PATH)
    db = app.db
    print("\n=== Genropy Benchmark ===\n")
    print("--- 1. Standard aggregates (ALL 3200 rows) ---\n")

    # 1. n_invoices ALL
    def q_count():
        return db.query('invc.customer',
                        columns='$account_name,$n_invoices',
                        enable_sq_join=True).fetch()
    timed("n_invoices ALL", q_count)

    # 2. invoiced_total ALL
    def q_sum():
        return db.query('invc.customer',
                        columns='$account_name,$invoiced_total',
                        enable_sq_join=True).fetch()
    timed("invoiced_total ALL", q_sum)

    # 3. 4 annotations ALL
    def q_4annot():
        return db.query('invc.customer',
                        columns='$account_name,$n_invoices,$invoiced_total,$last_invoice_date,$avg_invoice_total',
                        enable_sq_join=True).fetch()
    timed("4 annotations ALL", q_4annot)

    # 4. 6 annotations ALL
    def q_6annot():
        return db.query('invc.customer',
                        columns='$account_name,$n_invoices,$invoiced_total,$max_invoice,$min_invoice,$avg_invoice_total,$last_invoice_date',
                        enable_sq_join=True).fetch()
    timed("6 annotations ALL", q_6annot)

    # 5. WHERE n_invoices > 25
    def q_where_count():
        return db.query('invc.customer',
                        columns='$account_name,$n_invoices',
                        where='$n_invoices > :min_inv', min_inv=25,
                        enable_sq_join=True).fetch()
    timed("WHERE n_invoices>25", q_where_count)

    # 6. WHERE invoiced_total > 50000
    def q_where_sum():
        return db.query('invc.customer',
                        columns='$account_name,$invoiced_total',
                        where='$invoiced_total > :min_tot', min_tot=50000,
                        enable_sq_join=True).fetch()
    timed("WHERE invoiced_total>50K", q_where_sum)

    # 7. ORDER BY total ALL
    def q_order():
        return db.query('invc.customer',
                        columns='$account_name,$invoiced_total',
                        order_by='$invoiced_total DESC',
                        enable_sq_join=True).fetch()
    timed("ORDER BY total ALL", q_order)

    # 8. WHERE + ORDER combined
    def q_combined():
        return db.query('invc.customer',
                        columns='$account_name,$n_invoices,$invoiced_total',
                        where='$n_invoices > :min_inv', min_inv=15,
                        order_by='$invoiced_total DESC',
                        enable_sq_join=True).fetch()
    timed("WHERE+ORDER combined", q_combined)

    # --- Year-by-year ---
    print("\n--- 2. Year-by-year aggregates (8 formulas, ALL) ---\n")

    def q_year():
        year_cols = ','.join(
            f'$invoiced_{y},$n_invoices_{y}' for y in (2022, 2023, 2024, 2025))
        return db.query('invc.customer',
                        columns=f'$account_name,{year_cols}',
                        enable_sq_join=True).fetch()
    timed("Year-by-year (separate subqueries)", q_year)

    # --- Greatest-N-per-group ---
    print("\n--- 3. Greatest-N-per-group (ALL 3200 rows) ---\n")

    def q_top_product():
        return db.query('invc.customer',
                        columns='$account_name,$top_product_id',
                        enable_sq_join=True).fetch()
    timed("Top product per customer CORRELATED", q_top_product)

    # --- State tops ---
    print("\n--- 4. Top customer+product per state (8 rows) ---\n")

    def q_state():
        return db.query('invc.state',
                        columns='$code,$name,$top_customer_id,$top_product_id',
                        enable_sq_join=True).fetch()
    timed("Top customer+product per state", q_state)

    # --- Cross-formula ---
    print("\n--- 5. Cross-formula: top_product + n_sold (ALL 3200) ---\n")

    def q_cross():
        return db.query('invc.customer',
                        columns='$account_name,$top_product_id,$top_product_n_sold').fetch()
    timed("top_product + n_sold CORRELATED", q_cross)

    # Verify
    r = db.query('invc.customer',
                 columns='$account_name,$top_product_id,$top_product_n_sold',
                 where="$account_name = :name", name='Coastal Renovations Group').fetch()
    if r:
        row = r[0]
        print(f"\n  Verification: {row['account_name']}, product={row['top_product_id']}, n_sold={row['top_product_n_sold']}")
        print(f"  Expected: n_sold=48 (raw SQL verified)")


if __name__ == '__main__':
    run()
