"""Simulate the compiler's relation resolution pattern.

The compiler starts from one table and resolves N dotted paths of
varying depth — each path corresponds to a column selected through
a chain of foreign keys (e.g. ``@invoice_id.@customer_id.name``).

This test collects real paths from the model, then measures:
- first pass (build): resolver executions + Bag navigation
- second pass (cached): pure Bag navigation, resolvers cached
- new request (cache cleared): full rebuild cost

Run with: pytest tests/sql/test_compiler_simulation.py -v -s
"""

import time

from gnr.core.gnrbag import Bag
from core.common import BaseGnrTest

def _collect_real_paths(bag, prefix='', max_depth=4, depth=0):
    """Walk the relation tree collecting all reachable dotted paths.

    Returns a list of (path, depth) tuples.
    """
    paths = []
    if bag is None or depth > max_depth:
        return paths
    for node in bag:
        attr = node.attr or {}
        label = node.label
        joiner = attr.get('joiner')
        current = f'{prefix}.{label}' if prefix else label
        if joiner:
            child = node.value
            if child is not None and isinstance(child, Bag):
                paths.extend(_collect_real_paths(child, current, max_depth, depth + 1))
        else:
            paths.append((current, depth))
    return paths


def _select_paths(all_paths, per_depth=10):
    """Pick up to per_depth paths from each depth level."""
    by_depth = {}
    for p, d in all_paths:
        by_depth.setdefault(d, []).append(p)
    selected = []
    depths = {}
    for d in sorted(by_depth):
        take = by_depth[d][:per_depth]
        selected.extend(take)
        depths[d] = len(take)
    return selected, depths

def setup_module(module):
    BaseGnrTest.setup_class()

def teardown_module(module):
    BaseGnrTest.teardown_class()

class TestCompilerSimulation(BaseGnrTest):
    """Simulate the compiler resolving paths from a single starting table."""

    def test_invoice_row_50_paths(self, db_sqlite):
        """50 paths from invoice_row: build, cached, new request."""
        db_sqlite.currentEnv.pop('_relations', None)
        tbl = db_sqlite.model.table('invc.invoice_row')
        all_paths = _collect_real_paths(tbl.relations, max_depth=4)
        selected, depths = _select_paths(all_paths, per_depth=10)

        print(f'\n=== Compiler simulation: invc.invoice_row, {len(selected)} paths ===')
        for d in sorted(depths):
            print(f'  depth {d}: {depths[d]} paths')

        # Build (first pass)
        db_sqlite.currentEnv.pop('_relations', None)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        build_ms = (time.perf_counter() - t0) * 1000

        # Cached (second pass, same request)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        cached_ms = (time.perf_counter() - t0) * 1000

        # New request (cache cleared)
        db_sqlite.currentEnv.pop('_relations', None)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        rebuild_ms = (time.perf_counter() - t0) * 1000

        print(f'\n  build:   {build_ms:8.2f} ms')
        print(f'  cached:  {cached_ms:8.2f} ms')
        print(f'  rebuild: {rebuild_ms:8.2f} ms')

    def test_invoice_30_paths(self, db_sqlite):
        """30 paths from invoice."""
        db_sqlite.currentEnv.pop('_relations', None)
        tbl = db_sqlite.model.table('invc.invoice')
        all_paths = _collect_real_paths(tbl.relations, max_depth=3)
        selected, depths = _select_paths(all_paths, per_depth=10)

        print(f'\n=== Compiler simulation: invc.invoice, {len(selected)} paths ===')
        for d in sorted(depths):
            print(f'  depth {d}: {depths[d]} paths')

        db_sqlite.currentEnv.pop('_relations', None)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        build_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        cached_ms = (time.perf_counter() - t0) * 1000

        print(f'\n  build:   {build_ms:8.2f} ms')
        print(f'  cached:  {cached_ms:8.2f} ms')

    def test_customer_30_paths(self, db_sqlite):
        """30 paths from customer (mix ascending + descending)."""
        db_sqlite.currentEnv.pop('_relations', None)
        tbl = db_sqlite.model.table('invc.customer')
        all_paths = _collect_real_paths(tbl.relations, max_depth=3)
        selected, depths = _select_paths(all_paths, per_depth=10)

        print(f'\n=== Compiler simulation: invc.customer, {len(selected)} paths ===')
        for d in sorted(depths):
            print(f'  depth {d}: {depths[d]} paths')

        db_sqlite.currentEnv.pop('_relations', None)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        build_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        cached_ms = (time.perf_counter() - t0) * 1000

        print(f'\n  build:   {build_ms:8.2f} ms')
        print(f'  cached:  {cached_ms:8.2f} ms')

    def test_multiple_tables_same_request(self, db_sqlite):
        """Simulate a request touching 5 tables (shared cache across tables)."""
        tables = [
            'invc.invoice_row',
            'invc.invoice',
            'invc.customer',
            'invc.product',
            'invc.staff',
        ]

        # Collect paths for all tables
        db_sqlite.currentEnv.pop('_relations', None)
        table_paths = {}
        for tbl_name in tables:
            tbl = db_sqlite.model.table(tbl_name)
            all_paths = _collect_real_paths(tbl.relations, max_depth=3)
            selected, _ = _select_paths(all_paths, per_depth=5)
            table_paths[tbl_name] = selected

        total_paths = sum(len(v) for v in table_paths.values())

        print(f'\n=== 5 tables in same request, {total_paths} paths total ===')
        for tbl_name, paths in table_paths.items():
            print(f'  {tbl_name}: {len(paths)} paths')

        # Build
        db_sqlite.currentEnv.pop('_relations', None)
        t0 = time.perf_counter()
        for tbl_name, paths in table_paths.items():
            tbl = db_sqlite.model.table(tbl_name)
            for p in paths:
                tbl.relations[p]
        build_ms = (time.perf_counter() - t0) * 1000

        # Cached
        t0 = time.perf_counter()
        for tbl_name, paths in table_paths.items():
            tbl = db_sqlite.model.table(tbl_name)
            for p in paths:
                tbl.relations[p]
        cached_ms = (time.perf_counter() - t0) * 1000

        print(f'\n  build:   {build_ms:8.2f} ms')
        print(f'  cached:  {cached_ms:8.2f} ms')
