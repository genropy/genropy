#!/usr/bin/env python3
"""Import CSV data into test_invoice database (PostgreSQL or SQLite).

Usage:
    python import_csv.py --db postgres [--dbname test_invoice_pg] [--host localhost] [--port 5432]
    python import_csv.py --db sqlite --dbpath /path/to/test_invoice.db

Options:
    --with-invoices    Also import invoice and invoice_row CSVs
    --csv-dir DIR      Directory containing CSV files (default: ./export)
    --truncate         Truncate tables before importing
"""

import argparse
import csv
import os
import sys

SCHEMA = 'invc'

TABLES_ORDER = [
    'state',
    'customer_type',
    'vat_type',
    'payment_type',
    'postcode',
    'product_type',
    'product',
    'customer',
]

INVOICE_TABLES = [
    'invoice',
    'invoice_row',
]

SKIP_COLUMNS = {'pkey'}

TABLES_REVERSE = list(reversed(TABLES_ORDER + INVOICE_TABLES))


def get_pg_connection(dbname, host, port, user):
    import psycopg2
    return psycopg2.connect(dbname=dbname, host=host, port=port, user=user)


def get_sqlite_connection(dbpath):
    import sqlite3
    conn = sqlite3.connect(dbpath)
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def pg_table_name(table):
    return f'{SCHEMA}.invc_{table}'


def sqlite_table_name(table):
    return f'invc_{table}'


def convert_value(val, col_name):
    if val == '':
        return None
    return val


def truncate_tables(conn, db_type, tables):
    cur = conn.cursor()
    for table in tables:
        tname = pg_table_name(table) if db_type == 'postgres' else sqlite_table_name(table)
        if db_type == 'postgres':
            cur.execute(f'TRUNCATE {tname} CASCADE')
        else:
            cur.execute(f'DELETE FROM {tname}')
    conn.commit()
    cur.close()


def import_csv_file(conn, db_type, table, csv_path, batch_size=1000):
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        columns = [c for c in reader.fieldnames if c not in SKIP_COLUMNS]
        tname = pg_table_name(table) if db_type == 'postgres' else sqlite_table_name(table)

        if db_type == 'postgres':
            placeholders = ','.join([f'%({c})s' for c in columns])
        else:
            placeholders = ','.join([f':{c}' for c in columns])

        cols_str = ','.join(columns)
        sql = f'INSERT INTO {tname} ({cols_str}) VALUES ({placeholders})'

        cur = conn.cursor()
        count = 0
        batch = []

        for row in reader:
            record = {c: convert_value(row[c], c) for c in columns}
            batch.append(record)
            count += 1

            if len(batch) >= batch_size:
                if db_type == 'postgres':
                    cur.executemany(sql, batch)
                else:
                    cur.executemany(sql, batch)
                batch = []

        if batch:
            cur.executemany(sql, batch)

        conn.commit()
        cur.close()
        return count


def main():
    parser = argparse.ArgumentParser(description='Import CSV data into test_invoice database')
    parser.add_argument('--db', required=True, choices=['postgres', 'sqlite'],
                        help='Database type')
    parser.add_argument('--dbname', default='test_invoice_pg',
                        help='PostgreSQL database name (default: test_invoice_pg)')
    parser.add_argument('--host', default='localhost',
                        help='PostgreSQL host (default: localhost)')
    parser.add_argument('--port', default='5432',
                        help='PostgreSQL port (default: 5432)')
    parser.add_argument('--user', default=None,
                        help='PostgreSQL user (default: current user)')
    parser.add_argument('--dbpath', default=None,
                        help='SQLite database file path')
    parser.add_argument('--csv-dir', default=None,
                        help='Directory containing CSV files (default: ./export)')
    parser.add_argument('--with-invoices', action='store_true',
                        help='Also import invoice and invoice_row')
    parser.add_argument('--truncate', action='store_true',
                        help='Truncate tables before importing')

    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_dir = args.csv_dir or os.path.join(script_dir, 'export')

    if not os.path.isdir(csv_dir):
        print(f'CSV directory not found: {csv_dir}')
        sys.exit(1)

    tables = list(TABLES_ORDER)
    if args.with_invoices:
        tables.extend(INVOICE_TABLES)

    if args.db == 'postgres':
        user = args.user or os.environ.get('USER')
        conn = get_pg_connection(args.dbname, args.host, args.port, user)
        print(f'Connected to PostgreSQL: {args.dbname}@{args.host}:{args.port}')
    else:
        if not args.dbpath:
            print('--dbpath is required for SQLite')
            sys.exit(1)
        conn = get_sqlite_connection(args.dbpath)
        print(f'Connected to SQLite: {args.dbpath}')

    if args.truncate:
        truncate_order = [t for t in TABLES_REVERSE if t in tables]
        print(f'Truncating {len(truncate_order)} tables...')
        truncate_tables(conn, args.db, truncate_order)

    for table in tables:
        csv_path = os.path.join(csv_dir, f'{table}.csv')
        if not os.path.isfile(csv_path):
            print(f'  SKIP {table}: {csv_path} not found')
            continue
        count = import_csv_file(conn, args.db, table, csv_path)
        print(f'  {table}: {count} records imported')

    conn.close()
    print('Done!')


if __name__ == '__main__':
    main()
