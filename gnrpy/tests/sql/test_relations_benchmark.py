"""Benchmark for relation tree resolution with real dotted paths.

Issue #548: measures the cost of building and caching the relation
tree with the currentEnv per-request cache strategy.

Tests navigate using Bag dotted path (e.g. ``rels['@invoice_id.@customer_id.name']``)
which is how the compiler and application code access relations in practice.

Run with: pytest tests/sql/test_relations_benchmark.py -v -s
The -s flag is needed to see the printed timing table.
"""

import time

from gnr.core.gnrbag import Bag


def _collect_real_paths(bag, prefix='', max_depth=4, depth=0):
    """Walk the relation tree and collect all real dotted paths.

    Returns a list of (path, depth) tuples where path is a dotted
    string like '@invoice_id.@customer_id.name' and depth is how
    many relation hops it crosses.
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
                # relation node: recurse into the related table
                paths.extend(_collect_real_paths(child, current, max_depth, depth + 1))
        else:
            # leaf column
            paths.append((current, depth))
    return paths


class TestRelationPathsBenchmark:
    """Benchmark: resolve N real dotted paths, first pass vs cached."""

    def test_real_paths_build_vs_cached(self, db_sqlite):
        """Collect real paths from invoice_row, resolve all, measure build vs cache."""
        N = 50

        # Step 1: collect real paths (this triggers tree build, but we'll clear cache after)
        db_sqlite.currentEnv.pop('_relations', None)
        tbl = db_sqlite.model.table('invc.invoice_row')
        all_paths = _collect_real_paths(tbl.relations, max_depth=4)

        # Take up to N paths, sorted by depth (mix of short and long)
        all_paths.sort(key=lambda x: x[1])
        selected = [p for p, _ in all_paths[:N]]
        by_depth = {}
        for p, d in all_paths[:N]:
            by_depth.setdefault(d, []).append(p)

        print(f'\n=== {len(selected)} real paths from invc.invoice_row (max_depth=4) ===')
        for d in sorted(by_depth):
            print(f'  depth {d}: {len(by_depth[d])} paths')

        # Step 2: clear cache, first pass (build)
        db_sqlite.currentEnv.pop('_relations', None)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        build_ms = (time.perf_counter() - t0) * 1000

        # Step 3: second pass (all cached)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        cached_ms = (time.perf_counter() - t0) * 1000

        speedup = build_ms / cached_ms if cached_ms > 0 else float('inf')
        avg_build = build_ms / len(selected)
        avg_cached = cached_ms / len(selected)

        print(f'\n{"":10s} {"total_ms":>10s} {"avg_ms":>10s}')
        print(f'{"build":10s} {build_ms:10.2f} {avg_build:10.3f}')
        print(f'{"cached":10s} {cached_ms:10.2f} {avg_cached:10.3f}')
        print(f'{"speedup":10s} {speedup:9.1f}x')

    def test_real_paths_by_depth(self, db_sqlite):
        """Break down build vs cached time by path depth."""
        db_sqlite.currentEnv.pop('_relations', None)
        tbl = db_sqlite.model.table('invc.invoice_row')
        all_paths = _collect_real_paths(tbl.relations, max_depth=4)

        by_depth = {}
        for p, d in all_paths:
            by_depth.setdefault(d, []).append(p)

        print(f'\n=== Time breakdown by depth (invc.invoice_row) ===')
        print(f'{"depth":>5s} {"n_paths":>8s} {"build_ms":>10s} {"cached_ms":>10s} '
              f'{"avg_build":>10s} {"avg_cached":>10s} {"speedup":>8s}')
        print('-' * 70)

        for d in sorted(by_depth):
            paths = by_depth[d]
            # Clear and measure build
            db_sqlite.currentEnv.pop('_relations', None)
            t0 = time.perf_counter()
            for p in paths:
                tbl.relations[p]
            build_ms = (time.perf_counter() - t0) * 1000

            # Measure cached
            t0 = time.perf_counter()
            for p in paths:
                tbl.relations[p]
            cached_ms = (time.perf_counter() - t0) * 1000

            speedup = build_ms / cached_ms if cached_ms > 0 else float('inf')
            avg_b = build_ms / len(paths)
            avg_c = cached_ms / len(paths)
            print(f'{d:5d} {len(paths):8d} {build_ms:10.2f} {cached_ms:10.2f} '
                  f'{avg_b:10.3f} {avg_c:10.3f} {speedup:7.1f}x')

    def test_multiple_tables_comparison(self, db_sqlite):
        """Compare build vs cached across different starting tables."""
        tables = [
            'invc.invoice_row',
            'invc.invoice',
            'invc.customer',
            'invc.product',
            'invc.staff',
        ]
        N = 30

        print(f'\n=== Build vs cached across tables (up to {N} paths, max_depth=3) ===')
        print(f'{"table":25s} {"n_paths":>8s} {"build_ms":>10s} {"cached_ms":>10s} {"speedup":>8s}')
        print('-' * 65)

        for tbl_name in tables:
            db_sqlite.currentEnv.pop('_relations', None)
            tbl = db_sqlite.model.table(tbl_name)
            all_paths = _collect_real_paths(tbl.relations, max_depth=3)
            selected = [p for p, _ in all_paths[:N]]

            # Build
            db_sqlite.currentEnv.pop('_relations', None)
            t0 = time.perf_counter()
            for p in selected:
                tbl.relations[p]
            build_ms = (time.perf_counter() - t0) * 1000

            # Cached
            t0 = time.perf_counter()
            for p in selected:
                tbl.relations[p]
            cached_ms = (time.perf_counter() - t0) * 1000

            speedup = build_ms / cached_ms if cached_ms > 0 else float('inf')
            print(f'{tbl_name:25s} {len(selected):8d} {build_ms:10.2f} {cached_ms:10.2f} {speedup:7.1f}x')

    def test_new_request_cost(self, db_sqlite):
        """Simulate two consecutive requests (clear cache between them)."""
        N = 50
        db_sqlite.currentEnv.pop('_relations', None)
        tbl = db_sqlite.model.table('invc.invoice_row')
        all_paths = _collect_real_paths(tbl.relations, max_depth=4)
        selected = [p for p, _ in all_paths[:N]]

        # Request 1
        db_sqlite.currentEnv.pop('_relations', None)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        req1_ms = (time.perf_counter() - t0) * 1000

        # Request 2 (cache cleared = new request)
        db_sqlite.currentEnv.pop('_relations', None)
        t0 = time.perf_counter()
        for p in selected:
            tbl.relations[p]
        req2_ms = (time.perf_counter() - t0) * 1000

        print(f'\n=== Two consecutive requests ({len(selected)} paths each) ===')
        print(f'request 1: {req1_ms:.2f} ms')
        print(f'request 2: {req2_ms:.2f} ms (rebuilt from scratch)')
