#!/usr/bin/env python3
"""Benchmark: correlated subquery vs LEFT JOIN (sq_as_join).

Generates a large dataset and compares query times for:
- dvd_count vs dvd_count_join: COUNT(*)
- dvd_latest vs dvd_latest_join: MAX(purchasedate)
- dvd_count_available vs dvd_count_avail_join: COUNT(*) with WHERE available='yes'
- dvd_total_price vs dvd_total_price_join: SUM(price)
- dvd_count_like vs dvd_count_like_join: COUNT(*) with LIKE condition

Run with:
    cd gnrpy && PYTHONPATH=. python -m pytest tests/sql/benchmark_subquery_join.py -v -s
"""

import time
import random
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.sql.common import BaseGnrSqlTest, configurePackage
from gnr.sql.gnrsql import GnrSqlDb


NUM_MOVIES = 5000
NUM_DVDS = 50000
NUM_COUNTRIES = 10
NUM_SALES = 500000


class BaseBenchmark(BaseGnrSqlTest):

    @classmethod
    def _populate(cls):
        """Insert movies and dvds using raw SQL executemany."""
        conn = cls.db.adapter.connection()
        cursor = cls.db.adapter.cursor(conn)
        ph = '%s' if cls.db.implementation != 'sqlite' else '?'

        print(f'\nPopulating {NUM_MOVIES} movies...')
        movies = [(i, f'Movie_{i:05d}', 'ACTION', 2000 + (i % 25), 'US')
                  for i in range(NUM_MOVIES)]
        sql_movie = f'INSERT INTO video_movie (id, title, genre, year, nationality) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})'
        cursor.executemany(sql_movie, movies)

        print(f'Populating {NUM_DVDS} dvds...')
        random.seed(42)
        dvds = [(i, random.randint(0, NUM_MOVIES - 1),
                 f'{2003 + (i % 5)}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
                 'yes' if i % 3 else 'no',
                 round(random.uniform(5.0, 30.0), 2))
                for i in range(NUM_DVDS)]
        sql_dvd = f'INSERT INTO video_dvd (code, movie_id, purchasedate, available, price) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})'
        cursor.executemany(sql_dvd, dvds)

        print(f'Populating {NUM_COUNTRIES} countries...')
        countries = [(i, f'Country_{i}', f'C{i:02d}') for i in range(NUM_COUNTRIES)]
        sql_country = f'INSERT INTO video_country (id, name, code) VALUES ({ph}, {ph}, {ph})'
        cursor.executemany(sql_country, countries)

        print(f'Populating {NUM_SALES} sales...')
        sales = [(i, random.randint(0, NUM_DVDS - 1),
                  random.randint(0, NUM_COUNTRIES - 1),
                  f'{2005 + (i % 8)}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
                  round(random.uniform(10.0, 100.0), 2))
                 for i in range(NUM_SALES)]
        sql_sales = f'INSERT INTO video_sales (id, dvd_id, country_id, sale_date, amount) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})'
        cursor.executemany(sql_sales, sales)

        conn.commit()
        print(f'Data ready: {NUM_MOVIES} movies, {NUM_DVDS} dvds, {NUM_COUNTRIES} countries, {NUM_SALES} sales\n')

    def _run_query(self, table, columns, label, where=None, iterations=3):
        """Run query multiple times, return average time."""
        times = []
        result = None
        for _ in range(iterations):
            t0 = time.perf_counter()
            result = self.db.query(table, columns=columns, where=where).fetch()
            elapsed = time.perf_counter() - t0
            times.append(elapsed)
        avg = sum(times) / len(times)
        print(f'  {label}: {avg:.3f}s avg ({len(result)} rows, {iterations} iters)')
        return avg, result

    def _explain(self, table, columns, label):
        """Print EXPLAIN ANALYZE for a query."""
        q = self.db.query(table, columns=columns)
        conn = self.db.adapter.connection()
        cur = self.db.adapter.cursor(conn)
        cur.execute('EXPLAIN ANALYZE ' + q.sqltext, q.sqlparams)
        print(f'\n  EXPLAIN [{label}]:')
        for row in cur.fetchall():
            print(f'    {row[0]}')

    def _compare(self, table, inline_col, join_col, label):
        """Run inline vs join benchmark and verify results match."""
        print(f'\n--- {label} ---')
        t_inline, r_inline = self._run_query(table, f'$name,${inline_col}', 'Inline subquery')
        t_join, r_join = self._run_query(table, f'$name,${join_col}', 'LEFT JOIN')

        inline_vals = {r['name']: r[inline_col] for r in r_inline}
        join_vals = {r['name']: r[join_col] for r in r_join}
        mismatches = 0
        for title in inline_vals:
            v_i = inline_vals[title]
            v_j = join_vals[title]
            if v_i != v_j:
                # tolerate None vs 0 (COALESCE) and float rounding
                if v_i is None and v_j == 0 or v_j is None and v_i == 0:
                    continue
                if isinstance(v_i, (int, float)) and isinstance(v_j, (int, float)):
                    if abs(v_i - v_j) < 0.01:
                        continue
                mismatches += 1
                if mismatches <= 5:
                    print(f'    MISMATCH {title}: inline={v_i!r} join={v_j!r}')
        assert mismatches == 0, f'{mismatches} mismatches in {label}!'

        speedup = t_inline / t_join if t_join > 0 else float('inf')
        print(f'  => Speedup: {speedup:.1f}x')
        return t_inline, t_join

    def _compare_where(self, table, inline_col, join_col, where_inline, where_join, label):
        """Benchmark with WHERE on the formulaColumn."""
        print(f'\n--- {label} (WHERE) ---')
        t_inline, r_inline = self._run_query(table, f'$name,${inline_col}',
            'Inline subquery', where=where_inline)
        t_join, r_join = self._run_query(table, f'$name,${join_col}',
            'LEFT JOIN', where=where_join)
        print(f'  Inline: {len(r_inline)} rows, JOIN: {len(r_join)} rows')
        speedup = t_inline / t_join if t_join > 0 else float('inf')
        print(f'  => Speedup: {speedup:.1f}x')
        return t_inline, t_join

    def test_benchmark(self):
        """Benchmark: country→sales (10 countries, 500k sales = 50k sales/country)"""
        print(f'\n=== Benchmark [{self.name}]: {NUM_COUNTRIES} countries, {NUM_SALES} sales ===')

        T = 'video.country'
        results = []
        results.append(('SUM(amount)', *self._compare(
            T, 'total_sales', 'total_sales_join', 'SUM(amount)')))
        results.append(('SUM+genre', *self._compare(
            T, 'action_sales', 'action_sales_join', 'SUM(amount) WHERE genre=ACTION')))
        results.append(('COUNT(*)', *self._compare(
            T, 'sale_count', 'sale_count_join', 'COUNT(*)')))
        results.append(('WHERE SUM>thr', *self._compare_where(
            T, 'total_sales', 'total_sales_join',
            '$total_sales > 2500000', '$total_sales_join > 2500000',
            'SUM(amount) > threshold')))

        print(f'\n=== Summary [{self.name}] ===')
        print(f'  {"Column":<15} {"Inline":>8} {"JOIN":>8} {"Speedup":>8}')
        print(f'  {"-"*15} {"-"*8} {"-"*8} {"-"*8}')
        for label, t_i, t_j in results:
            sp = t_i / t_j if t_j > 0 else float('inf')
            print(f'  {label:<15} {t_i:>7.3f}s {t_j:>7.3f}s {sp:>7.1f}x')

        if self.db.implementation != 'sqlite':
            print(f'\n=== EXPLAIN ANALYZE ===')
            self._explain(T, '$name,$total_sales', 'SUM inline')
            self._explain(T, '$name,$total_sales_join', 'SUM join')

    def teardown_class(cls):
        cls.db.closeConnection()
        cls.db.dropDb(cls.dbname)


class TestBenchmark_sqlite(BaseBenchmark):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.name = 'sqlite'
        cls.dbname = cls.CONFIG['db.sqlite?filename'] + '_bench'
        cls.db = GnrSqlDb(dbname=cls.dbname)
        cls.db.createDb(cls.dbname)
        configurePackage(cls.db.packageSrc('video'))
        cls.db.startup()
        cls.db.checkDb(applyChanges=True)
        cls._populate()


class TestBenchmark_postgres3(BaseBenchmark):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.name = 'postgres3'
        cls.dbname = 'bench_sqjoin'
        cls.db = GnrSqlDb(implementation='postgres3',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password"))
        cls.db.createDb(cls.dbname)
        configurePackage(cls.db.packageSrc('video'))
        cls.db.startup()
        cls.db.checkDb(applyChanges=True)
        cls._populate()
