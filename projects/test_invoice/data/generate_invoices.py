#!/usr/bin/env python3
"""Generate random invoices and invoice rows for the test_invoice app.

Uses GnrApp to connect to a Genropy instance and generates realistic
invoice data for an Australian hardware store.

Usage:
    # Small dataset (sqlite / pg):
    python generate_invoices.py test_invoice \\
        --customers-per-state 2:3:5 \\
        --invoices-per-year 1:2:5 \\
        --rows-per-invoice 2:3:6

    # XL dataset (pg_xl):
    python generate_invoices.py test_invoice_pg_xl \\
        --customers-per-state 300:400:500 \\
        --invoices-per-year 14:30:80 \\
        --rows-per-invoice 6:15:50

Parameters use triangular distribution (min:mode:max) for natural variation.

Features:
    - Iterates state → customer → year for structured data generation
    - Dates spread across 2022-01-01 to 2025-06-30
    - Price history with semester-based multipliers (inflation simulation)
    - Invoices sorted by date before insert (required by Genropy counter)
    - Triggers disabled for bulk insert performance
"""

import argparse
import random
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


PRICE_MULTIPLIERS = {
    (2022, 1): Decimal('0.95'),
    (2022, 2): Decimal('0.97'),
    (2023, 1): Decimal('1.00'),
    (2023, 2): Decimal('1.05'),
    (2024, 1): Decimal('1.08'),
    (2024, 2): Decimal('1.10'),
    (2025, 1): Decimal('1.12'),
    (2025, 2): Decimal('1.15'),
}

YEARS = [2022, 2023, 2024, 2025]


def get_semester(d):
    return (d.year, 1 if d.month <= 6 else 2)


def get_price_for_date(base_price, invoice_date):
    semester = get_semester(invoice_date)
    multiplier = PRICE_MULTIPLIERS.get(semester, Decimal('1.00'))
    return (base_price * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def random_date_in_year(year):
    start = date(year, 1, 1)
    end = min(date(year, 12, 31), date(2025, 6, 30))
    if start > end:
        return None
    days_range = (end - start).days
    return start + timedelta(days=random.randint(0, days_range))


def tri(low, mode, high):
    return int(random.triangular(low, high, mode))


def parse_range(s):
    """Parse 'min:mode:max' into (low, mode, high) tuple of ints."""
    parts = s.split(':')
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"Expected min:mode:max, got '{s}'")
    return int(parts[0]), int(parts[1]), int(parts[2])


def generate(instance_name, seed=42, customers_per_state=(2, 3, 5),
             invoices_per_year=(1, 2, 5), rows_per_invoice=(2, 3, 6)):
    from gnr.app.gnrapp import GnrApp

    random.seed(seed)
    app = GnrApp(instance_name)
    db = app.db

    tbl_invoice = db.table('invc.invoice')
    tbl_row = db.table('invc.invoice_row')

    # Disable triggers for bulk insert
    original_trigger = getattr(tbl_row, 'trigger_onInserted', None)
    tbl_row.trigger_onInserted = lambda record=None: None

    # Load states
    states = db.table('invc.state').query(
        columns='$code', order_by='$code').fetch()

    # Load products
    products = db.table('invc.product').query(
        columns='$id, $unit_price, @vat_type_code.vat_rate AS prod_vat_rate'
    ).fetch()

    if not states:
        print('No states found. Import base data first.')
        sys.exit(1)
    if not products:
        print('No products found. Import base data first.')
        sys.exit(1)

    print(f'States: {len(states)}, Products: {len(products)}')

    # Iterate state → customer → year
    all_invoices = []
    selected_customers = []

    for state_row in states:
        state_code = state_row['code']
        customers = db.table('invc.customer').query(
            columns='$id',
            where='$state=:state', state=state_code,
            order_by='$id').fetch()

        if not customers:
            print(f'  State {state_code}: no customers, skipping')
            continue

        n_cust = min(tri(*customers_per_state), len(customers))
        chosen = random.sample(list(customers), n_cust)
        selected_customers.extend(chosen)
        print(f'  State {state_code}: {len(customers)} customers, selected {n_cust}')

        for cust in chosen:
            customer_id = cust['id']

            for year in YEARS:
                n_inv = tri(*invoices_per_year)

                for _ in range(n_inv):
                    inv_date = random_date_in_year(year)
                    if inv_date is None:
                        continue

                    n_rows = tri(*rows_per_invoice)
                    rows = []
                    total = Decimal('0')
                    vat_total = Decimal('0')

                    for _ in range(n_rows):
                        prod = random.choice(products)
                        quantity = random.randint(1, 50)
                        base_price = Decimal(str(prod['unit_price']))
                        unit_price = get_price_for_date(base_price, inv_date)
                        prod_vat_rate = Decimal(str(prod['prod_vat_rate'] or 0))
                        tot_price = (unit_price * quantity).quantize(
                            Decimal('0.01'), rounding=ROUND_HALF_UP)
                        vat = (tot_price * prod_vat_rate / Decimal('100')).quantize(
                            Decimal('0.01'), rounding=ROUND_HALF_UP)

                        total += tot_price
                        vat_total += vat

                        rows.append({
                            'product_id': prod['id'],
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'tot_price': tot_price,
                            'vat': vat,
                            'vat_rate': prod_vat_rate,
                        })

                    all_invoices.append({
                        'customer_id': customer_id,
                        'date': inv_date,
                        'total': total,
                        'vat_total': vat_total,
                        'gross_total': total + vat_total,
                        '_rows': rows,
                    })

    # Sort by date for counter compatibility
    all_invoices.sort(key=lambda x: x['date'])

    print(f'\nGenerated {len(all_invoices)} invoices '
          f'for {len(selected_customers)} customers. Inserting...')
    total_rows = 0
    for i, inv_data in enumerate(all_invoices):
        rows = inv_data.pop('_rows')
        tbl_invoice.insert(inv_data)
        invoice_id = inv_data['id']

        for row_data in rows:
            row_data['invoice_id'] = invoice_id
            tbl_row.insert(row_data)
            total_rows += 1

        if (i + 1) % 5000 == 0:
            db.commit()
            print(f'  {i + 1}/{len(all_invoices)} invoices, {total_rows} rows...')

    db.commit()

    # Restore trigger
    if original_trigger:
        tbl_row.trigger_onInserted = original_trigger

    print(f'Done! {len(all_invoices)} invoices, {total_rows} invoice rows.')


def main():
    parser = argparse.ArgumentParser(
        description='Generate random invoices for test_invoice app')
    parser.add_argument('instance', help='Genropy instance name')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--customers-per-state', type=parse_range,
                        default=(2, 3, 5),
                        help='min:mode:max customers per state (default: 2:3:5)')
    parser.add_argument('--invoices-per-year', type=parse_range,
                        default=(1, 2, 5),
                        help='min:mode:max invoices per customer per year (default: 1:2:5)')
    parser.add_argument('--rows-per-invoice', type=parse_range,
                        default=(2, 3, 6),
                        help='min:mode:max rows per invoice (default: 2:3:6)')
    args = parser.parse_args()
    generate(args.instance, seed=args.seed,
             customers_per_state=args.customers_per_state,
             invoices_per_year=args.invoices_per_year,
             rows_per_invoice=args.rows_per_invoice)


if __name__ == '__main__':
    main()
