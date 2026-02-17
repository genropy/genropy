#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_compiler : SQL query compiler
# Copyright (c) : 2004 - 2026 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU.
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""SQL query compiler for the GenroPy framework.

This module contains all the classes responsible for transforming
high-level, declarative query descriptions (column paths, relation paths,
WHERE expressions with macros) into executable SQL text:

Classes:
    CompiledColumn: Lightweight value object holding the result of compiling
        a single column reference.
    AliasManager: Manages SQL table alias allocation, lookup, and tracking
        of exploding (many-side) joins.
    ColumnCompiler: Resolves any column reference (simple, relation path,
        formula, many-side) into its SQL expression.
    SqlCompiledQuery: Value object that holds all the compiled parts of a
        SQL SELECT statement (columns, joins, where, group_by, etc.).
    SqlCompiledSubQuery: Subquery variant with identity support for merge.
    SqlQueryCompiler: Stateful compiler that orchestrates column resolution,
        macro expansion, and SQL assembly.
"""

import copy
import re
from collections import OrderedDict

from gnr.core.gnrdict import dictExtract
from gnr.core.gnrlang import uniquify
from gnr.core.gnrdate import decodeDatePeriod
from gnr.core import gnrstring
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsql_exceptions import GnrSqlException, GnrSqlMissingField, GnrSqlMissingColumn

# ---------------------------------------------------------------------------
#  Regex patterns (defined once, shared by all classes)
# ---------------------------------------------------------------------------

COLFINDER = re.compile(r"(\W|^)\$(\w+)")
RELFINDER = re.compile(r"([^A-Za-z0-9_]|^)(\@(\w[\w.@:]+))")
COLRELFINDER = re.compile(r"([@$]\w+(?:\.\w+)*)")
THISFINDER = re.compile(r'#THIS\.([\w\.@]+)')
ENVFINDER = re.compile(r"#ENV\(([^,)]+)(,[^),]+)?\)")
PREFFINDER = re.compile(r"#PREF\(([^,)]+)(,[^),]+)?\)")
BETWEENFINDER = re.compile(
    r"#BETWEEN\s*\(\s*((?:\$|@|\:)?[\w\.\@]+)\s*,"
    r"\s*((?:\$|@|\:)?[\w\.\@]+)\s*,"
    r"\s*((?:\$|@|\:)?[\w\.\@]+)\s*\)\s*",
    re.MULTILINE,
)
PERIODFINDER = re.compile(r"#PERIOD\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*,\s*:?(\w+)\)")
BAGEXPFINDER = re.compile(r"#BAG\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*\)(\s*AS\s*(\w*))?")
BAGCOLSEXPFINDER = re.compile(r"#BAGCOLS\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*\)(\s*AS\s*(\w*))?")

# ---------------------------------------------------------------------------
#  Aggregate mappings (used by ColumnCompiler for many-side subqueries)
# ---------------------------------------------------------------------------

# Mapping dtype -> default SQL aggregate function
DTYPE_AGGREGATOR = {
    'R': 'SUM', 'L': 'SUM', 'N': 'SUM',
    'B': 'BOOL_AND',
}

# Mapping Python aggregator name -> SQL function
AGGREGATOR_SQL = {
    'SUM': 'SUM', 'MAX': 'MAX', 'MIN': 'MIN', 'AVG': 'AVG',
    'CNT': 'COUNT',
    'AND': 'BOOL_AND', 'OR': 'BOOL_OR',
}


# ===================================================================
#  CompiledColumn
# ===================================================================

class CompiledColumn(object):
    """Value object holding the result of compiling a single column.

    Attributes:
        sql_expression (str): The SQL expression for this column
            (e.g. ``'t0.name'``, ``'t2.code'``, ``'( SELECT ... )'``).
        is_many (bool): ``True`` if this column traverses a many-side
            relation that was converted to a subquery.
        dtype (str | None): The data type code of the column.
        aggregator (str | None): The SQL aggregator used (if many).
        field_key (str | None): The key in ``relationDict``.
    """

    __slots__ = ('sql_expression', 'is_many', 'dtype', 'aggregator', 'field_key')

    def __init__(self, sql_expression, is_many=False, dtype=None,
                 aggregator=None, field_key=None):
        self.sql_expression = sql_expression
        self.is_many = is_many
        self.dtype = dtype
        self.aggregator = aggregator
        self.field_key = field_key


# ===================================================================
#  SubqueryEntry
# ===================================================================

class SubqueryEntry(object):
    """Registry entry for a deferred subquery."""

    __slots__ = ('compiled', 'origin', 'placeholder_key', 'identity_hash', 'sq_name')

    def __init__(self, compiled, origin, placeholder_key,
                 identity_hash=None, sq_name=None):
        self.compiled = compiled
        self.origin = origin
        self.placeholder_key = placeholder_key
        self.identity_hash = identity_hash
        self.sq_name = sq_name


# ===================================================================
#  AliasManager
# ===================================================================

class AliasManager(object):
    """Manages SQL table alias allocation and lookup.

    Encapsulates the ``aliases`` dictionary (mapping path-keys to SQL
    aliases like ``t0``, ``t1``, ...), the alias prefix, and tracking
    of exploding (many-side) tables.

    Args:
        prefix (str): Prefix for alias generation (default ``'t'``).
        main_table_sqlfullname (str): The fully-qualified SQL name of
            the main table, used to seed the initial alias.
    """

    def __init__(self, prefix, main_table_sqlfullname):
        self._prefix = prefix
        self._aliases = {main_table_sqlfullname: self._code(0)}
        self._exploding_tables = []

    @property
    def aliases(self):
        """The aliases dictionary (path-key -> SQL alias)."""
        return self._aliases

    @property
    def exploding_tables(self):
        """List of path-keys whose joins cause row explosion."""
        return self._exploding_tables

    @property
    def main_alias(self):
        """The SQL alias for the main table (e.g. ``'t0'``)."""
        return self._code(0)

    def _code(self, n):
        return '%s%i' % (self._prefix, n)

    def code(self, n):
        """Return the alias string for index *n*."""
        return self._code(n)

    def next_alias(self):
        """Allocate and return the next available alias."""
        return self._code(len(self._aliases))

    def lookup(self, path_key):
        """Look up an existing alias by path-key, or ``None``."""
        return self._aliases.get(path_key)

    def register(self, path_key):
        """Register a new path-key and return its fresh alias."""
        alias = self.next_alias()
        self._aliases[path_key] = alias
        return alias

    def mark_exploding(self, path_key):
        """Mark a path-key as causing row explosion."""
        self._exploding_tables.append(path_key)

    def is_exploding(self, path_key):
        """Check if a path-key was marked as exploding."""
        return path_key in self._exploding_tables

    def reset(self, main_table_sqlfullname):
        """Reset for a new compilation pass."""
        self._aliases.clear()
        self._aliases[main_table_sqlfullname] = self._code(0)
        self._exploding_tables.clear()


# ===================================================================
#  ColumnCompiler
# ===================================================================

class ColumnCompiler(object):
    """Resolves any column reference into its SQL expression.

    Handles all column types: physical columns, relation paths (one-side
    and many-side), formula columns (sql_formula, select, exists),
    relation_path aliases, and py_method virtual columns.

    When a many-side relation is encountered, the column is automatically
    converted to an inline correlated subquery with the appropriate
    aggregate function, avoiding row explosion.

    The ``ColumnCompiler`` is created by ``SqlQueryCompiler`` and shares
    mutable state with it via ``self.compiler``.

    Args:
        compiler: The parent ``SqlQueryCompiler`` instance.
    """

    def __init__(self, compiler):
        self.compiler = compiler

    def _is_lazy_enabled(self):
        """Check if lazy subquery rendering is enabled."""
        query = self.compiler.query
        if query and getattr(query, 'enable_lazy_subquery', None) is not None:
            return gnrstring.boolean(query.enable_lazy_subquery)
        return self.compiler._enable_lazy_subquery

    # --- Per-column state (set during compile, consumed by helpers) ---

    _curr = None
    _alias = None
    _curr_tblobj = None

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def compile(self, fieldpath, curr=None, basealias=None, parent=None):
        """Resolve *fieldpath* into a ``CompiledColumn``.

        This is the main entry point — equivalent to the former
        ``SqlQueryCompiler.getFieldAlias``.

        Args:
            fieldpath: Dot-separated field path.  Simple columns use
                the bare name; related columns use ``@relation.column``.
            curr: Current node in the relation tree.
            basealias: SQL alias of the table corresponding to *curr*.
            parent: Dot-separated prefix of already-traversed segments.

        Returns:
            CompiledColumn: The compiled result.
        """
        pathlist = fieldpath.split('.')
        fld = pathlist.pop()
        curr = curr or self.compiler.relations
        newpath = []
        basealias = basealias or self.compiler.alias_manager.main_alias

        # Reset many-side signal before traversal
        self._many_joiner_info = None

        # If the path has relation segments, resolve JOINs first
        if pathlist:
            alias, curr = self._find_relation_alias(
                list(pathlist), curr, basealias, newpath, parent=parent)
        else:
            alias = basealias

        # Many-side relation detected: convert to inline subquery
        if self._many_joiner_info is not None:
            info = self._many_joiner_info
            self._many_joiner_info = None
            # Build the full field path inside the target table:
            # remaining_path (extra relation hops) + fld (the final column)
            remaining = info['remaining_path']
            remaining.append(fld)
            target_field = '.'.join(remaining)
            expr = self._compile_many_as_subquery(
                info['joiner'], target_field,
                info['basealias'], info['curr'], info['rel_segment'])
            # Set per-column state for backward compat
            self._curr = curr
            self._alias = alias
            self._curr_tblobj = self.compiler.db.table(curr.tbl_name, pkg=curr.pkg_name)
            return CompiledColumn(expr, is_many=True)

        curr_tblobj = self.compiler.db.table(curr.tbl_name, pkg=curr.pkg_name)
        self._curr = curr
        self._alias = alias
        self._curr_tblobj = curr_tblobj

        # Branch: field is NOT a physical column — check virtual columns
        if fld not in curr.keys():
            fldalias = curr_tblobj.model.getVirtualColumn(fld, sqlparams=self.compiler.sqlparams)
            if fldalias is None:
                raise GnrSqlMissingField(
                    'Missing field %s in table %s.%s (requested field %s)' % (
                        fld, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))

            elif fldalias.relation_path and not fldalias.composed_of:
                return self.compile(fldalias.relation_path, curr=curr,
                                    basealias=alias, parent='.'.join(pathlist))

            elif fldalias.sql_formula or fldalias.select or fldalias.exists:
                expr = self._handle_formula(fldalias, fld, alias, curr, curr_tblobj)
                return CompiledColumn(expr)

            elif fldalias.py_method:
                self.compiler.cpl.pyColumns.append(
                    (fld, getattr(fldalias.table.dbtable, fldalias.py_method, None)))
                return CompiledColumn('NULL')

            else:
                raise GnrSqlMissingColumn(
                    'Invalid column %s in table %s.%s (requested field %s)' % (
                        fld, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))

        # Field is a physical column
        expr = '%s.%s' % (
            self.compiler.db.adapter.asTranslator(alias),
            curr_tblobj.column(fld).adapted_sqlname)
        return CompiledColumn(expr)

    # ------------------------------------------------------------------
    #  Formula columns
    # ------------------------------------------------------------------

    def _handle_formula(self, fldalias, fld, alias, curr, curr_tblobj):
        """Compile a formula/virtual column into a SQL expression.

        Handles sql_formula, select (subquery), and exists.
        Supports subquery-as-join conversion when enabled.
        """
        attr = copy.deepcopy(dict(fldalias.attributes))
        as_join = self._should_convert_to_join(fldalias)
        if as_join:
            select_attr = attr.get('select') or attr.get('select_dflt')
            if isinstance(select_attr, dict) and 'limit' in select_attr:
                as_join = False
            elif as_join and isinstance(select_attr, dict):
                as_join = not self._where_references_formula_column(
                    select_attr.get('where', ''), curr_tblobj)
        formula_kw = dictExtract(attr, 'var_')
        sql_formula = fldalias.sql_formula
        if sql_formula is True:
            sql_formula = getattr(curr_tblobj, 'sql_formula_%s' % fld)(attr)
        if sql_formula:
            sql_formula = self._preprocess_formula(
                fldalias, alias, curr, sql_formula, formula_kw)
        multi_select, sql_formula = self._preprocess_subqueryes(
            attr, as_join, alias,
            formula_column_name=fld, sql_formula=sql_formula)
        if not sql_formula and multi_select:
            if as_join:
                parts = []
                for sq_name, sq_pars in multi_select.items():
                    m = re.search(r'AS (c_\d+)', sq_pars.get('columns', ''))
                    col_ref = m.group(1) if m else 'c_0'
                    col_expr = '%s.%s' % (sq_name, col_ref)
                    if 'COUNT(' in sq_pars.get('columns', '').upper():
                        col_expr = 'COALESCE(%s, 0)' % col_expr
                    parts.append(col_expr)
                sql_formula = " || ' ' || ".join(parts)
            else:
                sql_formula = " || ' ' || ".join('#%s' % k for k in multi_select)
        select_dict = dict(multi_select) if multi_select else {}
        if select_dict:
            for sq_name, sq_select in list(select_dict.items()):
                if isinstance(sq_select, str):
                    sq_select = getattr(self.compiler.tblobj.dbtable, 'subquery_%s' % sq_select)()
                sq_pars = dict(sq_select)
                compiled = self._compiled_sub_query(alias, sq_pars, sq_name=sq_name)
                if as_join:
                    h = compiled._identity_hash
                    if h in self.compiler.sq_compiled_dct:
                        existing, existing_name, col_counter = self.compiler.sq_compiled_dct[h]
                        new_col = self._extract_aggregate_column(compiled.columns)
                        new_alias = 'c_%i' % col_counter
                        existing.columns += ', %s AS %s' % (new_col, new_alias)
                        self.compiler.sq_compiled_dct[h] = (existing, existing_name, col_counter + 1)
                        sql_formula = sql_formula.replace(
                            '%s.c_0' % sq_name,
                            '%s.%s' % (existing_name, new_alias))
                    else:
                        self.compiler.sq_compiled_dct[h] = (compiled, sq_name, 1)
                else:
                    if self._is_lazy_enabled():
                        ph_key = self.compiler._next_placeholder_key()
                        self.compiler.cpl.subquery_registry.append(SubqueryEntry(
                            compiled=compiled, origin='formula_inline',
                            placeholder_key=ph_key, identity_hash=compiled._identity_hash,
                            sq_name=sq_name))
                        sql_formula = re.sub(r'#%s\b' % sq_name, ph_key, sql_formula)
                    else:
                        sql_formula = re.sub(
                            r'#%s\b' % sq_name, compiled.get_sqltext(self.compiler.db), sql_formula)
        return f'( {sql_formula} )'

    def _should_convert_to_join(self, fldalias):
        sq_as_join = fldalias.attributes.get('sq_as_join')
        if sq_as_join is not None:
            return gnrstring.boolean(sq_as_join)
        query = self.compiler.query
        if query and getattr(query, 'enable_sq_join', None) is not None:
            return gnrstring.boolean(query.enable_sq_join)
        return gnrstring.boolean(
            getattr(self.compiler.db, 'extra_kw', {}).get('subquery_as_join', False))

    def _where_references_formula_column(self, where_str, tblobj):
        if not where_str:
            return False
        for m in THISFINDER.finditer(where_str):
            ref_field = m.group(1).split('.')[0]
            ref_col = tblobj.column(ref_field)
            if ref_col is not None and (getattr(ref_col, 'sql_formula', None)
                                        or getattr(ref_col, 'select', None)):
                return True
        return False

    def _preprocess_subqueryes(self, attr, as_join=False, alias=None,
                               formula_column_name=None, sql_formula=None):
        if 'exists' in attr:
            exists_sq = attr.pop('exists')
            exists_sq['exists'] = True
            attr['select_dflt'] = exists_sq
        elif 'select' in attr:
            attr['select_dflt'] = attr.pop('select')
        sq_dict = dictExtract(attr, 'select_')
        if not as_join or not sq_dict:
            return sq_dict, sql_formula
        sq_dict, sql_formula = self._condense_subqueries(sq_dict, sql_formula)
        if formula_column_name:
            prefixed = {}
            for sq_name, sq_pars in sq_dict.items():
                subquery_name = '%s_%s' % (formula_column_name, sq_name)
                if sql_formula:
                    sql_formula = sql_formula.replace(
                        '%s.' % sq_name, '%s.' % subquery_name)
                prefixed[subquery_name] = sq_pars
            sq_dict = prefixed
        for sq_name, sq_pars in sq_dict.items():
            sq_where = sq_pars.get('where', '')
            m = re.match(r'(@[\w.]+|\$\w+)\s*=\s*#THIS\.(\w+)(.*)', sq_where, re.DOTALL)
            if m:
                fk_field = m.group(1)
                joiner = '%s=#THIS.%s' % (fk_field, m.group(2))
                residual = m.group(3).strip()
                if residual.upper().startswith('AND '):
                    residual = residual[4:].strip()
                sq_pars['where'] = residual or None
                has_limit = 'limit' in sq_pars
                existing_group_by = sq_pars.get('group_by')
                if existing_group_by:
                    sq_pars['group_by'] = '%s,%s' % (fk_field, existing_group_by)
                elif not has_limit:
                    sq_pars['group_by'] = fk_field
                sq_pars['columns'] = '%s AS joiner, %s' % (fk_field, sq_pars['columns'])
                joiner = THISFINDER.sub(self.compiler.expandThis, joiner)
                sq_pars['joiner'] = joiner
        return sq_dict, sql_formula

    def _condense_subqueries(self, sq_dict, sql_formula):
        groups = {}
        for sq_name, sq_pars in sq_dict.items():
            key = (sq_pars['table'], sq_pars.get('where'))
            groups.setdefault(key, []).append(sq_name)
        col_counter = 0
        remap = {}
        for key, names in groups.items():
            if len(names) == 1:
                sq_name = names[0]
                sq_pars = sq_dict[sq_name]
                col_alias = 'c_%i' % col_counter
                sq_pars['columns'] = '%s AS %s' % (sq_pars['columns'], col_alias)
                col_counter += 1
                continue
            master = names[0]
            master_pars = sq_dict[master]
            merged_cols = []
            for name in names:
                pars = sq_dict[name]
                col_alias = 'c_%i' % col_counter
                merged_cols.append('%s AS %s' % (pars['columns'], col_alias))
                if name != master:
                    remap[name] = (master, col_alias)
                col_counter += 1
            master_pars['columns'] = ', '.join(merged_cols)
            for name in names[1:]:
                del sq_dict[name]
        if sql_formula:
            for absorbed, (master, col_alias) in remap.items():
                sql_formula = re.sub(
                    r'#%s\b' % absorbed, '%s.%s' % (master, col_alias), sql_formula)
            for sq_name, sq_pars in sq_dict.items():
                m = re.search(r'AS (c_\d+)', sq_pars['columns'])
                if m:
                    first_col = m.group(1)
                    sql_formula = re.sub(
                        r'#%s\b' % sq_name, '%s.%s' % (sq_name, first_col), sql_formula)
        return sq_dict, sql_formula

    def _preprocess_formula(self, fldalias, alias, curr, sql_formula, formula_kw):
        sql_formula = sql_formula.replace('#default', '#dflt')
        def resolveField(m):
            return m.group(1) + self.compile(
                m.group(2), curr=curr, basealias=alias).sql_expression
        sql_formula = RELFINDER.sub(resolveField, sql_formula)
        sql_formula = COLFINDER.sub(resolveField, sql_formula)
        sql_formula = THISFINDER.sub(self.compiler.expandThis, sql_formula)
        sql_formula = ENVFINDER.sub(self.compiler.expandEnv, sql_formula)
        sql_formula = PREFFINDER.sub(self.compiler.expandPref, sql_formula)
        if formula_kw:
            prefix = f'{id(fldalias)}_{self.compiler._currColKey}'
            for k, v in formula_kw.items():
                mangled_k = f'{prefix}_{k}'
                self.compiler.sqlparams[mangled_k] = v
                sql_formula = re.sub(
                    r"(:)(%s)(\W|$)" % k,
                    lambda m, mk=mangled_k: f'{m.group(1)}{mk}{m.group(3)}',
                    sql_formula)
        return sql_formula

    def _extract_aggregate_column(self, columns_str):
        m = re.search(r'AS\s+joiner\s*,\s*', columns_str)
        if m:
            col_part = columns_str[m.end():]
            col_part = re.sub(r'\s+AS\s+c_\d+\s*$', '', col_part.strip())
            return col_part
        return columns_str

    def _compiled_sub_query(self, alias, sq_pars, sq_name=None):
        joiner = sq_pars.pop('joiner', None)
        tpl = sq_pars.pop('tpl', None)
        cast = sq_pars.pop('cast', None)
        is_exists = sq_pars.pop('exists', False)
        sq_limit = sq_pars.pop('limit', None) if joiner else None
        if not tpl:
            if joiner:
                on_clause = re.sub(
                    r'@[\w.]+|\$\w+', '%s.joiner' % sq_name, joiner)
                tpl = ' LEFT JOIN (%%s) AS %s ON (%s) ' % (sq_name, on_clause)
            elif is_exists:
                tpl = ' EXISTS( %s ) '
            elif cast:
                tpl = ' CAST( ( %s ) AS ' + cast + ') '
            else:
                tpl = ' ( %s ) '
        sq_table = sq_pars.pop('table')
        sq_where = sq_pars.pop('where')
        sq_pars.setdefault('ignorePartition', True)
        sq_pars.setdefault('excludeDraft', False)
        sq_pars.setdefault('excludeLogicalDeleted', False)
        sq_pars.setdefault('subtable', '*')
        aliasPrefix = '%s_t' % alias
        if sq_where:
            sq_where = THISFINDER.sub(self.compiler.expandThis, sq_where)
        mangler_prefix = self.compiler.query._next_mangler_key('sq')
        q = self.compiler.db.table(sq_table).query(
            where=sq_where,
            aliasPrefix=aliasPrefix,
            addPkeyColumn=False,
            ignoreTableOrderBy=True,
            mangler=mangler_prefix,
            **sq_pars
        )
        compiled = q.compileQuery(compiled_class=SqlCompiledSubQuery)
        compiled.tpl = tpl
        resolved_where = compiled.where or ''
        for k, v in q.sqlparams.items():
            resolved_where = resolved_where.replace(':%s' % k, str(v))
        compiled._identity_hash = hash(
            (compiled.maintable, resolved_where, compiled.group_by or ''))
        self.compiler.sqlparams.update(q.sqlparams)
        return compiled

    # ------------------------------------------------------------------
    #  Relation traversal
    # ------------------------------------------------------------------

    def _find_relation_alias(self, pathlist, curr, basealias, newpath, parent=None):
        """Recursively resolve a relation path into the JOIN alias.

        When a many-side relation is encountered, instead of creating a
        JOIN (which would explode rows), the method stores the joiner
        info in ``_many_joiner_info`` and returns immediately.  The
        caller (``compile()``) picks this up and delegates to
        ``_compile_many_as_subquery``.
        """
        p = pathlist.pop(0)
        currNode = curr.getNode(p)
        if not currNode:
            raise GnrSqlMissingField(f"Relation {p} not found")
        joiner = currNode.attr['joiner']

        if joiner is None:
            tblalias = self.compiler.db.table(
                curr.tbl_name, pkg=curr.pkg_name).model.table_aliases[p]
            if tblalias is None:
                raise GnrSqlMissingField(
                    'Missing field %s in table %s.%s (requested field %s)' % (
                        p, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))
            else:
                pathlist = tblalias.relation_path.split('.') + pathlist
        else:
            manyrelation = (joiner['mode'] != 'O'
                            and not joiner.get('one_one', False))
            if manyrelation:
                # Many-side relation: signal to compile() that a subquery
                # is needed.  Any remaining pathlist segments become part
                # of the deep field path inside the subquery.
                self._many_joiner_info = dict(
                    joiner=joiner,
                    basealias=basealias,
                    curr=curr,
                    rel_segment=p,
                    remaining_path=list(pathlist),
                )
                pathlist.clear()
                return basealias, curr

            alias, newpath = self._get_relation_alias(
                currNode, newpath, basealias, parent=parent)
            basealias = alias
            curr = curr[p]

        if pathlist:
            alias, curr = self._find_relation_alias(
                pathlist, curr, basealias, newpath,
                parent=f"{parent}.{p}" if parent else p)
        return alias, curr

    def _get_relation_alias(self, relNode, path, basealias, parent=None):
        """Build or reuse the JOIN clause for a single relation hop."""
        joiner = relNode.attr['joiner']
        ref = joiner['many_relation'].split('.', 1)[-1]
        newpath = path + [ref]
        pw = tuple(newpath + [basealias])

        am = self.compiler.alias_manager

        # Fast path: join already exists
        existing = am.lookup(pw)
        if existing is not None:
            if am.is_exploding(pw):
                if self.compiler._currColKey not in self.compiler.cpl.explodingColumns:
                    self.compiler.cpl.explodingColumns.append(self.compiler._currColKey)
            return existing, newpath

        # New join
        alias = am.register(pw)
        manyrelation = False

        if joiner['mode'] == 'O':
            target_tbl = self.compiler.dbmodel.table(joiner['one_relation'])
            target_column = joiner['one_relation'].split('.')[-1]
            from_tbl = self.compiler.dbmodel.table(joiner['many_relation'])
            from_column = joiner['many_relation'].split('.')[-1]
        else:
            target_tbl = self.compiler.dbmodel.table(joiner['many_relation'])
            target_column = joiner['many_relation'].split('.')[-1]
            from_tbl = self.compiler.dbmodel.table(joiner['one_relation'])
            from_column = joiner['one_relation'].split('.')[-1]
            manyrelation = not joiner.get('one_one', False)

        ignore_tenant = joiner.get('ignore_tenant')
        target_sqlfullname = target_tbl._get_sqlfullname(ignore_tenant=ignore_tenant)

        # Build the ON condition
        joinerList = []
        target_sqlcolumn = None
        from_sqlcolumn = (from_tbl.sqlnamemapper[from_column]
                          if not joiner.get('virtual') else None)

        if from_sqlcolumn:
            joinerList.append(
                (from_sqlcolumn, target_tbl.sqlnamemapper[target_column]))
        elif from_tbl.column(from_column).attributes.get('composed_of'):
            from_columns = from_tbl.column(from_column).composed_of
            target_columns = target_tbl.column(target_column).composed_of
            if not target_columns:
                raise GnrSqlException(
                    'Relation with multikey works only with compositeColumns')
            target_sqlcolumns = [
                target_tbl.sqlnamemapper[tc]
                for tc in target_columns.split(',')]
            joinerList = list(zip(
                [from_tbl.sqlnamemapper[fc]
                 for fc in from_columns.split(',')],
                target_sqlcolumns))
        else:
            target_sqlcolumn = target_tbl.sqlnamemapper[target_column]

        joindict = dict()
        adaptedAlias = self.compiler.db.adapter.adaptSqlName(alias)
        adaptedBaseAlias = self.compiler.db.adapter.adaptSqlName(basealias)

        if 'join_on' in joiner:
            joiner['cnd'] = joiner['join_on']
        if joiner.get('cnd'):
            cnd = joiner.get('cnd')
            cnd = BETWEENFINDER.sub(self.compiler.expandBetween, cnd)
        elif joiner.get('between'):
            value_field, low_field, high_field = joiner.get('between').split(';')
            cnd = f"""
                ({low_field} IS NULL AND {high_field} IS NOT NULL AND {value_field}<{high_field}) OR
                ({low_field} IS NOT NULL AND {high_field} IS NULL AND {value_field}>={low_field}) OR
                ({low_field} IS NOT NULL AND {high_field} IS NOT NULL AND
                    {value_field} >= {low_field} AND {value_field} < {high_field}) OR
                ({low_field} IS NULL AND {high_field} IS NULL)
            """
            joiner['cnd'] = cnd
        elif joiner.get('case_insensitive', False) == 'Y':
            cnd = (f'lower({adaptedAlias}.{target_sqlcolumn})'
                   f' = lower({adaptedBaseAlias}.{from_sqlcolumn})')
        elif joinerList:
            cnd = ' AND '.join([
                f'({adaptedBaseAlias}.{fc})={adaptedAlias}.{tc}'
                for fc, tc in joinerList])
        elif joiner.get('virtual'):
            cnd = f'(${from_column})={adaptedAlias}.{target_sqlcolumn}'

        if parent:
            cnd = COLRELFINDER.sub(
                lambda g: f'{parent}.' + g.group(0).replace('$', ''), cnd)
        cnd = self.compiler.updateFieldDict(cnd, reldict=joindict)

        if joindict:
            for f in joindict.values():
                self.compile(f)
            self.compiler.cpl.relationDict.update(joindict)

        if self.compiler.joinConditions:
            from_fld, target_fld = self.compiler._tablesFromRelation(joiner)
            extracnd, one_one = self.compiler.getJoinCondition(
                target_fld, from_fld, alias, relation=relNode.label)
            if extracnd:
                extracnd = self.compiler.embedFieldPars(extracnd)
                extracnd = self.compiler.updateFieldDict(extracnd)
                cnd = '(%s AND %s)' % (cnd, extracnd)
                if one_one:
                    manyrelation = False

        self.compiler.cpl.joins.append(
            f'LEFT JOIN {target_sqlfullname} AS '
            f'{self.compiler.db.adapter.adaptSqlName(alias)} ON ({cnd})')

        if manyrelation:
            if self.compiler._currColKey not in self.compiler.cpl.explodingColumns:
                self.compiler.cpl.explodingColumns.append(self.compiler._currColKey)
            am.mark_exploding(pw)
            self.compiler._explodingRows = True
        return alias, newpath

    def get_join_condition(self, target_fld, from_fld, alias, relation=None):
        """Look up extra ON-condition for a join.

        Delegates to ``SqlQueryCompiler.getJoinCondition``.
        """
        return self.compiler.getJoinCondition(
            target_fld, from_fld, alias, relation=relation)

    # ------------------------------------------------------------------
    #  Many-side relation → inline subquery
    # ------------------------------------------------------------------

    def _compile_many_as_subquery(self, joiner, target_field, basealias,
                                  curr, rel_segment):
        """Convert a many-side relation column to an inline subquery.

        Instead of creating a JOIN that explodes rows, this method builds
        a correlated subquery with the appropriate aggregate function.

        Args:
            joiner: The joiner dict from the relation node.
            target_field: The field path inside the target table.
                Can be a simple field (``'amount'``) or a deep path
                through further relations (``'@product_id.name'``).
            basealias: SQL alias of the current (one-side) table.
            curr: Current relation tree node.
            rel_segment: The relation segment name.

        Returns:
            str: SQL expression like ``'( SELECT SUM(...) FROM ... WHERE ... )'``.
        """
        many_rel = joiner['many_relation']
        one_rel = joiner['one_relation']
        mpkg, mtbl, mfld = many_rel.split('.')
        _opkg, _otbl, ofld = one_rel.split('.')
        target_table = '%s.%s' % (mpkg, mtbl)

        # Resolve dtype/aggregator of the final column.
        dtype, aggregator = self._resolve_target_column_info(
            target_table, target_field)

        sql_agg = self._get_sql_aggregator(dtype, aggregator)

        # The column reference inside the subquery
        col_ref = self._field_ref(target_field)

        if sql_agg == 'STRING_AGG':
            col_expr = "STRING_AGG(DISTINCT %s::TEXT, ',')" % col_ref
        elif sql_agg == 'COUNT':
            col_expr = 'COUNT(%s)' % col_ref
        else:
            col_expr = '%s(%s)' % (sql_agg, col_ref)

        sq_pars = dict(
            table=target_table,
            columns=col_expr,
            where='$%s=#THIS.%s' % (mfld, ofld),
        )

        compiled = self._compiled_sub_query(basealias, sq_pars)
        if self._is_lazy_enabled():
            ph_key = self.compiler._next_placeholder_key()
            self.compiler.cpl.subquery_registry.append(SubqueryEntry(
                compiled=compiled, origin='many_side',
                placeholder_key=ph_key, identity_hash=compiled._identity_hash))
            return ph_key
        return compiled.get_sqltext(self.compiler.db)

    def _resolve_target_column_info(self, target_table, target_field):
        """Walk a (possibly deep) field path to find dtype and aggregator.

        Returns:
            tuple: ``(dtype, aggregator)`` of the leaf column.
        """
        parts = target_field.replace('@', '').split('.')
        tblobj = self.compiler.db.table(target_table)
        # Walk relation hops (all but the last segment)
        for seg in parts[:-1]:
            col = tblobj.model.column(seg)
            if col is None:
                return 'T', None
            rel = col.relatedColumn()
            if rel is None:
                return 'T', None
            tblobj = rel.table.dbtable
        # Final segment: the actual column
        leaf = parts[-1]
        col = tblobj.model.column(leaf)
        if col is not None:
            attrs = col.attributes
            return attrs.get('dtype', 'T'), attrs.get('aggregator')
        # Could be a virtual column
        vc = tblobj.model.getVirtualColumn(leaf)
        if vc is not None:
            return vc.attributes.get('dtype', 'T'), vc.attributes.get('aggregator')
        return 'T', None

    @staticmethod
    def _field_ref(target_field):
        """Convert a target_field path to the $/@-prefixed column reference
        used inside a subquery's ``columns`` expression.

        Simple fields → ``$amount``
        Relation paths → ``@product_id.name`` (already has @ prefix)
        """
        if target_field.startswith('@'):
            return target_field
        return '$%s' % target_field

    def _get_sql_aggregator(self, dtype, aggregator=None):
        """Determine the SQL aggregate function from dtype and aggregator.

        Mirrors the logic of ``SqlTable.fieldAggregate``.
        """
        if aggregator and aggregator in AGGREGATOR_SQL:
            return AGGREGATOR_SQL[aggregator]
        if dtype in ('R', 'L', 'N'):
            return AGGREGATOR_SQL.get(aggregator, 'SUM')
        if dtype == 'B':
            return 'BOOL_AND' if (not aggregator or aggregator == 'AND') else 'BOOL_OR'
        return 'STRING_AGG'


# ===================================================================
#  SqlCompiledQuery
# ===================================================================

class SqlCompiledQuery(object):
    """Value object holding every component of a compiled SQL SELECT statement.

    Instances of this class are produced by ``SqlQueryCompiler.compiledQuery``
    or ``SqlQueryCompiler.compiledRecordQuery`` and consumed by the database
    adapter to generate the final SQL text via ``get_sqltext``.
    """

    def __init__(self, maintable, relationDict=None, maintable_as=None):
        self.maintable = maintable
        self.relationDict = relationDict or {}
        self.aliasDict = {}
        self.resultmap = Bag()
        self.distinct = ''
        self.columns = ''
        self.joins = []
        self.additional_joins = []
        self.sq_joins = []
        self.where = None
        self.group_by = None
        self.having = None
        self.order_by = None
        self.limit = None
        self.offset = None
        self.for_update = None
        self.explodingColumns = []
        self.evaluateBagColumns = []
        self.aggregateDict = {}
        self.pyColumns = []
        self.maintable_as = maintable_as
        self.tpl = None
        self.subquery_registry = []
        self.ctes = {}

    def get_sqltext(self, db):
        """Render the final SQL text using the database adapter."""
        kwargs = {}
        for k in (
        'maintable', 'distinct', 'columns', 'joins', 'where', 'group_by', 'having', 'order_by', 'limit', 'offset',
        'for_update'):
            kwargs[k] = getattr(self, k)
        result = db.adapter.compileSql(maintable_as=self.maintable_as, **kwargs)
        if self.subquery_registry:
            result = self._resolve_placeholders(result, db)
        if self.tpl:
            result = self.tpl % result
        return result

    def _resolve_placeholders(self, sql_text, db):
        """Replace placeholder keys with rendered SQL from the registry."""
        for entry in self.subquery_registry:
            sql_text = sql_text.replace(entry.placeholder_key,
                                        entry.compiled.get_sqltext(db))
        return sql_text


class SqlCompiledSubQuery(SqlCompiledQuery):
    """A compiled subquery with identity support for merge."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._identity_hash = None

    def __eq__(self, other):
        if not isinstance(other, SqlCompiledSubQuery):
            return NotImplemented
        return self._identity_hash is not None and self._identity_hash == other._identity_hash

    def __hash__(self):
        if self._identity_hash is not None:
            return self._identity_hash
        return id(self)


# ===================================================================
#  SqlQueryCompiler
# ===================================================================

class SqlQueryCompiler(object):
    """Stateful compiler that transforms declarative query specs into SQL.

    Orchestrates column resolution (via ``ColumnCompiler``), alias
    management (via ``AliasManager``), macro expansion, and SQL assembly.
    """

    def __init__(self, tblobj, joinConditions=None, sqlContextName=None, sqlparams=None, locale=None, aliasPrefix=None, mangler=None, query_kw=None, mainquery_kw=None, query=None):
        self.tblobj = tblobj
        self.db = tblobj.db
        self.query = query
        self.dbmodel = tblobj.db.model
        if tblobj.db.reuse_relation_tree:
            self.relations = tblobj.relations
        else:
            self.relations = tblobj.newRelationResolver(cacheTime=-1)
        self.sqlparams = sqlparams
        self.joinConditions = joinConditions
        self.sqlContextName = sqlContextName
        self.cpl = None
        self._currColKey = None
        self.aliasPrefix = aliasPrefix or 't'
        self.locale = locale
        self.mangler = mangler
        self.query_kw = query_kw or {}
        self.mainquery_kw = mainquery_kw or {}
        self.subquery_kw = {}
        self.sq_compiled_dct = {}
        self.alias_manager = AliasManager(self.aliasPrefix, self.tblobj.sqlfullname)
        self.macro_expander = self.db.adapter.macroExpander(self)
        self._sq_placeholder_counter = 0
        self._enable_lazy_subquery = bool(
            self.query_kw.get('enable_lazy_subquery')
            or (self.query and getattr(self.query, 'enable_lazy_subquery', None))
            or getattr(self.db, 'extra_kw', {}).get('lazy_subquery', False))

    def _next_placeholder_key(self):
        """Generate a unique placeholder key for a deferred subquery."""
        key = '__sq_%d__' % self._sq_placeholder_counter
        self._sq_placeholder_counter += 1
        return key

    def aliasCode(self, n):
        """Return the table alias for index *n*."""
        return self.alias_manager.code(n)

    @property
    def aliases(self):
        """Backward-compatible access to the aliases dictionary."""
        return self.alias_manager.aliases

    def mangle(self, sql_text):
        """Prefix bind-parameter names with the mangler string."""
        if not self.mangler:
            return sql_text
        def replace_param(m):
            param_name = m.group(2)
            if param_name.startswith('env_'):
                return m.group(0)
            if param_name in self.sqlparams:
                return '%s%s_%s%s' % (m.group(1), self.mangler, param_name, m.group(3))
            return m.group(0)
        return re.sub(r"(:)(\w+)(\W|$)", replace_param, sql_text)

    def mangleParams(self):
        """Rename entries in ``sqlparams`` with the mangler prefix."""
        if not self.mangler:
            return
        for k, v in list(self.sqlparams.items()):
            if not k.startswith('env_'):
                mangled_key = '%s_%s' % (self.mangler, k)
                mangled_value = self.query_kw.get(k, self.mainquery_kw.get(k))
                self.subquery_kw[mangled_key] = mangled_value
                self.sqlparams[mangled_key] = v

    def init(self, lazy=None, eager=None):
        """Reset per-compilation state before a new compilation pass."""
        self._explodingRows = False
        self.lazy = lazy or []
        self.eager = eager or []
        self.alias_manager = AliasManager(
            self.aliasPrefix, self.tblobj.sqlfullname)
        self.fieldlist = []
        self.column_compiler = ColumnCompiler(self)

    # Backward-compatible property: _explodingTables delegates to alias_manager
    @property
    def _explodingTables(self):
        return self.alias_manager.exploding_tables

    def expandThis(self, m):
        fld = m.group(1)
        return self.getFieldAlias(fld, curr=self._curr, basealias=self._alias)

    def expandPref(self, m):
        prefpath = m.group(1)
        dflt = m.group(2)[1:] if m.group(2) else None
        return str(self._curr_tblobj.pkg.getPreference(prefpath, dflt))

    def expandEnv(self, m):
        what = m.group(1)
        par2 = None
        if m.group(2):
            par2 = m.group(2)[1:]
        if what in self.db.currentEnv:
            return "'%s'" % gnrstring.toText(self.db.currentEnv[what])
        elif par2 and par2 in self.db.currentEnv:
            return "'%s'" % gnrstring.toText(self.db.currentEnv[par2])
        if par2:
            env_tblobj = self.db.table(par2)
        else:
            env_tblobj = self._curr_tblobj
        handler = getattr(env_tblobj, 'env_%s' % what, None)
        if handler:
            return handler()
        else:
            return 'Not found %s' % what

    def getFieldAlias(self, fieldpath, curr=None, basealias=None, parent=None):
        """Resolve a field path into its SQL expression.

        Delegates to ``ColumnCompiler.compile()`` and syncs per-column
        state back for backward compatibility.
        """
        compiled_col = self.column_compiler.compile(
            fieldpath, curr=curr, basealias=basealias, parent=parent)
        # Sync per-column state back for backward compatibility
        self._curr = self.column_compiler._curr
        self._alias = self.column_compiler._alias
        self._curr_tblobj = self.column_compiler._curr_tblobj
        return compiled_col.sql_expression

    def getJoinCondition(self, target_fld, from_fld, alias, relation=None):
        """Look up an extra ON-condition for a join from ``joinConditions``."""
        if not self.joinConditions:
            return None, None
        jc_keys = []
        if relation:
            jc_keys.append(relation)
        if target_fld == '*' and from_fld == '*':
            jc_keys.append('*')
        else:
            jc_keys.append('%s_%s' % (
                target_fld.replace('.', '_'), from_fld.replace('.', '_')))
        for jc_key in jc_keys:
            jc = self.joinConditions.get(jc_key)
            if jc:
                condition = jc['condition'].replace('$tbl', alias)
                if 'params' in jc:
                    self.sqlparams.update(jc['params'])
                return condition, jc.get('one_one')
        return None, None

    def updateFieldDict(self, teststring, reldict=None):
        """Scan a SQL fragment for ``$column`` and ``@relation.column`` references."""
        if reldict is None: reldict = self.cpl.relationDict
        for col in COLFINDER.finditer(teststring):
            colname = col.group(2)
            if not colname in reldict:
                reldict[colname] = colname
        for col in RELFINDER.finditer(teststring):
            colname = col.group(2)
            asname = self.db.colToAs(colname)
            reldict[asname] = colname
            teststring = teststring.replace(colname, '$%s' % asname,1)
        return teststring

    def expandMultipleColumns(self, flt, bagFields):
        """Expand a glob-style column specification into explicit column paths."""
        subfield_name = None
        if flt and flt in self.tblobj.virtual_columns:
            subfield_name = flt
            vc = self.tblobj.virtual_columns[flt]
            flt = vc.sql_formula
        if flt.startswith('@'):
            path = gnrstring.split(flt)
            if path[-1].startswith('@'):
                flt = ''
            else:
                flt = path.pop(-1)
            flt = flt.strip('*')
            path = '.'.join(path)
            relflds = self.relations[path]
            rowkey = None
            if flt.startswith('('):
                flt = flt[1:-1]
                flt = flt.split(',')
                rowkey = flt[0].replace('.','_').replace('@','_')
                r = []
                flatten_path = path.replace('.','_').replace('@','_')
                for f in flt:
                    fldpath = '%s.%s' % (path, f)
                    r.append(fldpath)
                    flatten_fldpath=fldpath.replace('.','_').replace('@','_')
                    subfield_name = subfield_name or flatten_path
                    self.cpl.aggregateDict[flatten_fldpath] = [subfield_name,f, '%s_%s' %(flatten_path,rowkey)]
                return r
            else:
                return ['%s.%s' % (path, k) for k in list(relflds.keys()) if k.startswith(flt) and not k.startswith('@')]
        else:
            return self.tblobj.starColumns(bagFields)

    def embedFieldPars(self, sql):
        """Inline-replace bind parameters whose values are field references."""
        for k,v in list(self.sqlparams.items()):
            if isinstance(v, bytes):
                v = v.decode()
            if isinstance(v, str):
                doreplace=False
                if v.startswith('@'):
                    doreplace = v.split('.')[0] in self.tblobj.relations
                elif v.startswith('$'):
                    doreplace = v[1:] in self.tblobj.columns.keys() + self.tblobj.virtual_columns.keys()
                if doreplace:
                    sql = re.sub(r'(:%s)(\W|$)' % k, lambda m: '%s%s' %(v,m.group(2)), sql)
        return sql

    def compiledQuery(self, columns='', where='', order_by='',
                      distinct='', limit='', offset='',
                      group_by='', having='', for_update=False,
                      relationDict=None,
                      bagFields=False,
                      storename=None,subtable=None,
                      count=False, excludeLogicalDeleted=True,excludeDraft=True,
                      ignorePartition=False,ignoreTableOrderBy=False,
                      addPkeyColumn=True,
                      compiled_class=None):
        """Compile a SELECT query for a multi-row selection."""
        compiled_class = compiled_class or SqlCompiledQuery
        self.cpl = compiled_class(self.tblobj.sqlfullname,relationDict=relationDict,maintable_as=self.aliasCode(0))
        distinct = distinct or ''

        aggregate = bool(distinct or group_by)

        if group_by == '*':
            group_by = None

        if not ignoreTableOrderBy and not aggregate:
            order_by = order_by or self.tblobj.attributes.get('order_by')
        self.init()
        if ('pkey' not in self.cpl.relationDict) and self.tblobj.pkey:
            self.cpl.relationDict['pkey'] = self.tblobj.pkey

        # normalize the columns string
        columns = columns or ''
        columns = columns.replace('  ', ' ')
        columns = columns.replace('\n', '')
        columns = columns.replace(' as ', ' AS ')
        columns = columns.replace(' ,', ',')
        if storename and (storename=='*' or ',' in storename):
            columns = "%s, '_STORENAME_' AS _dbstore_" %columns
        if columns and not columns.endswith(','):
            columns = columns + ','
        # expand * and *filters
        if '*' in columns:
            col_list = [col for col in gnrstring.split(columns, ',') if col]
            new_col_list = []
            for col in col_list:
                col = col.strip()
                if col.startswith('*'):
                    new_col_list = new_col_list + self.expandMultipleColumns(col[1:], bagFields)
                else:
                    new_col_list.append(col)
            columns = ','.join(new_col_list)


        if count:
            order_by = ''
            if group_by:
                columns = group_by
            elif distinct:
                pass
            else:
                columns = 'count(*) AS "gnr_row_count"'
        elif addPkeyColumn and self.tblobj.pkey and not aggregate:
            columns = columns + ',\n' + f'${self.tblobj.pkey} AS {self.db.adapter.asTranslator("pkey")}'
            columns = columns.lstrip(',')
        else:
            columns = columns.strip('\n').strip(',')

        currentEnv = self.db.currentEnv
        context_subtables = currentEnv.get('context_subtables',Bag()).getItem(self.tblobj.fullname)
        if not subtable and context_subtables:
            subtable = context_subtables
        subtable = subtable or self.tblobj.attributes.get('default_subtable')
        if where:
            where = BETWEENFINDER.sub(self.expandBetween, where)
            where = PERIODFINDER.sub(self.expandPeriod, where)
            where = self.macro_expander.replace(where,'TSQUERY')

        env_conditions = dictExtract(currentEnv,'env_%s_condition_' %self.tblobj.fullname.replace('.','_'))
        wherelist = [where]
        if env_conditions:
            for condition in list(env_conditions.values()):
                wherelist.append('( %s )' %condition)
        wherelist.append(self.tblobj.dbtable.getPartitionCondition(ignorePartition=ignorePartition))
        if subtable and subtable != '*':
            subtable_list = re.split(r'[&|]', subtable)
            st_condition = subtable.replace('&',' AND ').replace('|',' OR ').replace('!',' NOT ')
            for s in subtable_list:
                if s.startswith('!'):
                    s = s[1:]
                cond = self.tblobj.dbtable.subtable(s.strip()).getCondition(sqlparams=self.sqlparams)
                st_condition = st_condition.replace(s,cond)
            wherelist.append(st_condition)
        logicalDeletionField = self.tblobj.logicalDeletionField
        if logicalDeletionField:
            if excludeLogicalDeleted is True:
                wherelist.append('${} IS NULL'.format(logicalDeletionField))
            elif excludeLogicalDeleted=='mark' and not (aggregate or count):
                columns = '{columns},${logicalDeletionField} AS "_isdeleted"'.format(columns=columns, logicalDeletionField=logicalDeletionField)

        if excludeDraft is True:
            draftField = self.tblobj.draftField
            if draftField:
                wherelist.append('${} IS NOT TRUE'.format(draftField))
        where = ' AND '.join(['({where_chunk})'.format(where_chunk=w) for w in wherelist if w])
        columns = self.updateFieldDict(columns)
        where = self.embedFieldPars(where)
        where = self.updateFieldDict(where or '')
        order_by = self.updateFieldDict(order_by or '')
        group_by = self.updateFieldDict(group_by or '')
        having = self.updateFieldDict(having or '')
        columns = BAGEXPFINDER.sub(self.expandBag,columns)
        columns = BAGCOLSEXPFINDER.sub(self.expandBagcols,columns)

        col_list = uniquify([col for col in gnrstring.split(columns, ',') if col])
        col_dict = OrderedDict()
        for col in col_list:
            col = col.strip()
            if re.search("(sum|count) *?\\(", col, re.I):
                aggregate = True
            if not ' AS ' in col:
                if col.startswith('$') and col[1:].replace('_', '').isalnum():
                    as_ = col[1:]
                else:
                    as_ = self.db.colToAs(col)
                as_ = self.db.adapter.asTranslator(as_)
                col = '%s AS %s' % (col, as_)
            else:
                colbody, as_ = col.split(' AS ', 1)
                as_ = self.db.adapter.asTranslator(as_.strip())
                self.cpl.aliasDict[as_] = colbody.strip()
            col_dict[as_] = col
        as_col_values = col_dict.values()
        columns = ',\n'.join(as_col_values)
        colPars = {}
        for key, value in list(self.cpl.relationDict.items()):
            self._currColKey = key
            colPars[key] = self.getFieldAlias(value)
        missingKeys = list(set(self.cpl.relationDict.keys()).difference(set(colPars.keys())))
        while missingKeys:
            for key in missingKeys:
                self._currColKey = key
                colPars[key] = self.getFieldAlias(self.cpl.relationDict[key])
            missingKeys = list(set(self.cpl.relationDict.keys()).difference(set(colPars.keys())))


        columns = gnrstring.templateReplace(columns, colPars, safeMode=True)

        where = gnrstring.templateReplace(where, colPars)
        if self.joinConditions:
            extracnd, one_one = self.getJoinCondition('*', '*', self.aliasCode(0))
            if extracnd:
                if where:
                    where = ' ( %s ) AND ( %s ) ' % (where, extracnd)
                else:
                    where = extracnd
        order_by = gnrstring.templateReplace(order_by, colPars)
        having = gnrstring.templateReplace(having, colPars)
        group_by = gnrstring.templateReplace(group_by, colPars)
        self.cpl.joins = [gnrstring.templateReplace(j, colPars) for j in self.cpl.joins+self.cpl.additional_joins]
        if self.cpl.sq_joins:
            self.cpl.joins.extend(self.cpl.sq_joins)
        for _h, (sq_compiled, _sq_name, _col_counter) in self.sq_compiled_dct.items():
            if self._enable_lazy_subquery:
                ph_key = self._next_placeholder_key()
                self.cpl.subquery_registry.append(SubqueryEntry(
                    compiled=sq_compiled, origin='formula_join',
                    placeholder_key=ph_key, identity_hash=_h, sq_name=_sq_name))
                self.cpl.joins.append(ph_key)
            else:
                self.cpl.joins.append(sq_compiled.get_sqltext(self.db))
        # --- DISTINCT handling ---
        if distinct:
            distinct = 'DISTINCT '
        elif distinct is None or distinct == '':
            if self._explodingRows:
                if not aggregate:
                    distinct = 'DISTINCT '
                    if order_by:
                        xorderby= gnrstring.split((('%s '%order_by.lower()).replace(' ascending ','').replace(' descending ','').replace(' asc ','').replace(' desc','')),',')
                        lowercol=columns.lower()
                        for i,xrd in enumerate(xorderby):
                            if not xrd.strip() in lowercol:
                                columns = '%s, \n%s AS __ord_col_%s' % (columns, xrd,i)
                    if count:
                        columns = '%s.%s' % (self.aliasCode(0),self.tblobj.pkey)

        self.cpl.distinct = distinct
        self.cpl.columns = self.mangle(self.macro_expander.replace(columns,'TSRANK,TSHEADLINE'))
        self.cpl.where = self.mangle(where)
        self.cpl.group_by = self.mangle(group_by)
        self.cpl.having = self.mangle(having)
        self.cpl.order_by = self.mangle(self.macro_expander.replace(order_by,'TSRANK'))
        self.cpl.joins = [self.mangle(j) for j in self.cpl.joins]
        self.cpl.limit = limit
        self.cpl.offset = offset
        self.cpl.for_update = for_update
        self.mangleParams()
        return self.cpl

    def compiledRecordQuery(self, lazy=None, eager=None, where=None,
                            bagFields=True, for_update=False, relationDict=None, virtual_columns=None):
        """Compile a SELECT query for a single-record fetch."""
        self.cpl = SqlCompiledQuery(self.tblobj.sqlfullname, relationDict=relationDict)
        if 'pkey' not in self.cpl.relationDict and self.tblobj.pkey:
            self.cpl.relationDict['pkey'] = self.tblobj.pkey
        self.init(lazy=lazy, eager=eager)
        colPars = {}
        joindict = {}
        virtual_columns = virtual_columns or []
        if isinstance(virtual_columns, str):
            virtual_columns = gnrstring.splitAndStrip(virtual_columns, ',')

        for fieldname, value, attrs in self.relations.digest('#k,#v,#a'):
            xattrs = {k:v for k, v in attrs.items() if not k in ['tag', 'comment', 'table', 'pkg']}
            if attrs.get('dtype') == 'X' and not bagFields:
                continue
            joiner = attrs.get('joiner')
            if joiner:
                if joiner.get('virtual') and joiner['mode'] == 'O':
                    virtual_columns.append(fieldname[1:])
                    for relation_condition in ('cnd', 'range'):
                        rel_cnd = joiner.get(relation_condition)
                        if rel_cnd:
                            self.updateFieldDict(rel_cnd, reldict=joindict)
                xattrs['_relmode'] = self._getRelationMode(attrs['joiner'])
            else:
                sqlname = attrs.get('sqlname') or fieldname
                self.fieldlist.append( '%s.%s AS %s' % (self.db.adapter.adaptSqlName(self.aliasCode(0)),self.db.adapter.adaptSqlName(sqlname),self.db.adapter.asTranslator('%s_%s'%(self.aliasCode(0),fieldname))))
                xattrs['as'] = '%s_%s' %(self.aliasCode(0),fieldname)
            self.cpl.resultmap.setItem(fieldname, None, xattrs)

        self._handle_virtual_columns(virtual_columns)
        self.cpl.where = self._recordWhere(where=where)
        self.cpl.columns = ',\n       '.join(self.fieldlist)
        self.cpl.for_update = for_update

        for key, value in list(joindict.items()):
            colPars[key] = self.getFieldAlias(value)
        self.cpl.joins = [gnrstring.templateReplace(j, colPars) for j in self.cpl.joins]

        return self.cpl


    def _getRelationMode(self, joiner):
        """Determine the dynamic-item mode for a relation."""
        if joiner['mode'] == 'O':
            return 'DynItemOne'
        isOneOne = joiner.get('one_one')
        if not isOneOne and self.joinConditions:
            from_fld, target_fld = self._tablesFromRelation(joiner)
            extracnd, isOneOne = self.getJoinCondition(target_fld, from_fld, '%s0' %self.aliasPrefix)
        return 'DynItemOneOne' if isOneOne else 'DynItemMany'


    def _handle_virtual_columns(self, virtual_columns):
        """Resolve virtual columns and add them to the field list."""
        if virtual_columns is False:
            return
        if isinstance(virtual_columns, str):
            virtual_columns = gnrstring.splitAndStrip(virtual_columns, ',')
        virtual_columns = (virtual_columns or []) + list(self.tblobj.static_virtual_columns.keys())
        if not virtual_columns:
            return
        virtual_columns = uniquify([v[1:] if v.startswith('$') else v for v in virtual_columns])
        tbl_virtual_columns = self.tblobj.virtual_columns
        for col_name in virtual_columns:
            column = tbl_virtual_columns[col_name]
            if column is None:
                continue
            column_attributes = self.tblobj.virtualColumnAttributes(col_name)
            self._currColKey = col_name
            field = self.getFieldAlias(column.name)

            xattrs = dict([(k, v) for k, v in list(column_attributes.items()) if not k in ['tag', 'comment', 'table', 'pkg']])

            if column_attributes['tag'] == 'virtual_column':
                as_name = '%s_%s' % (self.aliasCode(0), column.name)
                path_name = column.name
            else:
                pass
            xattrs['as'] = as_name
            self.fieldlist.append('%s AS %s' % (field, as_name))
            self.cpl.resultmap.setItem(path_name, None, xattrs)

    def expandBag(self, m):
        """Regex callback: expand a ``#BAG($field) AS alias`` macro."""
        fld = m.group(1)
        asfld = m.group(3)
        self.cpl.evaluateBagColumns.append(((asfld or fld).replace('$',''),False))
        return fld if not asfld else '{} AS {}'.format(fld, asfld)

    def expandBagcols(self, m):
        """Regex callback: expand a ``#BAGCOLS($field) AS alias`` macro."""
        fld = m.group(1)
        asfld = m.group(3)
        self.cpl.evaluateBagColumns.append(((asfld or fld).replace('$',''),True))
        return fld if not asfld else '{} AS {}'.format(fld, asfld)

    def expandBetween(self, m):
        """Regex callback: expand ``#BETWEEN(value, low, high)`` into SQL."""
        value_field = m.group(1)
        low_field = m.group(2)
        high_field = m.group(3)

        result = f"""
                (({low_field} IS NULL AND {high_field} IS NOT NULL AND {value_field}<={high_field}) OR
                ({low_field} IS NOT NULL AND {high_field} IS NULL AND {value_field}>={low_field}) OR
                ({low_field} IS NOT NULL AND {high_field} IS NOT NULL AND
                    {value_field} >= {low_field} AND {value_field} <= {high_field}) OR
                ({low_field} IS NULL AND {high_field} IS NULL))
            """
        return result

    def expandPeriod(self, m):
        """Regex callback: expand ``#PERIOD($field, param)`` into a date range."""
        fld = m.group(1)
        period_param = m.group(2)
        date_from, date_to = decodeDatePeriod(self.sqlparams[period_param],
                                              workdate=self.db.workdate,
                                              returnDate=True, locale=self.db.locale)
        from_param = '%s_from' % period_param
        to_param = '%s_to' % period_param

        if date_from is None and date_to is None:
            return ' true'
        elif date_from and date_to:
            if date_from == date_to:
                self.sqlparams[from_param] = date_from
                return ' %s = :%s ' % (fld, from_param)

            self.sqlparams[from_param] = date_from
            self.sqlparams[to_param] = date_to
            result = ' (%s BETWEEN :%s AND :%s) ' % (fld, from_param, to_param)
            return result

        elif date_from:
            self.sqlparams[from_param] = date_from
            return ' %s >= :%s ' % (fld, from_param)
        else:
            self.sqlparams[to_param] = date_to
            return ' %s <= :%s ' % (fld, to_param)

    def _recordWhere(self, where=None):
        """Compile a WHERE clause for a single-record query."""
        if where:
            self.updateFieldDict(where)
            colPars = {}
            for key, value in list(self.cpl.relationDict.items()):
                colPars[key] = self.getFieldAlias(value)
            where = gnrstring.templateReplace(where, colPars)
        return where

    def _tablesFromRelation(self, attrs):
        """Extract the from/target field identifiers from a joiner dict."""
        if attrs['mode'] == 'O':
            target_fld = attrs['one_relation']
            from_fld = attrs['many_relation']
        else:
            target_fld = attrs['many_relation']
            from_fld = attrs['one_relation']
        return from_fld, target_fld
