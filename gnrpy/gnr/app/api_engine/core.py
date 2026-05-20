"""ApiEngine — application-level facade for introspection and JSON-safe
read access to a GenroPy database.

The engine is constructed from a ``GnrApp`` instance, or from an
instance name (a fresh ``GnrApp`` is then created). Once built, it
exposes a uniform surface:

- package and table enumeration
- column-level typing for code generation
- relation-tree schema for interactive exploration
- OpenAPI schema synthesis (read + write)
- safe query execution returning JSON-safe envelopes

OpenAPI exposure is opt-in: a table or package must declare
``openapi=True`` (or a richer value) to appear in OpenAPI output.
Individual columns can override with ``openapi=False`` (excluded
entirely) or ``openapi='R'`` (read-only). System columns
(``__`` prefix) are never writable; ``pycolumn`` columns never
appear in OpenAPI output.
"""

import time

DEFAULT_DEPTH = 1


# ---------------------------------------------------------------------------
# Pure helpers — module private, no app/db state
# ---------------------------------------------------------------------------

def _classify_column(attr):
    """Classify a GenroPy column attribute dict.

    Returns ``(kind, has_subquery)`` where ``kind`` is one of ``real``,
    ``relation``, ``alias``, ``formula_subquery``, ``formula_sql``,
    ``bagitem``, ``pycolumn``, ``virtual_other``.
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


def _attr_to_json(attr):
    """Project a column attribute dict to a JSON-safe subset."""
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


def _bag_to_json(bag, depth=DEFAULT_DEPTH, relations_only=False):
    """Convert a relation-tree Bag to a JSON-safe dict.

    ``depth`` controls how deep child relations are expanded; nodes
    beyond are flagged ``truncated``. ``relations_only`` skips every
    non-relation node.
    """
    if bag is None:
        return None
    out = {}
    for node in bag:
        attr = node.attr
        kind, has_subquery = _classify_column(attr)
        if relations_only and kind != 'relation':
            continue
        item = {'attr': _attr_to_json(attr), 'kind': kind}
        if has_subquery:
            item['subquery'] = True
        v = node.value
        if v is None:
            pass
        elif hasattr(v, 'load') and not hasattr(v, 'nodes'):
            item['lazy'] = True
        elif hasattr(v, 'nodes'):
            if depth > 0:
                item['children'] = _bag_to_json(
                    v, depth=depth - 1, relations_only=relations_only)
            else:
                item['truncated'] = True
        out[node.label] = item
    return out


# ---------------------------------------------------------------------------
# dtype → Python / OpenAPI mapping
# ---------------------------------------------------------------------------

# Names mirror what gnr.core.gnrclasses.GnrClassCatalog associates with each
# dtype. Kept here as a local table to avoid importing the catalog at
# module load: the module stays usable without a db connection.

_DTYPE_PYTHON = {
    'T': 'str', 'A': 'str', 'P': 'str', 'TEXT': 'str',
    'R': 'float', 'F': 'float',
    'L': 'int', 'I': 'int',
    'B': 'bool',
    'D': 'date',
    'DH': 'datetime', 'DT': 'datetime', 'DHZ': 'datetime',
    'H': 'time', 'HZ': 'time',
    'TD': 'timedelta',
    'N': 'Decimal',
    'BAG': 'Bag',
    'JS': 'list',
}

_DTYPE_OPENAPI = {
    # textual
    'T': ('string', None), 'A': ('string', None), 'P': ('string', None),
    'TEXT': ('string', None),
    # numeric
    'R': ('number', 'float'), 'F': ('number', 'float'),
    'L': ('integer', 'int64'), 'I': ('integer', 'int64'),
    # boolean
    'B': ('boolean', None),
    # temporal
    'D': ('string', 'date'),
    'DH': ('string', 'date-time'), 'DT': ('string', 'date-time'),
    'DHZ': ('string', 'date-time'),
    'H': ('string', 'time'), 'HZ': ('string', 'time'),
    'TD': ('string', 'duration'),
    # Decimal is serialized as string to preserve precision
    'N': ('string', 'decimal'),
    # structured
    'BAG': ('object', 'gnr-bag'),
    'JS': ('array', None),
}


def _dtype_to_python(dtype):
    return _DTYPE_PYTHON.get((dtype or '').upper(), 'Any')


def _dtype_to_openapi(dtype):
    t, fmt = _DTYPE_OPENAPI.get((dtype or '').upper(), ('string', None))
    return t, fmt


# ---------------------------------------------------------------------------
# Internal helpers for openapi exposure rules
# ---------------------------------------------------------------------------

def _table_openapi_setting(tbl_obj):
    """Return the table-level openapi setting: False, True, or dict."""
    return tbl_obj.attributes.get('openapi', False)


def _package_openapi_setting(pkg_obj):
    return pkg_obj.attributes.get('openapi', False)


def _column_openapi_setting(attrs):
    """Return one of: False, True, 'R'. Defaults to True when absent."""
    val = attrs.get('openapi')
    if val is None:
        return True
    return val


def _is_system_column(colname):
    return colname.startswith('__')


# Allowed opt_kwargs for run_query
_RUN_QUERY_OPT_KEYS = frozenset((
    'excludeLogicalDeleted', 'excludeDraft', 'mode', 'checkPermissions',
))


# ---------------------------------------------------------------------------
# ApiEngine
# ---------------------------------------------------------------------------

class ApiEngine:
    """Facade for introspection and JSON-safe read access to a GenroPy DB.

    Construct with either a ``GnrApp`` instance or an instance name
    (a fresh ``GnrApp`` is created in that case)::

        engine = ApiEngine('test_invoice_pg')
        engine = ApiEngine(my_app)

    ``max_rows`` is an optional engine-level safety cap that applies to
    ``run_query`` unless the call overrides it.

    A per-query wall-clock timeout is not currently supported: gnrsql
    has no native primitive for it (tracked by genropy issue #919).
    Until that lands, callers that need to bound query duration must
    use external means (asyncio timeout, signal alarm, ...).

    Args:
        app: ``GnrApp`` instance or instance name (str).
        max_rows: default clamp on ``limit`` for ``run_query``.
    """

    def __init__(self, app, *, max_rows=None):
        if isinstance(app, str):
            from gnr.app.gnrapp import GnrApp
            app = GnrApp(app)
        self.app = app
        self.max_rows = max_rows

    # -- shorthand ----------------------------------------------------------

    @property
    def db(self):
        return self.app.db

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------

    def _resolve_targets(self, target):
        """Resolve a target argument to a list of table fullnames.

        Accepts:
            - None: every table of the db.
            - str without '.': a package name; expands to its tables.
            - str with '.': a table fullname; returns ``[target]``.
            - iterable of strings: each resolved as above and flattened.

        Raises ``ValueError`` when a name does not resolve to a known
        package or table.
        """
        if target is None:
            return sorted(t.fullname for t in self.db.tables)
        if isinstance(target, str):
            return self._resolve_single(target)
        if isinstance(target, (list, tuple, set)):
            out = []
            seen = set()
            for item in target:
                for name in self._resolve_single(item):
                    if name not in seen:
                        seen.add(name)
                        out.append(name)
            return out
        raise ValueError(
            'target must be None, str, or iterable of str; got %r' % (target,))

    def _resolve_single(self, name):
        if '.' in name:
            try:
                self.db.table(name)
            except Exception as exc:
                raise ValueError('Unknown table %r' % name) from exc
            return [name]
        if name not in self.db.packages:
            raise ValueError('Unknown package %r' % name)
        pkg = self.db.packages[name]
        return sorted('%s.%s' % (name, tname) for tname in pkg.tables.keys())

    def _resolve_package(self, name):
        if name not in self.db.packages:
            raise ValueError('Unknown package %r' % name)
        return self.db.packages[name]

    # ------------------------------------------------------------------
    # Enumeration
    # ------------------------------------------------------------------

    def package_names(self):
        """Sorted list of all package names in the database."""
        return sorted(self.db.packages.keys())

    def table_names(self, target=None):
        """List table fullnames.

        ``target`` may be ``None`` (the whole db) or a package name.
        """
        if target is None:
            return sorted(t.fullname for t in self.db.tables)
        if '.' in target:
            raise ValueError(
                'table_names target must be a package name or None; '
                'got table fullname %r' % target)
        pkg = self._resolve_package(target)
        return sorted('%s.%s' % (target, t) for t in pkg.tables.keys())

    # ------------------------------------------------------------------
    # Relation-tree schema
    # ------------------------------------------------------------------

    def table_schema(self, target, depth=DEFAULT_DEPTH, relations_only=False):
        """Relation-tree schema for one or more tables.

        Returns ``{table_fullname: {colname: {...}}}`` regardless of
        target shape. ``depth`` bounds expansion of relation children;
        ``relations_only`` skips non-relation entries entirely.
        """
        tables = self._resolve_targets(target)
        out = {}
        for fullname in tables:
            tbl_model = self.db.model.table(fullname)
            tree_bag = tbl_model.newRelationResolver().load()
            schema = _bag_to_json(
                tree_bag, depth=depth, relations_only=relations_only) or {}
            if not relations_only:
                vcols = tbl_model.get('virtual_columns')
                if vcols:
                    for name, vc in vcols.items():
                        attr = dict(vc.attributes)
                        kind, has_subquery = _classify_column(attr)
                        entry = {'attr': _attr_to_json(attr), 'kind': kind}
                        if has_subquery:
                            entry['subquery'] = True
                        schema[name] = entry
            out[fullname] = schema
        return out

    # ------------------------------------------------------------------
    # Flat column typing
    # ------------------------------------------------------------------

    def table_columns(self, target):
        """Flat per-table column typing.

        Returns ``{table_fullname: {colname: column_info}}`` where
        ``column_info`` carries ``dtype``, ``python_type``,
        ``openapi_type``, ``openapi_format``, ``kind``, ``nullable``,
        ``size``, ``unique``, ``pkey``, ``fkey``, ``default``,
        ``name_long``, ``openapi`` (raw setting from the model).

        ``pycolumn`` columns and the relation entries are excluded
        (relations surface as ``fkey`` on their owning column when
        present). All other kinds are included.
        """
        tables = self._resolve_targets(target)
        out = {}
        for fullname in tables:
            out[fullname] = self._collect_columns(fullname)
        return out

    def _collect_columns(self, fullname):
        tbl = self.db.table(fullname)
        cols_dict = {}
        # Real columns
        for colname, col in tbl.columns.items():
            attrs = dict(col.attributes)
            if attrs.get('tag') != 'column':
                continue
            if attrs.get('virtual_column'):
                continue
            cols_dict[colname] = self._column_info(colname, attrs, tbl, col=col)
        # Virtual columns from model (alias, formula_sql, formula_subquery,
        # bagitem, virtual_other — pycolumn excluded)
        vcols = self.db.model.table(fullname).get('virtual_columns') or {}
        for colname, vcol in vcols.items():
            attrs = dict(vcol.attributes)
            kind, _ = _classify_column(attrs)
            if kind == 'pycolumn':
                continue
            cols_dict[colname] = self._column_info(colname, attrs, tbl)
        return cols_dict

    def _column_info(self, colname, attrs, tbl, col=None):
        kind, has_subquery = _classify_column(attrs)
        dtype = attrs.get('dtype')
        openapi_type, openapi_format = _dtype_to_openapi(dtype)
        python_type = _dtype_to_python(dtype)
        is_pkey = (colname == tbl.pkey)
        notnull = bool(attrs.get('notnull')) or is_pkey
        info = {
            'kind': kind,
            'dtype': dtype,
            'python_type': python_type,
            'openapi_type': openapi_type,
            'openapi_format': openapi_format,
            'nullable': not notnull,
            'pkey': is_pkey,
            'size': attrs.get('size'),
            'unique': bool(attrs.get('unique')),
            'default': attrs.get('default'),
            'name_long': attrs.get('name_long'),
            'openapi': attrs.get('openapi'),
            'system': _is_system_column(colname),
        }
        if has_subquery:
            info['subquery'] = True
        # FK detection for real columns: ask the model directly
        if col is not None:
            related = col.relatedColumn()
            if related is not None:
                info['fkey'] = {
                    'target_table': related.table.fullname,
                    'target_column': related.name,
                }
        # FK info embedded in the joiner attribute (virtual relation entries)
        joiner = attrs.get('joiner')
        if joiner:
            info['fkey'] = {
                'target': joiner.get('one_relation'),
                'mode': joiner.get('mode'),
                'on_delete': joiner.get('onDelete'),
                'on_update': joiner.get('onUpdate_sql'),
                'relation_name': joiner.get('relation_name'),
                'one_one': bool(joiner.get('one_one')),
            }
        if attrs.get('relation_path'):
            info['relation_path'] = attrs['relation_path']
        return info

    # ------------------------------------------------------------------
    # OpenAPI schema synthesis
    # ------------------------------------------------------------------

    def openapi_schema(self, target=None, readonly=True):
        """Build an OpenAPI-friendly schema for the requested target.

        Behavior depends on ``target``:
            - ``None``: every table of every package with
              ``openapi=True`` is included.
            - package name: every table of that package with
              ``openapi=True``. Raises if the package itself is not
              exposed.
            - table fullname: just that table. Raises if the table is
              not exposed.
            - iterable: each element resolved individually.

        ``readonly=True`` (default) emits the complete schema with
        read-only columns annotated ``readOnly: True``; ``readonly=False``
        omits read-only columns entirely (suitable as POST/PUT body
        schema).

        Returns ``{table_fullname: {<openapi schema object>}}``.
        """
        explicit_table = isinstance(target, str) and '.' in target
        explicit_package = (isinstance(target, str)
                            and '.' not in target
                            and target is not None)
        tables: list[str]
        if explicit_package:
            assert isinstance(target, str)
            pkg = self._resolve_package(target)
            if _package_openapi_setting(pkg) is False:
                raise ValueError(
                    "Package %r is not exposed via openapi" % target)
            tables = self.table_names(target)
        elif explicit_table:
            assert isinstance(target, str)
            self._resolve_targets(target)
            tables = [target]
        elif isinstance(target, (list, tuple, set)):
            tables = self._resolve_targets(target)
        else:
            tables = self._all_exposed_tables()

        out = {}
        for fullname in tables:
            pkg_name = fullname.split('.', 1)[0]
            pkg = self.db.packages[pkg_name]
            if _package_openapi_setting(pkg) is False:
                if explicit_table:
                    raise ValueError(
                        "Table %r belongs to package %r which is not "
                        "exposed via openapi" % (fullname, pkg_name))
                continue
            tbl = self.db.table(fullname)
            tbl_setting = _table_openapi_setting(tbl)
            if tbl_setting is False:
                if explicit_table:
                    raise ValueError(
                        "Table %r is not exposed via openapi" % fullname)
                continue
            out[fullname] = self._build_openapi_table_schema(
                fullname, readonly=readonly)
        return out

    def _all_exposed_tables(self):
        out = []
        for pkg_name, pkg in self.db.packages.items():
            if _package_openapi_setting(pkg) is False:
                continue
            for tname, tobj in pkg.tables.items():
                if _table_openapi_setting(tobj) is False:
                    continue
                out.append('%s.%s' % (pkg_name, tname))
        return sorted(out)

    def _build_openapi_table_schema(self, fullname, readonly=True):
        columns = self._collect_columns(fullname)
        properties = {}
        required = []
        for colname, info in columns.items():
            col_setting = _column_openapi_setting(
                {'openapi': info.get('openapi')})
            if col_setting is False:
                continue
            is_real = info['kind'] == 'real'
            is_system = info['system']
            is_pkey = info['pkey']
            # Writable iff: real, not system, not declared 'R', not pkey
            writable = (is_real
                        and not is_system
                        and col_setting != 'R'
                        and not is_pkey)
            if not readonly and not writable:
                continue
            prop = {'type': info['openapi_type']}
            if info['openapi_format']:
                prop['format'] = info['openapi_format']
            if info['nullable']:
                prop['nullable'] = True
            if info['name_long']:
                prop['description'] = info['name_long']
            if not writable:
                prop['readOnly'] = True
            if info['size']:
                size = info['size']
                if info['openapi_type'] == 'string' and ',' not in str(size):
                    try:
                        prop['maxLength'] = int(size)
                    except (TypeError, ValueError):
                        pass
            if info.get('fkey'):
                prop['x-fkey'] = info['fkey']
            if info.get('relation_path'):
                prop['x-relation-path'] = info['relation_path']
            properties[colname] = prop
            if writable and not info['nullable'] and info['default'] is None:
                required.append(colname)
        schema = {
            'type': 'object',
            'title': fullname,
            'properties': properties,
        }
        if required:
            schema['required'] = required
        return schema

    # ------------------------------------------------------------------
    # run_query
    # ------------------------------------------------------------------

    def run_query(self, table,
                  columns=None,
                  where=None,
                  sqlparams=None,
                  order_by=None,
                  group_by=None,
                  having=None,
                  distinct=False,
                  limit=None,
                  offset=None,
                  subtable=None,
                  storename=None,
                  partition_kwargs=None,
                  language=None,
                  opt_kwargs=None,
                  *,
                  max_rows=None):
        """Execute a JSON-safe read selection.

        See module docstring for the parameter contract. ``max_rows``
        defaults to the engine-level value configured at construction;
        pass an explicit value to override.
        """
        if opt_kwargs:
            unknown = set(opt_kwargs) - _RUN_QUERY_OPT_KEYS
            if unknown:
                raise ValueError(
                    'Unknown opt_kwargs keys: %s. Allowed: %s'
                    % (sorted(unknown), sorted(_RUN_QUERY_OPT_KEYS)))

        cap = max_rows if max_rows is not None else self.max_rows

        requested_limit = limit
        effective_limit = limit
        if cap is not None:
            effective_limit = (min(int(limit), int(cap))
                               if limit is not None else int(cap))

        query_kwargs = dict(
            columns=columns,
            where=where,
            sqlparams=sqlparams,
            order_by=order_by,
            group_by=group_by,
            having=having,
            distinct=distinct,
            limit=effective_limit,
            offset=offset,
            subtable=subtable,
            addPkeyColumn=False,
        )
        if storename is not None:
            query_kwargs['_storename'] = storename
        if opt_kwargs:
            query_kwargs.update(opt_kwargs)
        query_kwargs = {k: v for k, v in query_kwargs.items()
                        if v is not None}
        query_kwargs.setdefault('addPkeyColumn', False)

        env_inject = {}
        if partition_kwargs:
            for field, value in partition_kwargs.items():
                if value is None:
                    continue
                if isinstance(value, (list, tuple, set)):
                    env_inject['allowed_%s' % field] = list(value)
                else:
                    env_inject['current_%s' % field] = value
        if language is not None:
            env_inject['current_language'] = language

        error = None
        rows = []
        rowcount = 0
        t0 = time.monotonic()
        try:
            with self.db.tempEnv(**env_inject):
                selection = (self.db.table(table)
                             .query(**query_kwargs).selection())
                rowcount = len(selection)
                rows = selection.output(mode='dictlist')
        except Exception as exc:
            error = '%s: %s' % (type(exc).__name__, exc)
        elapsed_ms = (time.monotonic() - t0) * 1000.0

        truncated = (
            cap is not None
            and requested_limit is not None
            and requested_limit > int(cap)
        ) or (cap is not None and rowcount >= int(cap))

        return {
            'rows': rows,
            'rowcount': rowcount,
            'truncated': truncated,
            'elapsed_ms': elapsed_ms,
            'error': error,
        }
