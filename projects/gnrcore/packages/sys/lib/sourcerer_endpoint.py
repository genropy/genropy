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


def run_query(db, table=None, count_only=False,
              max_rows=DEFAULT_MAX_ROWS,
              statement_timeout_ms=DEFAULT_STATEMENT_TIMEOUT_MS,
              app=None, **kwargs):
    """Execute a query against a GenroPy DB, returning the same shape that
    rpc_query produces over HTTP.

    Two execution paths:
        - If ``app`` is provided, uses ``app.getSelection`` (web context: full
          virtual_column resolution, alias expansion, etc.).
        - Otherwise falls back to ``db.table(table).query(**kwargs).fetch()``
          for in-process callers without a web app.

    Args:
        db: GenroPy db connection.
        table: Fully qualified table name (e.g. ``'fatt.fattura'``).
        count_only: If True, return only the row count.
        max_rows: Cap applied when ``limit`` is missing or higher.
        statement_timeout_ms: PostgreSQL statement_timeout cap (best effort).
        app: Optional GnrApp / web app proxy with ``getSelection``.
        **kwargs: Forwarded to getSelection / tbl.query (columns, where,
            distinct, group_by, having, order_by, limit, etc.).

    Returns:
        dict: {
            'ok': bool,
            'data': list[dict],
            'info': {
                'totalrows': int,
                'more': bool,
                'limit_applied': int|None,
                'servertime_ms': int,
                'error': str|None
            }
        }
    """
    info: dict = {'error': None}

    if not table and not count_only:
        # getSelection variant lets the caller pass table inside kwargs;
        # tbl.query variant requires it explicitly. We require it always
        # for clarity.
        return {'ok': False, 'data': [],
                'info': {'error': 'missing required parameter: table'}}

    # Cap limit
    if count_only:
        cap_applied = False
        info['limit_applied'] = kwargs.get('limit')
    else:
        requested = kwargs.get('limit')
        cap_applied = (requested is None
                       or (isinstance(requested, int)
                           and requested > max_rows))
        kwargs['limit'] = max_rows if cap_applied else requested
        info['limit_applied'] = kwargs['limit']

    kwargs.pop('recordResolver', None)

    _apply_statement_timeout(db, statement_timeout_ms)

    t0 = time.monotonic()
    try:
        if app is not None:
            # Web context: rich getSelection (preserves virtual cols)
            data_bag, attrs = app.getSelection(
                table=table, recordResolver=False, **kwargs)
            rows = []
            if not count_only:
                for k in data_bag.keys():
                    node = data_bag.getNode(k)
                    row = dict(node.attr)
                    row.pop('_customClasses', None)
                    row.pop('_attributes', None)
                    rows.append(row)
            info['totalrows'] = attrs.get('totalrows', 0)
            info['servertime_ms'] = attrs.get('servertime')
        else:
            # In-process: direct table.query (lighter)
            tbl = db.table(table)
            sel = tbl.query(**kwargs)
            if count_only:
                rows = []
                info['totalrows'] = sel.count()
            else:
                fetched = sel.fetch()
                rows = [dict(r) for r in fetched]
                info['totalrows'] = len(rows)
            info['servertime_ms'] = int(
                (time.monotonic() - t0) * 1000)

        info['more'] = (cap_applied
                        and info['totalrows'] >= max_rows)
        return {'ok': True, 'data': rows, 'info': info}
    except Exception as e:
        info['error'] = str(e)
        info['servertime_ms'] = int((time.monotonic() - t0) * 1000)
        return {'ok': False, 'data': [], 'info': info}


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
