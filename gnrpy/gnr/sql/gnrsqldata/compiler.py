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

This module contains the two main classes responsible for transforming
high-level, declarative query descriptions (column paths, relation paths,
WHERE expressions with macros) into executable SQL text:

Classes:
    SqlCompiledQuery: Value object that holds all the compiled parts of a
        SQL SELECT statement (columns, joins, where, group_by, etc.).
    SqlQueryCompiler: Stateful compiler that walks the relation tree of a
        table, resolves ``$column`` and ``@relation.column`` references,
        builds JOIN clauses, expands macros (#BETWEEN, #PERIOD, #ENV, ...),
        and produces a fully populated ``SqlCompiledQuery``.

The compiler is used internally by ``SqlQuery`` (selections) and
``SqlRecord`` (single-record fetch) and should not be instantiated
directly by application code.

Module-level constants:
    COLFINDER, RELFINDER, COLRELFINDER: Regular expressions for detecting
        ``$column`` and ``@relation.column`` references in SQL fragments.
    BETWEENFINDER, PERIODFINDER: Regular expressions for the ``#BETWEEN``
        and ``#PERIOD`` macro syntax.
    BAGEXPFINDER, BAGCOLSEXPFINDER: Regular expressions for the ``#BAG``
        and ``#BAGCOLS`` macro syntax.
    ENVFINDER, PREFFINDER, THISFINDER: Regular expressions for the
        ``#ENV``, ``#PREF``, and ``#THIS`` macro syntax.
"""

import re
from collections import OrderedDict

from gnr.core.gnrdict import dictExtract
from gnr.core.gnrlang import uniquify
from gnr.core.gnrdate import decodeDatePeriod
from gnr.core import gnrstring
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsql_exceptions import GnrSqlException, GnrSqlMissingField, GnrSqlMissingColumn

COLFINDER = re.compile(r"(\W|^)\$(\w+)")
RELFINDER = re.compile(r"([^A-Za-z0-9_]|^)(\@(\w[\w.@:]+))")
COLRELFINDER = re.compile(r"([@$]\w+(?:\.\w+)*)")

BETWEENFINDER = re.compile(r"#BETWEEN\s*\(\s*((?:\$|@|\:)?[\w\.\@]+)\s*,\s*((?:\$|@|\:)?[\w\.\@]+)\s*,\s*((?:\$|@|\:)?[\w\.\@]+)\s*\)\s*",re.MULTILINE)
PERIODFINDER = re.compile(r"#PERIOD\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*,\s*:?(\w+)\)")

BAGEXPFINDER = re.compile(r"#BAG\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*\)(\s*AS\s*(\w*))?")
BAGCOLSEXPFINDER = re.compile(r"#BAGCOLS\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*\)(\s*AS\s*(\w*))?")

ENVFINDER = re.compile(r"#ENV\(([^,)]+)(,[^),]+)?\)")
PREFFINDER = re.compile(r"#PREF\(([^,)]+)(,[^),]+)?\)")
THISFINDER = re.compile(r'#THIS\.([\w\.@]+)')

class SqlCompiledQuery(object):
    """Value object holding every component of a compiled SQL SELECT statement.

    Instances of this class are produced by ``SqlQueryCompiler.compiledQuery``
    or ``SqlQueryCompiler.compiledRecordQuery`` and consumed by the database
    adapter to generate the final SQL text via ``get_sqltext``.

    Attributes:
        maintable (str): Fully-qualified SQL name of the main table
            (e.g. ``"myschema"."mytable"``).
        relationDict (dict): Mapping of symbolic column names to their
            relation paths.  Populated during compilation.
        aliasDict (dict): Mapping of output AS-names to the original SQL
            expression when an explicit ``AS`` was provided in the column
            specification.
        resultmap (Bag): Metadata bag describing the structure of the
            result set (used by ``SqlRecord``).
        distinct (str): Either ``'DISTINCT '`` or ``''``.
        columns (str): Comma-separated SQL column expressions ready for
            the SELECT clause.
        joins (list[str]): List of ``LEFT JOIN ... ON (...)`` clauses.
        additional_joins (list[str]): Extra joins appended after the
            main ones (rarely used).
        where (str | None): The compiled WHERE clause.
        group_by (str | None): The compiled GROUP BY clause.
        having (str | None): The compiled HAVING clause.
        order_by (str | None): The compiled ORDER BY clause.
        limit (int | str | None): Row limit for the query.
        offset (int | str | None): Row offset for the query.
        for_update (bool | None): Whether to append ``FOR UPDATE``.
        explodingColumns (list[str]): Column keys whose relation traversal
            causes row multiplication (many-side joins).
        evaluateBagColumns (list[tuple]): Columns that need post-query
            Bag evaluation (from ``#BAG`` / ``#BAGCOLS`` macros).
        aggregateDict (dict): Metadata for columns that will be
            aggregated by ``SqlSelection._aggregateRows``.
        pyColumns (list[tuple]): Columns computed in Python via
            ``py_method`` virtual columns.
        maintable_as (str | None): Alias for the main table
            (e.g. ``'t0'``).
    """

    def __init__(self, maintable, relationDict=None, maintable_as=None):
        """Initialise a new compiled query container.

        Args:
            maintable: Fully-qualified SQL name of the main table.
            relationDict: Optional pre-populated relation dictionary.
                Defaults to an empty dict.
            maintable_as: Optional alias for the main table in the
                generated SQL (e.g. ``'t0'``).
        """
        self.maintable = maintable
        self.relationDict = relationDict or {}
        self.aliasDict = {}
        self.resultmap = Bag()
        self.distinct = ''
        self.columns = ''
        self.joins = []
        self.additional_joins = []
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

    def get_sqltext(self, db):
        """Render the final SQL text using the database adapter.

        Collects all compiled attributes and delegates to
        ``db.adapter.compileSql`` which assembles them into a
        dialect-specific SQL string.

        Args:
            db: A :class:`GnrSqlDb <gnr.sql.gnrsql.GnrSqlDb>` instance
                providing the adapter for the target RDBMS.

        Returns:
            str: The complete SQL SELECT statement.
        """
        kwargs = {}
        for k in (
        'maintable', 'distinct', 'columns', 'joins', 'where', 'group_by', 'having', 'order_by', 'limit', 'offset',
        'for_update'):
            kwargs[k] = getattr(self, k)
        return db.adapter.compileSql(maintable_as=self.maintable_as,**kwargs)



class SqlQueryCompiler(object):
    """Stateful compiler that transforms declarative query specs into SQL.

    ``SqlQueryCompiler`` is used internally by ``SqlQuery`` (for selections)
    and ``SqlRecord`` (for single-record fetches).  It walks the relation
    tree of a table, resolves ``$column`` / ``@relation.column`` references,
    builds LEFT JOIN clauses, expands macros (``#BETWEEN``, ``#PERIOD``,
    ``#ENV``, ``#PREF``, ``#THIS``, ``#BAG``, ``#BAGCOLS``), and fills a
    ``SqlCompiledQuery`` instance with all the SQL fragments.

    Typical lifecycle::

        compiler = SqlQueryCompiler(tblobj, ...)
        cpl = compiler.compiledQuery(columns=..., where=..., ...)
        sql = cpl.get_sqltext(db)

    Attributes:
        tblobj: The ``SqlTable`` model object for the main table.
        db: The ``GnrSqlDb`` database instance.
        dbmodel: The ``GnrSqlDbModel`` model instance.
        relations: Relation resolver for the main table (may be shared
            or freshly created depending on ``reuse_relation_tree``).
        sqlparams (dict): Bind-parameter dictionary for the query.
        joinConditions (dict | None): Extra join conditions keyed by
            ``target_from`` or relation name.
        sqlContextName (str | None): Context name for subsequent
            related selections.
        cpl (SqlCompiledQuery | None): The compiled query being built
            (set during compilation).
        aliasPrefix (str): Prefix for table aliases (default ``'t'``).
        locale (str | None): Current locale for date/text formatting.
        macro_expander: Adapter-specific macro expander instance.
    """

    def __init__(self, tblobj, joinConditions=None, sqlContextName=None, sqlparams=None, locale=None, aliasPrefix=None):
        """Initialise the compiler for a given table.

        Args:
            tblobj: The ``SqlTable`` model object for the main table.
                Obtain it via ``db.table('pkg.tablename')``.
            joinConditions: Optional dict of extra conditions to apply
                when joining related tables.  See
                ``SqlQuery.setJoinCondition``.
            sqlContextName: Optional context name propagated to related
                selections built from the query result.
            sqlparams: Optional dict of bind parameters referenced in
                WHERE / HAVING clauses and macros.
            locale: Optional locale string (e.g. ``'it'``, ``'en_us'``)
                used for date decoding and text formatting.
            aliasPrefix: Optional prefix for generated table aliases.
                Defaults to ``'t'`` producing ``t0``, ``t1``, ...
        """
        self.tblobj = tblobj
        self.db = tblobj.db
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
        self.macro_expander = self.db.adapter.macroExpander(self)

    def aliasCode(self, n):
        """Return the table alias for index *n*.

        Args:
            n: Zero-based integer index.

        Returns:
            str: Alias string like ``'t0'``, ``'t1'``, etc.
        """
        return '%s%i' %(self.aliasPrefix,n)


    def init(self, lazy=None, eager=None):
        """Reset per-compilation state before a new compilation pass.

        Must be called at the beginning of ``compiledQuery`` or
        ``compiledRecordQuery`` to ensure no residual state from a
        previous compilation leaks into the new one.

        Args:
            lazy: Optional list of relation paths to resolve lazily
                (used by ``SqlRecord``).
            eager: Optional list of relation paths to resolve eagerly
                (used by ``SqlRecord``).
        """
        self._explodingRows = False
        self._explodingTables = []
        self.lazy = lazy or []
        self.eager = eager or []
        self.aliases = {self.tblobj.sqlfullname: self.aliasCode(0)}
        self.fieldlist = []

    def getFieldAlias(self, fieldpath, curr=None, basealias=None, parent=None):
        """Resolve a field path into its SQL ``alias.column`` representation.

        Translates GenroPy field paths such as ``@relname.@rel2name.colname``
        into their SQL equivalent (e.g. ``t4.colname``), creating LEFT JOIN
        clauses as a side effect when a relation is traversed for the first
        time.

        This method is recursive: virtual columns whose definition is itself
        a relation path trigger a new call to ``getFieldAlias``.

        Note:
            This method has nothing to do with the SQL ``AS`` operator nor
            with the name of output columns.

        Args:
            fieldpath: A dot-separated field path.  Simple columns use
                the bare name (e.g. ``'colname'``); related columns use
                ``@relation.colname`` notation.
            curr: Current node in the relation resolver tree.  Defaults
                to ``self.relations`` (the root).
            basealias: SQL alias of the table corresponding to *curr*.
                Defaults to ``self.aliasCode(0)`` (the main table).
            parent: Dot-separated prefix tracking the relation path
                already traversed (used to qualify sub-query references).

        Returns:
            str: A SQL expression for the field, e.g. ``'t0.mycolumn'``
            or ``'( sql_formula_expression )'`` for virtual columns.

        Raises:
            GnrSqlMissingField: If the field or relation cannot be found
                in the model.
            GnrSqlMissingColumn: If a virtual column has no valid
                definition (no sql_formula, select, exists, relation_path
                or py_method).
        """

        def expandThis(m):
            """Regex callback: resolve ``#THIS.field`` references relative to current alias."""
            fld = m.group(1)
            return self.getFieldAlias(fld, curr=curr, basealias=alias)

        def expandPref(m):
            """Regex callback: resolve ``#PREF(path, default)`` to a literal preference value."""
            prefpath = m.group(1)
            dflt = m.group(2)[1:] if m.group(2) else None
            return str(curr_tblobj.pkg.getPreference(prefpath, dflt))

        def expandEnv(m):
            """Regex callback: resolve ``#ENV(name, fallback)`` to a quoted env value.

            Resolution order:
                1. Direct lookup of *name* in ``db.currentEnv``.
                2. Direct lookup of *fallback* (par2) in ``db.currentEnv``.
                3. Call ``env_<name>`` method on the table object.
                4. Return a literal ``'Not found <name>'`` string.
            """
            what = m.group(1)
            par2 = None
            if m.group(2):
                par2 = m.group(2)[1:]
            # Branch 1: direct env lookup
            if what in self.db.currentEnv:
                return "'%s'" % gnrstring.toText(self.db.currentEnv[what])
            # Branch 2: fallback env lookup
            elif par2 and par2 in self.db.currentEnv:
                return "'%s'" % gnrstring.toText(self.db.currentEnv[par2])
            # Branch 3: delegate to table's env_<name> handler
            if par2:
                env_tblobj = self.db.table(par2)
            else:
                env_tblobj = curr_tblobj
            handler = getattr(env_tblobj, 'env_%s' % what, None)
            if handler:
                return handler()
            else:
                return 'Not found %s' % what
        # --- Split the dotted field path into relation segments + final field ---
        pathlist = fieldpath.split('.')
        fld = pathlist.pop()
        curr = curr or self.relations
        newpath = []
        basealias = basealias or self.aliasCode(0)

        # --- If the path has relation segments, resolve JOINs first ---
        if pathlist:
            alias, curr = self._findRelationAlias(list(pathlist), curr, basealias, newpath, parent=parent)
        else:
            alias = basealias
        curr_tblobj = self.db.table(curr.tbl_name, pkg=curr.pkg_name)

        # --- Branch: field is NOT a physical column -- check virtual columns ---
        if not fld in curr.keys():
            fldalias = curr_tblobj.model.getVirtualColumn(fld, sqlparams=self.sqlparams)
            if fldalias == None:
                # No virtual column found -- raise
                raise GnrSqlMissingField('Missing field %s in table %s.%s (requested field %s)' % (
                fld, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))

            elif fldalias.relation_path and not fldalias.composed_of:
                # Branch: virtual column defined as a relation_path alias
                # -- recurse to resolve the underlying relation
                return self.getFieldAlias(fldalias.relation_path, curr=curr,
                                          basealias=alias, parent='.'.join(pathlist))

                # REVIEW: dead code below -- old alternative implementation
                # for refs #120, left commented for investigation. Consider
                # removing after verifying #120 is resolved.
                ### FIXME: refs #120 - left to support investigation
                #pathlist.append(fldalias.relation_path)
                #newfieldpath = '.'.join(pathlist)        # replace the field alias with the column relation_path
                # then call getFieldAlias again with the real path
                #return self.getFieldAlias(f"{'.'.join(pathlist)}.{fldalias.relation_path}", #curr=curr,
                #                                          basealias=basealias), #parent='.'.join(pathlist))  # call getFieldAlias recursively


            elif fldalias.sql_formula or fldalias.select or fldalias.exists:
                # Branch: virtual column with sql_formula / select / exists
                sql_formula = fldalias.sql_formula
                attr = dict(fldalias.attributes)
                # If sql_formula is literally True, delegate to the
                # table's sql_formula_<fieldname> method
                if sql_formula is True:
                    sql_formula = getattr(curr_tblobj,'sql_formula_%s' %fld)(attr)
                select_dict = dictExtract(attr,'select_')
                # If no formula was provided, build default sub-select wrapper
                if not sql_formula:
                    sql_formula = '#default' if fldalias.select else 'EXISTS(#default)'
                    select_dict['default'] = fldalias.select or fldalias.exists
                if select_dict:
                    for susbselect,sq_pars in list(select_dict.items()):
                        if isinstance(sq_pars, str):
                            sq_pars = getattr(self.tblobj.dbtable,'subquery_%s' %sq_pars)()
                        sq_pars = dict(sq_pars)
                        cast = sq_pars.pop('cast',None)
                        tpl = ' CAST( ( %s ) AS ' +cast +') ' if cast else ' ( %s ) '
                        sq_table = sq_pars.pop('table')
                        sq_where = sq_pars.pop('where')
                        sq_pars.setdefault('ignorePartition',True)
                        sq_pars.setdefault('excludeDraft',False)
                        sq_pars.setdefault('excludeLogicalDeleted',False)
                        sq_pars.setdefault('subtable','*')
                        aliasPrefix = '%s_t' %alias
                        sq_where = THISFINDER.sub(expandThis,sq_where)
                        sql_text = self.db.queryCompile(table=sq_table,where=sq_where,aliasPrefix=aliasPrefix,addPkeyColumn=False,ignoreTableOrderBy=True,**sq_pars)
                        sql_formula = re.sub('#%s\\b' %susbselect, tpl %sql_text,sql_formula)
                subreldict = {}
                sql_formula = self.macro_expander.replace(sql_formula,'TSRANK,TSHEADLINE,VECRANK')
                sql_formula = self.updateFieldDict(sql_formula, reldict=subreldict)
                sql_formula = BETWEENFINDER.sub(self.expandBetween, sql_formula)
                sql_formula = ENVFINDER.sub(expandEnv, sql_formula)
                sql_formula = PREFFINDER.sub(expandPref, sql_formula)
                sql_formula = THISFINDER.sub(expandThis,sql_formula)
                sql_formula_var = dictExtract(attr,'var_')
                if sql_formula_var:
                    prefix = str(id(fldalias))
                    currentEnv = self.db.currentEnv
                    for k,v in list(sql_formula_var.items()):
                        newk = f'{prefix}_{self._currColKey}_{k}'
                        currentEnv[newk] = v
                        sql_formula = re.sub("(:)(%s)(\\W|$)" %k,lambda m: '%senv_%s%s'%(m.group(1),newk,m.group(3)), sql_formula)
                subColPars = {}
                for key, value in list(subreldict.items()):
                    subColPars[key] = self.getFieldAlias(value, curr=curr, basealias=alias)
                sql_formula = gnrstring.templateReplace(sql_formula, subColPars, safeMode=True)
                return f'( {sql_formula} )'
            elif fldalias.py_method:
                # Branch: column computed in Python -- emit NULL in SQL
                # and register the py_method for post-query evaluation
                #self.cpl.pyColumns.append((fld,getattr(self.tblobj.dbtable,fldalias.py_method,None)))
                self.cpl.pyColumns.append((fld,getattr(fldalias.table.dbtable,fldalias.py_method,None)))
                return 'NULL'
            else:
                # Branch: virtual column has no usable definition
                raise GnrSqlMissingColumn('Invalid column %s in table %s.%s (requested field %s)' % (
                fld, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))

        # --- Field is a physical column: return alias.sqlname ---
        return '%s.%s' % (self.db.adapter.asTranslator(alias), curr_tblobj.column(fld).adapted_sqlname)

    def _findRelationAlias(self, pathlist, curr, basealias, newpath, parent=None):
        """Recursively resolve a relation path into the JOIN alias.

        Walks through *pathlist* one segment at a time.  For each segment:

        - If the node has a ``joiner``, delegates to ``_getRelationAlias``
          to build the JOIN clause and obtain the alias.
        - If the node is a *table alias* (no joiner), expands its
          ``relation_path`` and prepends it to the remaining path segments.

        Args:
            pathlist: Mutable list of remaining relation segments to
                resolve (consumed during recursion).
            curr: Current node in the relation resolver tree.
            basealias: SQL alias of the table corresponding to *curr*.
            newpath: Accumulator list tracking the physical relation path
                traversed so far (used for error messages).
            parent: Dot-separated prefix of already-traversed segments
                (used to qualify sub-query references in join conditions).

        Returns:
            tuple[str, object]: ``(alias, curr)`` where *alias* is the SQL
            alias (e.g. ``'t3'``) of the final table and *curr* is the
            corresponding relation resolver node.

        Raises:
            GnrSqlMissingField: If a segment cannot be found as either
                a relation or a table alias.
        """
        p = pathlist.pop(0)
        currNode = curr.getNode(p)
        if not currNode:
            raise GnrSqlMissingField(f"Relation {p} not found")
        joiner = currNode.attr['joiner']

        if joiner == None:
            # Branch: no joiner -- this segment is a table alias, not a relation.
            # Expand the alias's relation_path and prepend to remaining segments.
            tblalias = self.db.table(curr.tbl_name, pkg=curr.pkg_name).model.table_aliases[p]
            if tblalias == None:
                # REVIEW: the original comment mentions GnrSqlBadRequest which
                # no longer exists. Replaced with GnrSqlMissingField but the
                # error message may not be entirely appropriate.
                #DUBBIO: non esiste più GnrSqlBadRequest
                #from gnr.sql.gnrsql import
                #raise GnrSqlBadRequest('Missing field %s in requested field %s' % (p, fieldpath))
                raise GnrSqlMissingField('Missing field %s in table %s.%s (requested field %s)' % (
                p, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))
            else:
                # Replace the alias with its underlying relation_path segments
                pathlist = tblalias.relation_path.split(
                        '.') + pathlist # set the alias table relation_path in the current path
        else:
            # Branch: real relation -- build or reuse JOIN
            alias, newpath = self._getRelationAlias(currNode, newpath, basealias, parent=parent)
            basealias = alias
            curr = curr[p]

        # Continue recursion if there are remaining path segments
        if pathlist:
            alias, curr = self._findRelationAlias(pathlist, curr, basealias, newpath, parent=f"{parent}.{p}" if parent else p)
        return alias, curr

    # REVIEW: dead code -- _getJoinerCnd was commented out. If it is no
    # longer needed it should be removed entirely.
    #def _getJoinerCnd(self, joiner):

    def _getRelationAlias(self, relNode, path, basealias, parent=None):
        """Build (or reuse) the JOIN clause for a single relation hop.

        If this relation was already traversed in the current compilation
        (same *path* + *basealias* key), the existing alias is returned
        immediately.  Otherwise a new ``LEFT JOIN`` clause is generated
        and appended to ``self.cpl.joins``.

        The method handles several join flavours:

        - Standard single-column foreign key.
        - Composite (multi-column) foreign keys.
        - Case-insensitive joins.
        - Virtual joins (``joiner['virtual']``).
        - Custom ``cnd`` / ``join_on`` expressions.
        - ``between`` range joins (deprecated in favour of ``#BETWEEN``).

        Args:
            relNode: The relation resolver node carrying the ``joiner``
                attribute dict.
            path: Accumulator list tracking the physical relation path
                traversed so far.
            basealias: SQL alias of the *from* side of the join.
            parent: Dot-separated prefix of already-traversed segments
                (used to qualify column references in the ON clause).

        Returns:
            tuple[str, list]: ``(alias, newpath)`` where *alias* is the
            SQL alias for the joined table and *newpath* is the updated
            path accumulator.
        """
        #ref = attrs['many_relation'].split('.')[-1]
        joiner = relNode.attr['joiner']
        ref = joiner['many_relation'].split('.', 1)[-1] #fix 25-11-09
        newpath = path + [ref]
        pw = tuple(newpath+[basealias])

        # --- Fast path: join already exists from a previous column ---
        if pw in self.aliases:
            if pw in self._explodingTables:
                if not self._currColKey in self.cpl.explodingColumns:
                    self.cpl.explodingColumns.append(self._currColKey)
            return self.aliases[pw], newpath

        # --- New join: allocate a fresh alias ---
        alias = self.aliasCode(len(self.aliases))
        self.aliases[pw] = alias
        manyrelation = False

        # --- Determine target/from tables and columns based on join mode ---
        if joiner['mode'] == 'O':
            # Branch: One-side (we are on the many-side looking up)
            target_tbl = self.dbmodel.table(joiner['one_relation'])
            target_column = joiner['one_relation'].split('.')[-1]
            from_tbl = self.dbmodel.table(joiner['many_relation'])
            from_column = joiner['many_relation'].split('.')[-1]
        else:
            # Branch: Many-side (we are on the one-side looking down)
            target_tbl = self.dbmodel.table(joiner['many_relation'])
            target_column = joiner['many_relation'].split('.')[-1]
            from_tbl = self.dbmodel.table(joiner['one_relation'])
            from_column = joiner['one_relation'].split('.')[-1]
            manyrelation = not joiner.get('one_one', False)

        #target_sqlschema = target_tbl.sqlschema
        #target_sqltable = target_tbl.sqlname
        ignore_tenant = joiner.get('ignore_tenant')
        target_sqlfullname = target_tbl._get_sqlfullname(ignore_tenant=ignore_tenant)

        # --- Build the ON condition ---
        joinerList = []
        # REVIEW: target_sqlcolumn is initialised to None and reassigned only
        # in some branches (from_sqlcolumn falsy + not composed_of, or
        # case_insensitive/virtual). If none of those branches are taken,
        # target_sqlcolumn remains None and may cause errors in subsequent
        # branches that use it (case_insensitive, virtual). Verify that
        # all paths are actually covered.
        target_sqlcolumn = None
        from_sqlcolumn = from_tbl.sqlnamemapper[from_column] if not joiner.get('virtual') else None

        if from_sqlcolumn:
            # Branch: standard single-column join
            joinerList.append((from_sqlcolumn,target_tbl.sqlnamemapper[target_column]))
        elif from_tbl.column(from_column).attributes.get('composed_of'):
            # Branch: composite (multi-column) foreign key
            from_columns = from_tbl.column(from_column).composed_of
            target_columns = target_tbl.column(target_column).composed_of
            if not target_columns:
                raise  GnrSqlException('Relation with multikey works only with compositeColumns')
            target_sqlcolumns = [target_tbl.sqlnamemapper[tc] for tc in target_columns.split(',')]
            joinerList = list(zip([from_tbl.sqlnamemapper[from_column] for from_column in from_columns.split(',')], target_sqlcolumns))
        else:
            # Branch: fallback -- use target column directly
            target_sqlcolumn = target_tbl.sqlnamemapper[target_column]

        joindict = dict()
        adaptedAlias = self.db.adapter.adaptSqlName(alias)
        adaptedBaseAlias = self.db.adapter.adaptSqlName(basealias)

        # --- Select join condition flavour ---
        if 'join_on' in joiner:
            joiner['cnd'] = joiner['join_on']
        if joiner.get('cnd'):
            # Branch: explicit condition expression
            cnd = joiner.get('cnd')
            cnd = BETWEENFINDER.sub(self.expandBetween, cnd)
            #cnd = self.updateFieldDict(joiner['cnd'], reldict=joindict)
        elif joiner.get('between'):
            # Branch: legacy ``between`` syntax
            # REVIEW: TODO deprecate -- use #BETWEEN macro instead
            value_field,low_field,high_field = joiner.get('between').split(';')
            cnd = f"""
                ({low_field} IS NULL AND {high_field} IS NOT NULL AND {value_field}<{high_field}) OR
                ({low_field} IS NOT NULL AND {high_field} IS NULL AND {value_field}>={low_field}) OR
                ({low_field} IS NOT NULL AND {high_field} IS NOT NULL AND
                    {value_field} >= {low_field} AND {value_field} < {high_field}) OR
                ({low_field} IS NULL AND {high_field} IS NULL)
            """
            #cnd = self.updateFieldDict(joiner['cnd'], reldict=joindict)
            joiner['cnd'] = cnd
        elif (joiner.get('case_insensitive', False) == 'Y'):
            # Branch: case-insensitive join
            cnd = f'lower({adaptedAlias}.{target_sqlcolumn}) = lower({adaptedBaseAlias}.{from_sqlcolumn})'
        elif joinerList:
            # Branch: multi-column (composite) condition
            cnd = ' AND '.join([f'({adaptedBaseAlias}.{from_column})={adaptedAlias}.{target_sqlcolumn}' for from_column,target_sqlcolumn in joinerList])
        elif joiner.get('virtual'):
            # Branch: virtual relation
            cnd = f'(${from_column})={adaptedAlias}.{target_sqlcolumn}'

        # Qualify column references with parent path when inside a nested relation
        if parent:
            cnd =COLRELFINDER.sub(lambda g:f'{parent}.'+g.group(0).replace('$',''),cnd)
        cnd = self.updateFieldDict(cnd, reldict=joindict)

        # Resolve any field references found in the join condition
        if joindict:
            for f in joindict.values():
                self.getFieldAlias(f)
            self.cpl.relationDict.update(joindict)

        # Apply extra joinConditions if configured
        if self.joinConditions:
            from_fld, target_fld = self._tablesFromRelation(joiner)
            extracnd, one_one = self.getJoinCondition(target_fld, from_fld, alias,relation=relNode.label)
            if extracnd:
                extracnd = self.embedFieldPars(extracnd)
                extracnd = self.updateFieldDict(extracnd)
                cnd = '(%s AND %s)' % (cnd, extracnd)
                if one_one:
                    manyrelation = False # joinCondition turns many into one_one

        # Emit the LEFT JOIN clause
        self.cpl.joins.append(f'LEFT JOIN {target_sqlfullname} AS {self.db.adapter.adaptSqlName(alias)} ON ({cnd})')

        # Track "exploding" (many-side) joins that multiply result rows
        if manyrelation:
            if not self._currColKey in self.cpl.explodingColumns:
                self.cpl.explodingColumns.append(self._currColKey)
            self._explodingTables.append(pw)
            self._explodingRows = True
        return alias, newpath

    def getJoinCondition(self, target_fld, from_fld, alias, relation=None):
        """Look up an extra ON-condition for a join from ``joinConditions``.

        ``joinConditions`` is a dict (set via ``SqlQuery.setJoinCondition``)
        keyed either by the *relation* name or by
        ``<target>_<from>`` with dots replaced by underscores.

        Each entry is a dict with:

        - ``condition`` (str): SQL fragment; ``$tbl`` is replaced with
          the target table's alias.
        - ``params`` (dict, optional): Bind parameters merged into
          ``self.sqlparams``.
        - ``one_one`` (bool, optional): If ``True``, a many-side join is
          treated as one-to-one (suppresses row explosion).

        Args:
            target_fld: Dot-separated target field identifier, or ``'*'``
                for the main-table wildcard condition.
            from_fld: Dot-separated from field identifier, or ``'*'``.
            alias: SQL alias of the target table.
            relation: Optional relation name used as primary lookup key.

        Returns:
            tuple[str | None, bool | None]: ``(extra_condition, one_one)``
            where *extra_condition* is the SQL fragment (or ``None``) and
            *one_one* indicates if the join should be treated as 1:1.
        """
        extracnd = None
        one_one = None
        joinExtra = self.joinConditions.get(relation or '%s_%s' % (target_fld.replace('.', '_'), from_fld.replace('.', '_')))
        if joinExtra:
            extracnd = joinExtra['condition'].replace('$tbl', alias)
            params = joinExtra.get('params') or dict()
            self.sqlparams.update(params)
            #raise str(self.sqlparams)
            one_one = joinExtra.get('one_one')
        return extracnd, one_one

    def updateFieldDict(self, teststring, reldict=None):
        """Scan a SQL fragment for ``$column`` and ``@relation.column`` references.

        For every ``$column`` reference found, an identity entry is added to
        *reldict* (``{colname: colname}``).

        For every ``@relation.column`` reference found, a flattened alias is
        created (e.g. ``_relation_column``), registered in *reldict*, and the
        original ``@relation.column`` token in *teststring* is replaced with
        ``$_relation_column``.

        After this transformation *teststring* contains only ``$name``
        placeholders which can be resolved to ``alias.sqlname`` via
        ``getFieldAlias`` and then substituted with ``templateReplace``.

        Args:
            teststring: SQL fragment to scan and transform.
            reldict: Mapping to populate.  Defaults to
                ``self.cpl.relationDict``.

        Returns:
            str: The transformed *teststring* with ``@rel`` tokens replaced.
        """
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
        """Expand a glob-style column specification into explicit column paths.

        Handles the following patterns:

        - ``*`` -- all columns of the main table.
        - ``*prefix_`` -- columns of the main table whose name starts with
          *prefix_*.
        - ``*@rel1.@rel2`` -- all columns of the table reached through
          *rel1.rel2*.
        - ``*@rel1.@rel2.prefix_`` -- columns of that related table
          starting with *prefix_*.
        - ``*@rel.(col1,col2,...)`` -- explicit list of related columns
          (also populates ``aggregateDict`` for grouped output).

        Args:
            flt: The filter/pattern string (without the leading ``*``
                that was already stripped by the caller in some paths,
                but may still be present in the ``@`` branch).
            bagFields: If ``True``, include Bag-typed columns (``dtype='X'``)
                when expanding ``*``.

        Returns:
            list[str]: Expanded list of column paths.
        """
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
        """Inline-replace bind parameters whose values are field references.

        If a bind parameter value starts with ``@`` (relation path) or
        ``$`` (column name) and the referenced field actually exists in
        the current table, the ``:paramname`` placeholder in *sql* is
        replaced with the literal field reference so that it becomes part
        of the SQL expression rather than a bind value.

        Args:
            sql: SQL fragment potentially containing ``:paramname``
                placeholders.

        Returns:
            str: The transformed SQL fragment.
        """
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
                      addPkeyColumn=True):
        """Compile a SELECT query for a multi-row selection.

        This is the main entry point used by ``SqlQuery``.  It performs the
        full compilation pipeline:

        1. Normalise and expand the *columns* specification (``*`` globs,
           ``#BAG`` / ``#BAGCOLS`` macros).
        2. Expand macros in the *where* clause (``#BETWEEN``, ``#PERIOD``,
           ``#TSQUERY``).
        3. Assemble additional WHERE predicates (env conditions, partition,
           subtable, logical deletion, draft exclusion).
        4. Scan all SQL fragments for ``$col`` / ``@rel.col`` references
           via ``updateFieldDict``.
        5. Resolve every reference through ``getFieldAlias``, building
           JOIN clauses as a side effect.
        6. Perform final ``templateReplace`` to produce real SQL column /
           where / order_by / group_by / having strings.
        7. Handle DISTINCT injection when many-side joins cause row
           explosion.

        Args:
            columns: Comma-separated column specification.  Supports
                ``$col``, ``@rel.col``, ``*``, ``*prefix_``, and
                ``sql_expression AS alias`` syntax.
            where: SQL WHERE clause (may contain macros).
            order_by: SQL ORDER BY clause.
            distinct: If truthy, force ``SELECT DISTINCT``.  If ``''``
                or ``None``, DISTINCT is auto-injected when many-side
                joins cause row explosion.
            limit: Maximum number of rows to return.
            offset: Number of rows to skip.
            group_by: SQL GROUP BY clause.  Use ``'*'`` to signal
                aggregation without an explicit GROUP BY list.
            having: SQL HAVING clause.
            for_update: If ``True``, add ``FOR UPDATE`` locking.
            relationDict: Optional pre-populated relation dictionary.
            bagFields: If ``True``, include Bag-typed columns when
                expanding ``*``.
            storename: Optional store name; when ``'*'`` or containing
                commas, a ``_dbstore_`` sentinel column is added.
            subtable: Optional subtable filter specification.
            count: If ``True``, optimise for counting rows instead of
                returning data.
            excludeLogicalDeleted: If ``True``, exclude logically deleted
                records.  If ``'mark'``, include them with an
                ``_isdeleted`` flag column.
            excludeDraft: If ``True``, exclude draft records.
            ignorePartition: If ``True``, skip partition conditions.
            ignoreTableOrderBy: If ``True``, ignore the table's default
                ``order_by`` attribute.
            addPkeyColumn: If ``True``, append the primary key column
                to the SELECT list.

        Returns:
            SqlCompiledQuery: Fully populated compiled query ready to be
            rendered to SQL via ``get_sqltext``.
        """
        # get the SqlCompiledQuery: an object that mantains all the informations to build the sql text
        self.cpl = SqlCompiledQuery(self.tblobj.sqlfullname,relationDict=relationDict,maintable_as=self.aliasCode(0))
        distinct = distinct or '' # distinct is a text to be inserted in the sql query string

        # aggregate: test if the result will aggregate db rows
        aggregate = bool(distinct or group_by)

        # group_by == '*': if all columns are aggregate functions, there will be no GROUP BY columns,
        #                  but SqlQueryCompiler need to know that result will aggregate db rows
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
        storename = storename or self.db.currentEnv.get('storename')
        if storename and (storename=='*' or ',' in storename):
            columns = "%s, '_STORENAME_' AS _dbstore_" %columns
        if columns and not columns.endswith(','):
            columns = columns + ','
        # expand * and *filters: see self.expandMultipleColumns
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


        if count:               # if the query is executed in count mode...
            order_by = ''       # sort has no meaning
            if group_by:        # the number of rows is defined only from GROUP BY cols, so clean aggregate functions from columns.
                columns = group_by # was 't0.%s' % self.tblobj.pkey        # ????
            elif distinct:
                pass            # leave columns as is to calculate distinct values
            else:
                columns = 'count(*) AS "gnr_row_count"'  # use the sql count function istead of load all data
        elif addPkeyColumn and self.tblobj.pkey and not aggregate:
            columns = columns + ',\n' + f'${self.tblobj.pkey} AS {self.db.adapter.asTranslator("pkey")}'
            columns = columns.lstrip(',')
        else:
            columns = columns.strip('\n').strip(',')

        # translate @relname.fldname in $_relname_fldname and add them to the relationDict
        currentEnv = self.db.currentEnv
        context_subtables = currentEnv.get('context_subtables',Bag()).getItem(self.tblobj.fullname)
        if not subtable and context_subtables:
            subtable = context_subtables
        subtable = subtable or self.tblobj.attributes.get('default_subtable')
        if where:
            where = BETWEENFINDER.sub(self.expandBetween, where)
            where = PERIODFINDER.sub(self.expandPeriod, where)
            where = self.macro_expander.replace(where,'TSQUERY,VECQUERY')

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
                columns = '{columns},${logicalDeletionField} AS "_isdeleted"'.format(columns=columns, logicalDeletionField=logicalDeletionField) #add logicalDeletionField

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
                    # replace non word char with _ and check for numbers
                    as_ = self.db.colToAs(col)
                as_ = self.db.adapter.asTranslator(as_)
                col = '%s AS %s' % (col, as_)
            else:
                colbody, as_ = col.split(' AS ', 1)
                # leave the col as is, but save the AS name to recover the db column original name from selection result
                as_ = self.db.adapter.asTranslator(as_.strip())
                self.cpl.aliasDict[as_] = colbody.strip()
            col_dict[as_] = col
        # build the clean and complete sql string for the columns, but still all fields are expressed as $fieldname
        as_col_values = col_dict.values()
        columns = ',\n'.join(as_col_values)
        # translate all fields and related fields from $fldname to t0.fldname, t1.fldname... and prepare the JOINs
        colPars = {}
        for key, value in list(self.cpl.relationDict.items()):
            # self._currColKey manage exploding columns in recursive getFieldAlias without add too much parameters
            self._currColKey = key
            colPars[key] = self.getFieldAlias(value)
        missingKeys = list(set(self.cpl.relationDict.keys()).difference(set(colPars.keys())))
        while missingKeys:
            for key in missingKeys:
                self._currColKey = key
                colPars[key] = self.getFieldAlias(self.cpl.relationDict[key])
            missingKeys = list(set(self.cpl.relationDict.keys()).difference(set(colPars.keys())))


        # replace $fldname with tn.fldname: finally the real SQL columns!
        columns = gnrstring.templateReplace(columns, colPars, safeMode=True)

        # replace $fldname with tn.fldname: finally the real SQL where!
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
        #self.cpl.additional_joins.reverse()
        self.cpl.joins = [gnrstring.templateReplace(j, colPars) for j in self.cpl.joins+self.cpl.additional_joins]
        # --- DISTINCT handling ---
        if distinct:
            # Branch: caller explicitly requested DISTINCT
            distinct = 'DISTINCT '
        elif distinct is None or distinct == '':
            if self._explodingRows:
                # Branch: many-side JOINs detected -- auto-inject DISTINCT
                if not aggregate:
                    distinct = 'DISTINCT '
                    # When DISTINCT is used with ORDER BY, every ORDER BY
                    # expression must appear in the SELECT list.  Add any
                    # missing order columns as hidden __ord_col_N aliases.
                    if order_by:
                        xorderby= gnrstring.split((('%s '%order_by.lower()).replace(' ascending ','').replace(' descending ','').replace(' asc ','').replace(' desc','')),',')
                        lowercol=columns.lower()
                        for i,xrd in enumerate(xorderby):
                            if not xrd.strip() in lowercol:
                                columns = '%s, \n%s AS __ord_col_%s' % (columns, xrd,i)
                    #order_by=None
                    if count:
                        # REVIEW: counting with DISTINCT on pkey returns the number
                        # of rows in the main table, not the actual number of rows
                        # after explosion. The original comment asks
                        # "It is the right behaviour ????" -- the answer is "yes"
                        # in some cases (see _aggregateRows), but it may surprise
                        # callers expecting the real exploded row count.
                        # Consider better documentation or making it configurable.
                        columns = '%s.%s' % (self.aliasCode(0),self.tblobj.pkey)

        # --- Store all compiled fragments into the SqlCompiledQuery ---
        self.cpl.distinct = distinct
        self.cpl.columns = self.macro_expander.replace(columns,'TSRANK,TSHEADLINE,VECRANK')
        self.cpl.where = where
        self.cpl.group_by = group_by
        self.cpl.having = having
        self.cpl.order_by = self.macro_expander.replace(order_by,'TSRANK,VECRANK')
        self.cpl.limit = limit
        self.cpl.offset = offset
        self.cpl.for_update = for_update
        # REVIEW: commented-out debug raise -- remove if no longer needed
        #raise str(self.cpl.get_sqltext(self.db))  # uncomment it for hard debug
        return self.cpl

    def compiledRecordQuery(self, lazy=None, eager=None, where=None,
                            bagFields=True, for_update=False, relationDict=None, virtual_columns=None):
        """Compile a SELECT query for a single-record fetch.

        Used by ``SqlRecord`` to build a query that retrieves all physical
        columns of the main table plus any requested virtual columns, with
        the relation tree metadata stored in ``cpl.resultmap`` so that
        related data can be lazily or eagerly loaded later.

        Args:
            lazy: Optional list of relation paths to load lazily (on
                first access).
            eager: Optional list of relation paths to load immediately
                as part of the main query.
            where: SQL WHERE clause identifying the record (may contain
                macros).
            bagFields: If ``True``, include Bag-typed columns
                (``dtype='X'``) in the result.
            for_update: If ``True``, add ``FOR UPDATE`` locking.
            relationDict: Optional pre-populated relation dictionary.
            virtual_columns: List (or comma-separated string) of virtual
                column names to include in the query.

        Returns:
            SqlCompiledQuery: Fully populated compiled query.
        """
        self.cpl = SqlCompiledQuery(self.tblobj.sqlfullname, relationDict=relationDict)
        if 'pkey' not in self.cpl.relationDict and self.tblobj.pkey:
            self.cpl.relationDict['pkey'] = self.tblobj.pkey
        self.init(lazy=lazy, eager=eager)
        colPars = {}
        joindict = {}
        virtual_columns = virtual_columns or []
        # REVIEW: duplicated line -- the following line is identical to the
        # previous one and has no effect. Likely a copy-paste leftover.
        virtual_columns = virtual_columns or []
        if isinstance(virtual_columns, str):
            virtual_columns = gnrstring.splitAndStrip(virtual_columns, ',')

        # Iterate over all fields/relations of the main table
        for fieldname, value, attrs in self.relations.digest('#k,#v,#a'):
            xattrs = {k:v for k, v in attrs.items() if not k in ['tag', 'comment', 'table', 'pkg']}
            # Skip Bag-typed columns unless explicitly requested
            #if not (bagFields or (attrs.get('dtype') != 'X')):
            if attrs.get('dtype') == 'X' and not bagFields:
                continue
            joiner = attrs.get('joiner')
            if joiner:
                # Branch: this field is a relation -- record metadata
                # for lazy/eager loading, don't add it to the SELECT list
                if joiner.get('virtual') and joiner['mode'] == 'O':
                    virtual_columns.append(fieldname[1:])
                    for relation_condition in ('cnd', 'range'):
                        rel_cnd = joiner.get(relation_condition)
                        if rel_cnd:
                            self.updateFieldDict(rel_cnd, reldict=joindict)
                xattrs['_relmode'] = self._getRelationMode(attrs['joiner'])
            else:
                # Branch: physical column -- add to the SELECT list
                sqlname = attrs.get('sqlname') or fieldname
                self.fieldlist.append( '%s.%s AS %s' % (self.db.adapter.adaptSqlName(self.aliasCode(0)),self.db.adapter.adaptSqlName(sqlname),self.db.adapter.asTranslator('%s_%s'%(self.aliasCode(0),fieldname))))
                xattrs['as'] = '%s_%s' %(self.aliasCode(0),fieldname)
            self.cpl.resultmap.setItem(fieldname, None, xattrs)

        # Resolve virtual columns (sql_formula, py_method, etc.)
        self._handle_virtual_columns(virtual_columns)
        self.cpl.where = self._recordWhere(where=where)
        self.cpl.columns = ',\n       '.join(self.fieldlist)
        self.cpl.for_update = for_update

        # Resolve any field references that appeared in join conditions
        for key, value in list(joindict.items()):
            colPars[key] = self.getFieldAlias(value)
        self.cpl.joins = [gnrstring.templateReplace(j, colPars) for j in self.cpl.joins]

        return self.cpl


    def _getRelationMode(self, joiner):
        """Determine the dynamic-item mode for a relation.

        Returns a string identifier used by ``SqlRecord`` to decide how
        to lazily load the related data:

        - ``'DynItemOne'`` -- one-side of a relation (foreign key lookup).
        - ``'DynItemOneOne'`` -- one-to-one relation (including many-side
          relations narrowed to 1:1 by a join condition).
        - ``'DynItemMany'`` -- many-side relation.

        Args:
            joiner: The joiner attribute dict from the relation node.

        Returns:
            str: One of ``'DynItemOne'``, ``'DynItemOneOne'``,
            ``'DynItemMany'``.
        """
        if joiner['mode'] == 'O':
            return 'DynItemOne'
        isOneOne = joiner.get('one_one')
        if not isOneOne and self.joinConditions:
            from_fld, target_fld = self._tablesFromRelation(joiner)
            extracnd, isOneOne = self.getJoinCondition(target_fld, from_fld, '%s0' %self.aliasPrefix)
        return 'DynItemOneOne' if isOneOne else 'DynItemMany'


    def _handle_virtual_columns(self, virtual_columns):
        """Resolve virtual columns and add them to the field list.

        For each virtual column, resolves its SQL expression via
        ``getFieldAlias`` and appends the resulting ``expression AS alias``
        entry to ``self.fieldlist``.  Also populates ``cpl.resultmap``
        with the column's metadata.

        Args:
            virtual_columns: A list of virtual column names, a
                comma-separated string, or ``False`` to skip entirely.
        """
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
                # REVIEW: commented-out debug print -- column=None is silently
                # skipped via continue. This may hide configuration errors.
                # Consider adding a logging.warning.
                #print 'not existing col:%s' % col_name  # jbe commenting out the print
                continue
            column_attributes = self.tblobj.virtualColumnAttributes(col_name)
            self._currColKey = col_name
            field = self.getFieldAlias(column.name)

            xattrs = dict([(k, v) for k, v in list(column_attributes.items()) if not k in ['tag', 'comment', 'table', 'pkg']])

            if column_attributes['tag'] == 'virtual_column':
                as_name = '%s_%s' % (self.aliasCode(0), column.name)
                path_name = column.name
            else:
                # REVIEW: the else branch contains only ``pass`` and does not
                # assign as_name or path_name. If entered, variables retain
                # values from the previous iteration (or are undefined on the
                # first iteration), causing a potential NameError or silently
                # wrong behaviour. Verify whether this branch is actually
                # reachable and, if so, handle it explicitly.
                pass
            xattrs['as'] = as_name
            self.fieldlist.append('%s AS %s' % (field, as_name))
            self.cpl.resultmap.setItem(path_name, None, xattrs)
            #self.cpl.dicttemplate[path_name] = as_name

    def expandBag(self, m):
        """Regex callback: expand a ``#BAG($field) AS alias`` macro.

        Registers the column for post-query Bag evaluation (the raw value
        will be parsed into a ``Bag`` object after fetching).

        Args:
            m: Regex match object with groups (1) field, (3) optional alias.

        Returns:
            str: The column expression, optionally with ``AS alias``.
        """
        fld = m.group(1)
        asfld = m.group(3)
        self.cpl.evaluateBagColumns.append(((asfld or fld).replace('$',''),False))
        return fld if not asfld else '{} AS {}'.format(fld, asfld)

    def expandBagcols(self, m):
        """Regex callback: expand a ``#BAGCOLS($field) AS alias`` macro.

        Like ``expandBag`` but the second element of the registered tuple
        is ``True``, signalling that the Bag should be expanded into
        individual columns.

        Args:
            m: Regex match object with groups (1) field, (3) optional alias.

        Returns:
            str: The column expression, optionally with ``AS alias``.
        """
        fld = m.group(1)
        asfld = m.group(3)
        self.cpl.evaluateBagColumns.append(((asfld or fld).replace('$',''),True))
        return fld if not asfld else '{} AS {}'.format(fld, asfld)

    def expandBetween(self, m):
        """Regex callback: expand ``#BETWEEN(value, low, high)`` into SQL.

        Generates a four-branch OR expression that handles NULLs on either
        bound:

        - Only high bound present: ``value <= high``.
        - Only low bound present: ``value >= low``.
        - Both bounds present: ``low <= value <= high``.
        - Both NULL: always true.

        Args:
            m: Regex match object with groups (1) value_field,
                (2) low_field, (3) high_field.

        Returns:
            str: SQL fragment implementing the inclusive range check.
        """
        # Example: #BETWEEN($dataLavoro,$dataInizioValidita,$dataFineValidita)
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
        # REVIEW: TODO -- verify whether the upper bound should be inclusive
        # (<=) or exclusive (<). Currently inclusive, but the legacy between
        # in _getRelationAlias uses < for the upper bound.
        # Inconsistent behaviour between the two.
        return result

    def expandPeriod(self, m):
        """Regex callback: expand ``#PERIOD($field, param)`` into a date range.

        Decodes the period string stored in ``self.sqlparams[param]``
        (e.g. ``'2024Q1'``, ``'202401'``) into concrete ``date_from`` /
        ``date_to`` values via ``decodeDatePeriod``, then generates the
        appropriate SQL predicate:

        - Both dates present and equal: ``field = :param_from``.
        - Both dates present: ``field BETWEEN :param_from AND :param_to``.
        - Only from: ``field >= :param_from``.
        - Only to: ``field <= :param_to``.
        - Neither: ``true`` (no filtering).

        Side effect: adds ``param_from`` and/or ``param_to`` keys to
        ``self.sqlparams``.

        Args:
            m: Regex match object with groups (1) field, (2) param name.

        Returns:
            str: SQL fragment for the period filter.
        """
        fld = m.group(1)
        period_param = m.group(2)
        date_from, date_to = decodeDatePeriod(self.sqlparams[period_param],
                                              workdate=self.db.workdate,
                                              returnDate=True, locale=self.db.locale)
        from_param = '%s_from' % period_param
        to_param = '%s_to' % period_param

        # Branch: no date boundaries -- no filtering
        if date_from is None and date_to is None:
            return ' true'
        # Branch: both boundaries present
        elif date_from and date_to:
            if date_from == date_to:
                # Single-day period
                self.sqlparams[from_param] = date_from
                return ' %s = :%s ' % (fld, from_param)

            self.sqlparams[from_param] = date_from
            self.sqlparams[to_param] = date_to
            # REVIEW: TODO -- deprecare l'uso di BETWEEN nativo SQL a favore
            # di >= / < per coerenza con il comportamento delle date (il
            # BETWEEN SQL e' inclusivo su entrambi gli estremi).
            result = ' (%s BETWEEN :%s AND :%s) ' % (fld, from_param, to_param)
            return result

        # Branch: only lower bound
        elif date_from:
            self.sqlparams[from_param] = date_from
            return ' %s >= :%s ' % (fld, from_param)
        # Branch: only upper bound
        else:
            self.sqlparams[to_param] = date_to
            return ' %s <= :%s ' % (fld, to_param)

    def _recordWhere(self, where=None):
        """Compile a WHERE clause for a single-record query.

        Scans *where* for column/relation references, resolves them to
        SQL aliases, and performs template replacement.

        Used by ``compiledRecordQuery`` and the record resolver.

        Args:
            where: Optional WHERE clause string (may contain ``$col``
                and ``@rel.col`` tokens).

        Returns:
            str | None: The compiled WHERE string, or ``None`` if no
            *where* was provided.
        """
        if where:
            self.updateFieldDict(where)
            colPars = {}
            for key, value in list(self.cpl.relationDict.items()):
                colPars[key] = self.getFieldAlias(value)
            where = gnrstring.templateReplace(where, colPars)
        return where

    def _tablesFromRelation(self, attrs):
        """Extract the from/target field identifiers from a joiner dict.

        Swaps the identifiers based on the join direction so that the
        caller always gets ``(from_fld, target_fld)`` regardless of
        whether the relation is mode ``'O'`` (one-side) or ``'M'``
        (many-side).

        Args:
            attrs: Joiner attribute dict with keys ``mode``,
                ``one_relation``, ``many_relation``.

        Returns:
            tuple[str, str]: ``(from_fld, target_fld)`` as dot-separated
            ``pkg.table.column`` identifiers.
        """
        if attrs['mode'] == 'O':
            target_fld = attrs['one_relation']
            from_fld = attrs['many_relation']
        else:
            target_fld = attrs['many_relation']
            from_fld = attrs['one_relation']
        return from_fld, target_fld


# ===========================================================================
# REVIEW NOTES (compiler.py)
# ===========================================================================
#
# List of oddities, dead code, and suspicious spots found during the
# documentation of this module.  Each entry corresponds to a
# ``# REVIEW:`` marker in the source code.
#
# 1. _getJoinerCnd (dead code)
#    - Commented-out method just before _getRelationAlias.
#    - Never referenced elsewhere.  Remove if no longer needed.
#
# 2. _findRelationAlias -- non-existent GnrSqlBadRequest
#    - The original comment notes that GnrSqlBadRequest no longer exists.
#    - Replaced by GnrSqlMissingField, but the error message may not be
#      appropriate for the "table alias not found" case.
#
# 3. getFieldAlias -- FIXME refs #120 (dead code)
#    - Commented-out code block after the recursive return on
#      fldalias.relation_path.  Left for investigation on issue #120.
#    - Check whether #120 has been resolved and, if so, remove.
#
# 4. compiledQuery -- commented-out debug raise
#    - ``#raise str(self.cpl.get_sqltext(self.db))`` at end of method.
#    - Manual debug aid.  Remove or convert to logging.
#
# 5. compiledQuery -- distinct/exploding + count
#    - The original comment asks "It is the right behaviour ????"
#      regarding DISTINCT count on pkey with many-side joins.
#    - The answer is "yes" in some cases (see _aggregateRows) but may
#      surprise callers.  Document better or make configurable.
#
# 6. _handle_virtual_columns -- else branch with only ``pass``
#    - When column_attributes['tag'] != 'virtual_column', the else branch
#      does not assign as_name or path_name.  Variables retain values from
#      the previous iteration (or NameError on the first).
#    - Verify whether this branch is actually reachable.
#
# 7. _handle_virtual_columns -- commented-out debug print
#    - ``#print 'not existing col:%s' % col_name`` is Python 2 syntax.
#    - If a warning is needed, use logging.warning.
#
# 8. expandBetween -- interval inclusivity inconsistency
#    - expandBetween uses ``<=`` (inclusive) on the upper bound.
#    - The legacy between in _getRelationAlias uses ``<`` (exclusive).
#    - Inconsistent behaviour: unify.
#
# 9. expandPeriod -- SQL BETWEEN
#    - Uses native ``BETWEEN`` (inclusive on both ends).
#    - For dates, ``>= / <`` might be more correct.
#    - Consider deprecating in favour of explicit range.
#
# 10. compiledRecordQuery -- duplicated line
#     - ``virtual_columns = virtual_columns or []`` appears twice in a
#       row.  The second is a no-op.  Copy-paste leftover.
#
# 11. _getRelationAlias -- target_sqlcolumn potentially None
#     - target_sqlcolumn is initialised to None and reassigned only in
#       some branches (else of the from_sqlcolumn/composed_of block).
#     - In the case_insensitive and virtual branches it is used:
#       if those branches are reached without going through the else,
#       target_sqlcolumn is None and a runtime error would occur.
#     - Verify that all paths are covered.
#
# ===========================================================================
