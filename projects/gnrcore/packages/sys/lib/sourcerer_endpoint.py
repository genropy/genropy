"""Server-side helpers for the Sourcerer integration endpoint.

Functions in this module are shared between:
    - sys/webpages/ep_sourcerer.py (HTTP entry point exposed via @public_method)
    - downstream consumers that want to introspect/query a GenroPy DB
      in-process with the same shape as rpc_relationtree / rpc_query

Public surface:
    - classify_column(attr) -> (kind, has_subquery)
    - attr_to_json(attr) -> dict
    - bag_to_json(bag, depth=1) -> dict
    - build_table_schema(db, table_fullname, depth=1) -> dict
    - list_table_names(db) -> list[str]
    - run_query(db, table=None, count_only=False, max_rows=1000,
                statement_timeout_ms=3000, **kwargs) -> dict
"""

import time

DEFAULT_MAX_ROWS = 1000
DEFAULT_STATEMENT_TIMEOUT_MS = 3000


def classify_column(attr):
    """Classify a GenroPy column attribute dict.

    Returns:
        (kind, has_subquery): kind is one of
            'real', 'relation', 'alias', 'formula_subquery',
            'formula_sql', 'bagitem', 'pycolumn', 'virtual_other'.
        has_subquery is True only for formula_subquery (the costly kind).
    """
    if attr.get('joiner') or attr.get('tag') == 'relation':
        return 'relation', False
    if not attr.get('virtual_column'):
        return 'real', False
    if attr.get('relation_path'):
        return 'alias', False
    if attr.get('select'):
        return 'formula_subquery', True
    if attr.get('bagcolumn') or attr.get('itempath'):
        return 'bagitem', False
    if attr.get('sql_formula'):
        return 'formula_sql', False
    if attr.get('py_method') or attr.get('pyColumn'):
        return 'pycolumn', False
    return 'virtual_other', False


def attr_to_json(attr):
    """Convert a column attribute dict to a JSON-serializable subset."""
    out = {}
    for k, v in attr.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            out[k] = v
        elif isinstance(v, dict):
            sub = {sk: sv for sk, sv in v.items()
                   if isinstance(sv, (str, int, float, bool, type(None)))}
            if sub:
                out[k] = sub
    return out


def bag_to_json(bag, depth=1):
    """Recursively convert a relation tree Bag to a JSON-serializable dict.

    depth controls how deep relation children are expanded; nodes beyond
    are marked with truncated=True.
    """
    if bag is None:
        return None
    out = {}
    for node in bag:
        attr = node.attr
        kind, has_subquery = classify_column(attr)
        item = {'attr': attr_to_json(attr), 'kind': kind}
        if has_subquery:
            item['subquery'] = True
        v = node.value
        if v is None:
            pass
        elif hasattr(v, 'load') and not hasattr(v, 'nodes'):
            item['lazy'] = True
        elif hasattr(v, 'nodes'):
            if depth > 0:
                item['children'] = bag_to_json(v, depth=depth - 1)
            else:
                item['truncated'] = True
        out[node.label] = item
    return out


def build_table_schema(db, table_fullname, depth=1):
    """Build a JSON-serializable schema dict for a single table.

    Includes real columns, relations (with classification of join cardinality),
    and virtual columns (aliases, sql formulas, subqueries, etc.).
    """
    tbl_model = db.model.table(table_fullname)
    tree_bag = tbl_model.newRelationResolver().load()
    schema = bag_to_json(tree_bag, depth=depth) or {}
    vcols = tbl_model.get('virtual_columns')
    if vcols:
        for name, vc in vcols.items():
            attr = dict(vc.attributes)
            kind, has_subquery = classify_column(attr)
            entry = {'attr': attr_to_json(attr), 'kind': kind}
            if has_subquery:
                entry['subquery'] = True
            schema[name] = entry
    return schema


def list_table_names(db):
    """Return sorted fullnames of all tables visible from the DB."""
    return sorted(t.fullname for t in db.tables)


def _apply_statement_timeout(db, timeout_ms):
    """Best-effort SET LOCAL statement_timeout for PostgreSQL adapters."""
    try:
        adapter_name = type(db.adapter).__name__.lower()
        if 'postgres' in adapter_name or 'pg' in adapter_name:
            db.execute("SET LOCAL statement_timeout = %d" % int(timeout_ms))
    except Exception:
        pass


def run_query(site, table=None,
              max_rows=DEFAULT_MAX_ROWS,
              statement_timeout_ms=DEFAULT_STATEMENT_TIMEOUT_MS,
              **kwargs):
    """Execute a getSelection against a GenroPy site.

    Args:
        site: GnrWsgiSite (provides ``site.db`` and ``site.dummyPage.app``).
        table: fully qualified table name (e.g. ``'fatt.fattura'``).
        max_rows: cap applied when ``limit`` is missing or higher.
        statement_timeout_ms: PostgreSQL statement_timeout cap.
        **kwargs: forwarded to ``app.getSelection`` (columns, where, condition,
            distinct, group_by, having, order_by, limit, offset, pkeys,
            sqlparams, excludeLogicalDeleted, excludeDraft, countOnly, …).

    Returns:
        ``{'ok': bool, 'data': list[dict], 'info': {...}}``
    """
    kwargs['limit'] = min(int(kwargs.get('limit') or max_rows), max_rows)
    kwargs.setdefault('addPkeyColumn', False)

    _apply_statement_timeout(site.db, statement_timeout_ms)

    t0 = time.monotonic()
    try:
        rows, attrs = site.dummyPage.app.getSelection(
            table=table, recordResolver=False,
            output_mode='dictlist', **kwargs)
        if kwargs.get('countOnly'):
            rows = []
        total = attrs.get('totalrows', 0)
        return {
            'ok': True,
            'data': rows,
            'info': {
                'totalrows': total,
                'limit_applied': kwargs['limit'],
                'more': total >= kwargs['limit'],
                'servertime_ms': attrs.get('servertime') or int(
                    (time.monotonic() - t0) * 1000),
                'error': None,
            },
        }
    except Exception as e:
        return {
            'ok': False,
            'data': [],
            'info': {
                'error': str(e),
                'servertime_ms': int((time.monotonic() - t0) * 1000),
            },
        }


def build_relationtree_response(db, table=None, ticket_code=None):
    """Compose the full rpc_relationtree response shape.

    Mirrors the contract of ep_sourcerer.rpc_relationtree so callers
    (web HTTP or in-process) get the exact same structure.
    """
    info: dict = {'endpoint': 'rpc_relationtree', 'error': None}

    if not table:
        try:
            tables = list_table_names(db)
            return {'ok': True, 'ticket_code': ticket_code,
                    'info': info, 'tables': tables, 'trees': None}
        except Exception as e:
            info['error'] = str(e)
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'tables': None, 'trees': None}

    requested = [t.strip() for t in str(table).split(',') if t.strip()]
    info['tables_requested'] = requested
    trees = {}
    failed = {}
    for tname in requested:
        try:
            trees[tname] = build_table_schema(db, tname)
        except Exception as e:
            failed[tname] = str(e)
    if failed:
        info['tables_failed'] = failed

    if not trees:
        info['error'] = 'no_table_resolved'
        return {'ok': False, 'ticket_code': ticket_code,
                'info': info, 'tables': None, 'trees': None}

    return {'ok': True, 'ticket_code': ticket_code,
            'info': info, 'tables': None, 'trees': trees}
