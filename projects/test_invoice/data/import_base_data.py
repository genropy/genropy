"""Import base data (CSV) into test_invoice_pg via Genropy.

Used by CI to populate the DB after gnrdbsetup creates the schema.
Imports lookup tables, customers, and products in FK-safe order.
Invoice data is loaded per-session by the test conftest.
"""
import csv
import os
import sys

from gnr.web.gnrwsgisite import GnrWsgiSite

EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'export')

TABLES_ORDER = [
    ('invc.customer_type', 'customer_type.csv'),
    ('invc.payment_type', 'payment_type.csv'),
    ('invc.state', 'state.csv'),
    ('invc.vat_type', 'vat_type.csv'),
    ('invc.postcode', 'postcode.csv'),
    ('invc.product_type', 'product_type.csv'),
    ('invc.product', 'product.csv'),
    ('invc.customer', 'customer.csv'),
]


def main():
    site = GnrWsgiSite('test_invoice_pg')
    db = site.db
    for table_name, csv_file in TABLES_ORDER:
        path = os.path.join(EXPORT_DIR, csv_file)
        tbl = db.table(table_name)
        with open(path, newline='') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                clean = {k: (v if v != '' else None) for k, v in row.items()}
                tbl.insert(clean)
                count += 1
        db.commit()
        print(f'{table_name}: {count} rows')
    print('Done.')


if __name__ == '__main__':
    sys.exit(main() or 0)
