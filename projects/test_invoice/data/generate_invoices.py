#!/usr/bin/env python3
"""Generate random invoices and invoice rows for the test_invoice app.

Uses GnrApp to connect to a Genropy instance and generates realistic
invoice data for an Australian hardware store.

Usage:
    python generate_invoices.py <instance_name>
    python generate_invoices.py test_invoice          # SQLite
    python generate_invoices.py test_invoice_pg        # PostgreSQL

Features:
    - 0-30 invoices per customer (5% exceptional customers get 30-60)
    - Dates spread across 2022-01-01 to 2025-06-30
    - Price history with semester-based multipliers (inflation simulation)
    - 1-20 rows per invoice (5% get 30-50 rows)
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

DATE_START = date(2022, 1, 1)
DATE_END = date(2025, 6, 30)


def get_semester(d):
    return (d.year, 1 if d.month <= 6 else 2)


def get_price_for_date(base_price, invoice_date):
    semester = get_semester(invoice_date)
    multiplier = PRICE_MULTIPLIERS.get(semester, Decimal('1.00'))
    return (base_price * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def random_date():
    days_range = (DATE_END - DATE_START).days
    return DATE_START + timedelta(days=random.randint(0, days_range))


def generate(instance_name, seed=42):
    from gnr.app.gnrapp import GnrApp

    random.seed(seed)
    app = GnrApp(instance_name)
    db = app.db

    tbl_invoice = db.table('invc.invoice')
    tbl_row = db.table('invc.invoice_row')

    # Disable triggers for bulk insert
    original_trigger = getattr(tbl_row, 'trigger_onInserted', None)
    tbl_row.trigger_onInserted = lambda record=None: None

    # Load customers and products
    customers = db.table('invc.customer').query(columns='$id').fetch()
    products = db.table('invc.product').query(
        columns='$id, $unit_price, @vat_type_code.vat_rate AS prod_vat_rate'
    ).fetch()

    if not customers:
        print('No customers found. Import base data first.')
        sys.exit(1)
    if not products:
        print('No products found. Import base data first.')
        sys.exit(1)

    print(f'Customers: {len(customers)}, Products: {len(products)}')

    # Pre-generate all invoices with their rows (unsorted)
    all_invoices = []
    for cust in customers:
        customer_id = cust['id']
        if random.random() < 0.05:
            num_invoices = random.randint(30, 60)
        else:
            num_invoices = random.randint(0, 30)

        for _ in range(num_invoices):
            inv_date = random_date()

            if random.random() < 0.05:
                num_rows = random.randint(30, 50)
            else:
                num_rows = random.randint(1, 20)

            rows = []
            total = Decimal('0')
            vat_total = Decimal('0')

            for _ in range(num_rows):
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

    print(f'Generated {len(all_invoices)} invoices. Inserting...')
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
    args = parser.parse_args()
    generate(args.instance, seed=args.seed)


if __name__ == '__main__':
    main()
