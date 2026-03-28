#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_record : SQL record and resolvers
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
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

"""Single-record loading, resolvers and result container.

This module provides:

- ``SqlRelatedRecordResolver`` / ``SqlRelatedSelectionResolver``:
  lazy BagResolver subclasses used to populate related record/selection
  sub-trees on demand (e.g. ``@relation_name`` nodes inside a record Bag).

- ``SqlRecord``: compiles and executes a query that returns exactly one
  row, then builds a hierarchical ``Bag`` representation of the record
  with nested resolvers for every related table.

- ``SqlRecordBag``: a thin Bag subclass that adds a convenience
  ``save()`` method (insert-or-update) and carries a reference to the
  originating ``db`` and ``tablename``.
"""

from gnr.core import gnrstring
from gnr.core.gnrbag import Bag, BagResolver
from gnr.sql.gnrsqldata.compiler import SqlQueryCompiler
from gnr.sql.gnrsql_exceptions import SelectionExecutionError, RecordDuplicateError, \
    RecordNotExistingError, RecordSelectionError


class SqlRelatedRecordResolver(BagResolver):
    """Lazy resolver that loads a single related record on first access.

    Attached as resolver on ``@relation_name`` nodes inside a record Bag.
    When the node is accessed, ``load()`` creates a ``SqlRecord`` for the
    target table/field and returns its output in the requested *mode*.

    Attributes:
        target_fld: Fully-qualified field reference ``pkg.table.column``
            that identifies the foreign-key target.
        relation_value: The value used to match ``target_fld``.
        mode: Output mode forwarded to ``SqlRecord.output()`` (typically
            ``'bag'``).
    """
    classKwargs = {'cacheTime': 0,
                   'readOnly': True,
                   'db': None,
                   'mode': None,
                   'joinConditions': None,
                   'sqlContextName': None,
                   'virtual_columns': None,
                   'ignoreMissing': False,
                   'ignoreDuplicate': False,
                   'bagFields': True,
                   'target_fld': None,
                   'relation_value': None}

    # REVIEW: resolverSerialize() is nearly identical to
    # SqlRelatedSelectionResolver.resolverSerialize() -- consider
    # extracting into a mixin or shared helper method.
    def resolverSerialize(self):
        """Serialize the resolver state for Bag persistence.

        Returns:
            dict: A dictionary with module, class, args and kwargs suitable
            for later reconstruction. The ``db`` reference is replaced by
            a symbolic ``'maindb'`` marker.
        """
        attr = {}
        attr['resolvermodule'] = self.__class__.__module__
        attr['resolverclass'] = self.__class__.__name__
        attr['args'] = list(self._initArgs)
        attr['kwargs'] = dict(self._initKwargs)
        attr['kwargs'].pop('db')
        attr['kwargs']['_serialized_app_db'] = 'maindb'
        return attr

    def load(self):
        """Load the related record from the database.

        Splits ``target_fld`` into *pkg.table.column*, builds a
        ``SqlRecord`` with the appropriate parameters, and returns its
        output in the configured ``mode``.

        Returns:
            Bag or other: The record output in the requested mode.
        """
        pkg, tbl, related_field = self.target_fld.split('.')
        dbtable = '%s.%s' % (pkg, tbl)
        recordpars = dict()
        recordpars[str(related_field)] = self.relation_value
        # If the parent node specifies a store field, propagate it
        if self.parentNode.attr.get('_storefield'):
            recordpars['_storename'] = self.parentNode.parentbag[self.parentNode.attr.get('_storefield')]
        record = SqlRecord(self.db.table(dbtable), joinConditions=self.joinConditions,
                           sqlContextName=self.sqlContextName,
                           ignoreMissing=self.ignoreMissing, ignoreDuplicate=self.ignoreDuplicate,
                           virtual_columns=self.virtual_columns,
                           bagFields=self.bagFields, **recordpars)
        return record.output(self.mode)


class SqlRelatedSelectionResolver(BagResolver):
    """Lazy resolver that loads a related *selection* (many-side) on first access.

    Attached as resolver on ``@relation_name`` nodes where the relation is
    one-to-many. When accessed, ``load()`` runs a ``relatedQuery`` on the
    target table and returns the selection output (typically ``'grid'``).

    Attributes:
        target_fld: Fully-qualified field reference ``pkg.table.column``.
        relation_value: The value used to filter the many-side rows.
        condition: Optional extra WHERE condition.
        columns: Columns to select (defaults to ``'*'``).
        mode: Output mode for the resulting ``SqlSelection``.
    """
    classKwargs = {'cacheTime': 0, 'readOnly': True, 'db': None,
                   'columns': None, 'mode': None, 'sqlparams': None, 'joinConditions': None, 'sqlContextName': None,
                   'target_fld': None, 'relation_value': None, 'condition': None, 'bagFields': None,'virtual_columns':None}

    # REVIEW: resolverSerialize() is nearly identical to
    # SqlRelatedRecordResolver.resolverSerialize() -- consider
    # extracting into a mixin or shared helper method.
    def resolverSerialize(self):
        """Serialize the resolver state for Bag persistence.

        Returns:
            dict: A dictionary with module, class, args and kwargs suitable
            for later reconstruction.
        """
        attr = {}
        attr['resolvermodule'] = self.__class__.__module__
        attr['resolverclass'] = self.__class__.__name__
        attr['args'] = list(self._initArgs)
        attr['kwargs'] = dict(self._initKwargs)
        attr['kwargs'].pop('db')
        attr['kwargs']['_serialized_app_db'] = 'maindb'
        return attr

    def load(self):
        """Load the related selection from the database.

        Builds a ``relatedQuery`` on the target table filtered by
        ``relation_value`` and returns the selection output in the
        configured ``mode``.

        Returns:
            Bag or other: The selection output in the requested mode.
        """
        pkg, tbl, related_field = self.target_fld.split('.')
        dbtable = '%s.%s' % (pkg, tbl)
        query = self.db.table(dbtable).relatedQuery(field=related_field,value=self.relation_value,where=self.condition,
                                                    sqlContextName=self.sqlContextName, **self.sqlparams)
        return query.selection().output(self.mode, recordResolver=(self.mode == 'grid'),virtual_columns=self.virtual_columns)

class SqlRecord(object):
    """Compile and execute a single-record query, producing a hierarchical Bag.

    ``SqlRecord`` encapsulates the process of:

    1. Building a ``SqlCompiledQuery`` via ``SqlQueryCompiler.compiledRecordQuery``.
    2. Executing the compiled SQL and fetching exactly one row.
    3. Walking the ``resultmap`` to populate a ``SqlRecordBag`` with scalar
       fields and lazy resolvers for every declared relation.

    The ``output()`` dispatcher delegates to ``out_bag``, ``out_dict``,
    ``out_json``, ``out_record``, ``out_newrecord``, ``out_sample`` or
    ``out_template`` depending on the requested *mode*.
    """
    def __init__(self, dbtable, pkey=None, where=None,
                 lazy=None, eager=None, relationDict=None,
                 sqlparams=None,
                 ignoreMissing=False, ignoreDuplicate=False,
                 bagFields=True, for_update=False,
                 joinConditions=None, sqlContextName=None,
                 virtual_columns=None,_storename=None,
                 checkPermissions=None,
                 aliasPrefix=None,
                 **kwargs):
        """Initialize a single-record query builder.

        Args:
            dbtable: The ``SqlTable`` instance to query.
            pkey: Primary key value. If the table has a composite key and
                *pkey* starts with ``'['``, it is parsed into individual
                field params.
            where: Optional explicit WHERE clause (overrides pkey lookup).
            lazy: List of relations to resolve lazily.
            eager: List of relations to resolve eagerly.
            relationDict: Symbolic names for relation paths.
            sqlparams: Dictionary of SQL bind parameters.
            ignoreMissing: If ``True``, return an empty Bag instead of
                raising ``RecordNotExistingError`` when no row is found.
            ignoreDuplicate: If ``True``, silently take the first row
                when multiple rows match.
            bagFields: Include Bag-type (``dtype='X'``) fields.
            for_update: If ``True``, add ``FOR UPDATE`` to the query.
            joinConditions: Extra conditions for related-table joins.
            sqlContextName: Named SQL context for sub-resolvers.
            virtual_columns: Comma-separated virtual columns to include.
            _storename: Optional store name for multi-store setups.
            checkPermissions: Permission check parameters.
            aliasPrefix: Prefix for table aliases (default ``'t'``).
            **kwargs: Additional field=value pairs merged into *sqlparams*.
        """
        # REVIEW: the check ``if pkey and ...`` uses truthiness -- fails for
        # pkey=0 (int) or pkey='' (empty string). Consider ``if pkey is not None``.
        if pkey and len(dbtable.pkeys)>1 and pkey.startswith('['):
            sqlparams = sqlparams or {}
            sqlparams.update(dbtable.parseSerializedKey(pkey))
            pkey = None
        self.dbtable = dbtable
        self.pkey = pkey
        self.where = where
        self.relmodes = dict(lazy=lazy, eager=eager)
        self.relationDict = relationDict
        self.sqlparams = sqlparams or {}
        self.sqlparams.update(kwargs)
        self.joinConditions = joinConditions or {}
        self.sqlContextName = sqlContextName
        self.db = self.dbtable.db
        self._compiled = None
        self._result = None
        self.ignoreMissing = ignoreMissing
        self.ignoreDuplicate = ignoreDuplicate
        self.bagFields = bagFields
        self.for_update = for_update
        self.virtual_columns = virtual_columns
        self.storename = _storename
        self.checkPermissions = checkPermissions
        self.aliasPrefix = aliasPrefix or 't'


    def setJoinCondition(self, target_fld, from_fld, condition, one_one=False, **kwargs):
        """Register an extra join condition for a specific relation.

        Args:
            target_fld: Fully-qualified target field (``pkg.table.column``).
            from_fld: Fully-qualified source field.
            condition: SQL condition string (may reference ``$tbl``).
            one_one: If ``True``, treat a one-to-many relation as one-to-one.
            **kwargs: Additional bind parameters for the condition.
        """
        cond = dict(condition=condition, one_one=one_one, params=kwargs)
        self.joinConditions['%s_%s' % (target_fld.replace('.', '_'), from_fld.replace('.', '_'))] = cond

    def output(self, mode, **kwargs):
        """Dispatch to the appropriate ``out_<mode>`` method.

        Args:
            mode: One of ``'bag'``, ``'dict'``, ``'json'``, ``'record'``,
                ``'newrecord'``, ``'sample'``, ``'template'``.
            **kwargs: Extra arguments forwarded to the output method.

        Returns:
            The record data in the requested format.

        Raises:
            SelectionExecutionError: If *mode* does not match any
                ``out_<mode>`` method.
        """
        if hasattr(self, 'out_%s' % mode):
            return getattr(self, 'out_%s' % mode)(**kwargs)
        else:
            raise SelectionExecutionError('Not existing mode: %s' % mode)

    def _get_compiled(self):
        if self._compiled is None:
            self._compiled = self.compileQuery()
        return self._compiled

    compiled = property(_get_compiled)

    def compileQuery(self):
        """Build a ``SqlCompiledQuery`` for this record fetch.

        Determines the WHERE clause from ``pkey``, explicit ``where``, or
        ``sqlparams`` keys, then delegates to
        ``SqlQueryCompiler.compiledRecordQuery``.

        Returns:
            SqlCompiledQuery: The compiled query ready for execution.
        """
        if self.where:
            where = self.where
        elif self.pkey is not None:
            where = '$pkey = :pkey'
        else:
            where = ' AND '.join([f'"{self.aliasPrefix}0".{k}=:{k}' for k in self.sqlparams.keys() if self.dbtable.column(k) is not None])
        compiler = SqlQueryCompiler(self.dbtable.model, sqlparams=self.sqlparams,
                                  joinConditions=self.joinConditions,
                                  sqlContextName=self.sqlContextName,aliasPrefix=self.aliasPrefix)
        return compiler.compiledRecordQuery(where=where,relationDict=self.relationDict,bagFields=self.bagFields,
                                                for_update=self.for_update,virtual_columns=self.virtual_columns,
                                                **self.relmodes)

    def _get_result(self):
        if self._result is None:
            with self.db.tempEnv(currentImplementation=self.dbtable.dbImplementation):
                self.adapterResult()
        return self._result

    def adapterResult(self):
        """Execute the compiled query and store the single-row result.

        Handles three outcomes:

        - Exactly one row → stored as ``_result``.
        - Zero rows → raises ``RecordNotExistingError`` unless
          ``ignoreMissing`` is ``True``.
        - Multiple rows → tries to filter out logically-deleted duplicates;
          if still ambiguous, raises ``RecordDuplicateError`` unless
          ``ignoreDuplicate`` is ``True``.

        Raises:
            RecordSelectionError: If no WHERE clause is available.
            RecordNotExistingError: If no matching row is found.
            RecordDuplicateError: If more than one row matches.
        """
        if not self.compiled.where:
            raise RecordSelectionError(
                    "Insufficient parameters for selecting a record: %s" % (self.dbtable.fullname, ))
        params = self.sqlparams
        if self.pkey is not None:
            params['pkey'] = self.pkey
            # REVIEW: commented-out line ``raise '%s ...'`` -- debug leftover
        cursor = self.db.execute(self.compiled.get_sqltext(self.db), params, dbtable=self.dbtable.fullname,storename=self.storename)
        data = cursor.fetchall()
        index = cursor.index
        cursor.close()
        if self.compiled.explodingColumns and len(data)>1:
            data = self.aggregateRecords(data,index)
        if len(data) == 1:
            self._result = data[0]
        elif len(data) == 0:
            if self.ignoreMissing:
                self._result = Bag()
            else:
                raise RecordNotExistingError(
                        "No record found in table %s for selection %s %s" % (self.dbtable.fullname,
                                                                                self.compiled.get_sqltext(self.db),
                                                                                params))
        else:
            if self.dbtable.logicalDeletionField:
                data = [r for r in data if r['%s0_%s' %(self.aliasPrefix,self.dbtable.logicalDeletionField)] is None]
            if len(data) == 1:
                self._result = data[0]
            elif self.ignoreDuplicate:
                self._result = data[0]
            else:
                raise RecordDuplicateError(
                        "Found more than one record in table %s for selection %s %s" % (self.dbtable.fullname,
                                                                                        self.compiled.get_sqltext(
                                                                                                self.db), params))


    def aggregateRecords(self, data, index):
        """Collapse multiple rows into one when exploding columns are present.

        When a record query joins through a one-to-many relation, the
        result set may contain multiple rows for the same primary key.
        This method merges them by collecting the exploding-column values
        into lists, then calling ``dbtable.fieldAggregate`` on each.

        Args:
            data: List of row dicts from the cursor.
            index: Column-name → position mapping (currently unused).

        Returns:
            list: A single-element list containing the merged row dict.
        """
        # REVIEW: parameter ``index`` is never used in the method body
        # -- consider removing from signature.
        resultmap = self.compiled.resultmap
        mapdict = dict(resultmap.digest('#k,#a.as'))
        explodingColumns = [(mapdict[k],k) for k in self.compiled.explodingColumns]
        result = dict(data[0])
        for col,fld in explodingColumns:
            result[col] = [result[col]]
        for d in data[1:]:
            for col,fld in explodingColumns:
                result[col].append(d[col])
        for col,fld in explodingColumns:
            result[col] = self.dbtable.fieldAggregate(fld,result[col],fieldattr=resultmap.getAttr(fld))
        return [result]

    # REVIEW: _set_result ignores the ``result`` parameter and always
    # creates an empty Bag(). Seems intentional for ``out_newrecord`` and
    # ``out_sample`` which assign ``self.result = Bag(...)`` before
    # ``loadRecord``, but the setter does not propagate the value -- the
    # effect is that the getter will then run ``adapterResult``. Verify
    # whether this behaviour is truly desired or is a bug.
    def _set_result(self, result):
        self._result = Bag()

    result = property(_get_result, _set_result)

    def out_newrecord(self, resolver_one=True, resolver_many=True):
        """Build a new, empty record Bag with resolvers and default values.

        Args:
            resolver_one: Attach resolvers for one-to-one relations.
            resolver_many: Attach resolvers for one-to-many relations.

        Returns:
            SqlRecordBag: A record pre-populated with table default values.
        """
        result = SqlRecordBag(self.db, self.dbtable.fullname)
        self.result = Bag()
        self.loadRecord(result, resolver_many=resolver_many, resolver_one=resolver_one)

        newdefaults = self.dbtable.defaultValues()
        for k, v in list(newdefaults.items()):
            result[k] = v

        return result


    def out_sample(self, resolver_one=True, resolver_many=True, sample_kwargs=None):
        """Build a sample record Bag with resolvers and sample values.

        Useful for generating demo/test data or preview templates.

        Args:
            resolver_one: Attach resolvers for one-to-one relations.
            resolver_many: Attach resolvers for one-to-many relations.
            sample_kwargs: Optional dict of overrides applied after the
                sample values are loaded.

        Returns:
            SqlRecordBag: A record pre-populated with table sample values.
        """
        result = SqlRecordBag(self.db, self.dbtable.fullname)
        self.result = Bag(self.dbtable.sampleValues())
        self.loadRecord(result, resolver_many=resolver_many, resolver_one=resolver_one)
        if sample_kwargs:
            result.update(sample_kwargs)
        return result

    def out_bag(self, resolver_one=True, resolver_many=True):
        """Load the record into a ``SqlRecordBag`` with lazy resolvers.

        This is the primary output mode. Each scalar field becomes a Bag
        item; each relation becomes a node with a lazy resolver that
        fires on first access.

        Args:
            resolver_one: Attach resolvers for one-to-one/many-to-one
                relations.
            resolver_many: Attach resolvers for one-to-many relations.

        Returns:
            SqlRecordBag: The fully-populated record Bag.
        """
        result = SqlRecordBag(self.db, self.dbtable.fullname)
        if self.result is not None:
            self.loadRecord(result, resolver_many=resolver_many,resolver_one=resolver_one)
        return result


    def out_template(self, recordtemplate=None):
        """Render the record through a string template.

        Args:
            recordtemplate: A template string with ``$field`` placeholders.

        Returns:
            str: The template with placeholders replaced by field values.
        """
        record = Bag()
        self.loadRecord(record, resolver_many=True, resolver_one=True)
        return gnrstring.templateReplace(recordtemplate, record, safeMode=True)

    def out_record(self):
        """Load the record into a plain Bag (no lazy resolvers).

        Returns:
            Bag: The record data without relation resolvers.
        """
        result = Bag()
        if self.result:
            self.loadRecord(result,resolver_many=False, resolver_one=False)
        return result

    def out_json(self):
        """Serialize the record as a JSON string.

        Returns:
            str: JSON representation of the record dict.
        """
        return gnrstring.toJson(self.out_dict())

    def out_dict(self):
        """Return the record as a flat Python dict.

        Virtual columns backed by ``py_method`` handlers are evaluated
        and their results merged into the dict.

        Returns:
            dict: Field-name → value mapping (keys stripped of the
            ``t0_`` alias prefix).
        """
        pyColumnsDict = dict([(k,h) for k,h in self.compiled.pyColumns])
        result = dict([(str(k)[3:], self.result[k]) for k in list(self.result.keys())])
        for k,v in list(result.items()):
            result[k] =  pyColumnsDict[k](result,field=k) if k in pyColumnsDict else result[k]
        self._decryptRow(result)
        return result

    def loadRecord(self, result, resolver_one=None, resolver_many=None):
        """Populate *result* Bag from the SQL result and resultmap.

        Delegates to ``_loadRecord`` for field/relation traversal, then
        evaluates any ``pyColumns`` (Python-computed virtual columns).

        Args:
            result: The target Bag to populate.
            resolver_one: Attach one-side resolvers.
            resolver_many: Attach many-side resolvers.
        """
        self._loadRecord(result, self.result, self.compiled.resultmap,
                         resolver_one=resolver_one, resolver_many=resolver_many)
        if self.compiled.pyColumns:
            for field, handler in self.compiled.pyColumns:
                if handler:
                    result[field] = handler(result, field=field)
        self._decryptRow(result)

    def _decryptRow(self, row):
        """Decrypt encrypted fields in a row (dict or Bag), in place.

        Args:
            row: A dict or Bag object (modified in place).
        """
        encrypted = self.compiled.encryptedColumns
        if not encrypted:
            return
        app = getattr(self.db, 'application', None)
        encryptor = getattr(app, 'encryptor', None) if app else None
        if not encryptor:
            return
        encryptor.decrypt_row(row, encrypted)


    def _loadRecord_DynItemMany(self, joiner, info, sqlresult,
                                resolver_one, resolver_many, virtual_columns):
        """Build a lazy ``SqlRelatedSelectionResolver`` for a one-to-many relation.

        Args:
            joiner: Relation metadata dict from the resultmap.
            info: Mutable attribute dict for the Bag node.
            sqlresult: The raw SQL row data.
            resolver_one: Passed through (unused here).
            resolver_many: If truthy, create the resolver.
            virtual_columns: Virtual columns to propagate to the sub-query.

        Returns:
            tuple: ``(resolver_value, info_dict)``
        """
        # REVIEW: parameter ``resolver_one`` is unused in this method
        # -- consider removing or documenting if it is kept for signature
        # uniformity with the other _loadRecord_DynItem* methods.
        opkg, otbl, ofld = joiner['one_relation'].split('.')

        info['_from_fld'] = joiner['one_relation']
        info['_target_fld'] = joiner['many_relation']
        info['_onDelete'] = joiner.get('onDelete')
        info['_relation_value'] = sqlresult['%s0_%s' %(self.aliasPrefix,ofld)]
        target_fld = info['_target_fld']
        mpkg, mtbl, mrelated_field = target_fld.split('.')
        many_table = self.db.table('%s.%s' % (mpkg, mtbl))
        order_by = joiner.get('many_order_by') or many_table.attributes.get('order_by')
        sqlparams = dict()
        if order_by:
            sqlparams['order_by'] = order_by
        # REVIEW: the ``#if True or resolver_many is True:`` / ``#else:``
        # block is a vestige of an old toggle -- the code in the ``else``
        # branch is unreachable. Consider removing the commented-out code.
        value = SqlRelatedSelectionResolver(
                columns='*', db=self.db, cacheTime=-1,
                target_fld=target_fld,
                relation_value=info['_relation_value'],
                mode='grid', joinConditions=self.joinConditions,
                sqlContextName=self.sqlContextName,
                virtual_columns=virtual_columns,
                sqlparams=sqlparams)
        info['_many_order_by'] = order_by
        info['_sqlContextName'] = self.sqlContextName
        info['_resolver_name'] = resolver_many
        info['_virtual_columns'] = virtual_columns
        return value,info

    def _loadRecord_DynItemOneOne(self, joiner, info, sqlresult,
                                   resolver_one, resolver_many, virtual_columns):
        """Build a lazy ``SqlRelatedRecordResolver`` for a one-one (reverse) relation.

        Args:
            joiner: Relation metadata dict from the resultmap.
            info: Mutable attribute dict for the Bag node.
            sqlresult: The raw SQL row data.
            resolver_one: If truthy, create the resolver.
            resolver_many: Passed through (unused here).
            virtual_columns: Virtual columns to propagate.

        Returns:
            tuple: ``(resolver_value, info_dict)``
        """
        opkg, otbl, ofld = joiner['one_relation'].split('.')
        info['_from_fld'] = joiner['one_relation']
        info['_target_fld'] = joiner['many_relation']
        info['one_one'] = joiner['one_one']
        info['_onDelete'] = joiner.get('onDelete')
        # REVIEW: both branches of ``if joiner.get('virtual')`` produce
        # the exact same value -- the conditional is useless.
        if joiner.get('virtual'):
            relation_value = sqlresult['%s0_%s' %(self.aliasPrefix,ofld)]
        else:
            relation_value = sqlresult['%s0_%s' %(self.aliasPrefix,ofld)]
        # REVIEW: ``#if True or resolver_one is True:`` / ``#else:`` block
        # -- vestige of an old toggle, else branch unreachable.
        value = SqlRelatedRecordResolver(db=self.db, cacheTime=-1,
                                         target_fld=info['_target_fld'],
                                         relation_value=relation_value,
                                         mode='bag',
                                         bagFields=True,
                                         ignoreMissing=True,
                                         virtual_columns=virtual_columns,
                                         joinConditions=self.joinConditions,
                                         sqlContextName=self.sqlContextName)
        info['_resolver_name'] = resolver_one
        info['_sqlContextName'] = self.sqlContextName
        info['_relation_value'] = relation_value
        info['_virtual_columns'] = virtual_columns

        return value, info


    def _loadRecord_DynItemOne(self, joiner, info, sqlresult,
                                resolver_one, resolver_many, virtual_columns):
        """Build a lazy ``SqlRelatedRecordResolver`` for a many-to-one (FK) relation.

        Args:
            joiner: Relation metadata dict from the resultmap.
            info: Mutable attribute dict for the Bag node.
            sqlresult: The raw SQL row data.
            resolver_one: If truthy, create the resolver.
            resolver_many: Passed through (unused here).
            virtual_columns: Virtual columns to propagate.

        Returns:
            tuple: ``(resolver_value, info_dict)``
        """
        if joiner.get('eager_one'):
            info['_eager_one']=joiner['eager_one']
        mpkg, mtbl, mfld = joiner['many_relation'].split('.')
        info['_from_fld'] = joiner['many_relation']
        info['_target_fld'] = joiner['one_relation']
        relation_value = sqlresult['%s0_%s' %(self.aliasPrefix,mfld)]
        # REVIEW: ``#if True or resolver_one is True:`` / ``#else:`` block
        # -- vestige of an old toggle, else branch unreachable.
        value=SqlRelatedRecordResolver(db=self.db, cacheTime=-1,
                                             target_fld=info['_target_fld'],
                                             relation_value=relation_value,
                                             mode='bag', virtual_columns=virtual_columns,
                                             bagFields=True,
                                             ignoreMissing=True,
                                             joinConditions=self.joinConditions,
                                             sqlContextName=self.sqlContextName
                                             )
        #else:
        if 'storefield' in joiner:
            info['_storefield'] = joiner['storefield']
        if 'resolver_kwargs' in joiner:
            info['_resolver_kwargs'] = joiner['resolver_kwargs']
        info['_resolver_name'] = resolver_one
        info['_sqlContextName'] = self.sqlContextName
        info['_auto_relation_value'] = mfld
        info['_virtual_columns'] = virtual_columns
        info['_storename'] = joiner.get('_storename') or self.storename
        return value,info

    def _onChangedValueCb(self, node=None, evt=None, info=None, **kwargs):
        """Callback subscribed to FK field nodes to refresh the related resolver.

        When the FK value changes (``evt='upd_value'``), the corresponding
        ``@relation`` resolver is updated with the new value, triggering
        a reload on next access.
        """
        if evt == 'upd_value':
            rnode = node.parentbag.getNode('@%s' % node.label)
            if rnode and rnode.resolver:
                rnode.resolver(relation_value=node.value)

    def _loadRecord(self, result, sqlresult, fields, resolver_one=None, resolver_many=None):
        """Walk the *resultmap* and populate the target Bag.

        For each entry in *fields*:

        - **Scalar fields**: copy the value from ``sqlresult`` into *result*.
        - **Bag-type fields** (``dtype='X'``): wrap the value in a ``Bag``
          (or skip if ``bagFields`` is ``False``).
        - **Relation fields** (``_relmode`` present): delegate to the
          appropriate ``_loadRecord_DynItem*`` method and attach the
          resolver to the result Bag. For ``DynItemOne`` relations, also
          subscribe to FK value changes so the resolver is refreshed.

        Args:
            result: Target Bag to populate.
            sqlresult: Raw row data (dict-like) from the cursor.
            fields: ``resultmap`` Bag with field metadata attributes.
            resolver_one: Attach one-side (FK) resolvers.
            resolver_many: Attach many-side resolvers.
        """
        pending_subscribes = []
        for fieldname, args in list(fields.digest('#k,#a')):
            dtype = args.get('dtype')
            info = dict(args)
            joiner = info.pop('joiner',None)
            relmode = info.pop('_relmode',None)
            if relmode:
                info['mode'] = joiner['mode']
                if (relmode=='DynItemMany' and resolver_many) or (resolver_one and relmode in ('DynItemOneOne','DynItemOne')):
                    virtual_columns = self.virtual_columns
                    if virtual_columns:
                        virtual_columns = ','.join(
                            [vc.split('.', 1)[1] for vc in virtual_columns.split(',') if vc.startswith(fieldname)])
                    value, info = getattr(self,'_loadRecord_%s' %relmode)(joiner,info,sqlresult,resolver_one,resolver_many,virtual_columns)
                    result.setItem(fieldname, value, info)
                    if resolver_one and relmode =='DynItemOne':
                        if fieldname[1:] in result:
                            result.getNode(fieldname[1:]).subscribe('resolverChanged',self._onChangedValueCb)
                        else:
                            pending_subscribes.append(fieldname[1:])
            else:
                value = sqlresult['%s0_%s' %(self.aliasPrefix,fieldname)]
                if dtype == 'X':
                    if self.bagFields:
                        value = Bag(value)
                    else:
                        continue

                result.setItem(fieldname, value, info)
        for pending in pending_subscribes:
            result.getNode(pending).subscribe('resolverChanged',self._onChangedValueCb)


class SqlRecordBag(Bag):
    """Bag subclass that holds a single-record snapshot and can save itself.

    Extends ``Bag`` with a convenience ``save()`` method that inserts or
    updates the record in the database depending on ``isNew``.

    Attributes:
        db: Reference to the ``GnrSqlDb`` instance.
        tablename: Fully-qualified table name (``pkg.table``).
        isNew: If ``True``, ``save()`` will INSERT; otherwise UPDATE.
    """
    def __init__(self, db=None, tablename=None):
        """Initialize the record bag.

        Args:
            db: The ``GnrSqlDb`` instance.
            tablename: Fully-qualified table name.
        """
        Bag.__init__(self)
        self.db = db
        self.tablename = tablename
        self.isNew = True

    def save(self, **kwargs):
        """Persist the record to the database.

        If ``isNew`` is ``True``, performs an INSERT and flips the flag.
        Otherwise performs an UPDATE.

        Args:
            **kwargs: Field=value pairs merged into the Bag before saving.
        """
        for k, v in list(kwargs.items()):
            self[k] = v
        if self.isNew:
            self.db.table(self.tablename).insert(self)
            self.isNew = False
        else:
            self.db.table(self.tablename).update(self)

    # REVIEW: _set_db/_get_db contain commented-out weakref code.
    # In the past ``db`` was probably a weakref to avoid GC cycles;
    # currently it is a direct strong reference. Evaluate whether the
    # cycle SqlRecordBag -> db -> table -> ... -> SqlRecordBag exists
    # and whether restoring the weakref would be appropriate.
    def _set_db(self, db):
        if db is None:
            self._db = db
        else:
            self._db = db

    def _get_db(self):
        if self._db:
            return self._db

    db = property(_get_db, _set_db)


# ===========================================================================
# REVIEW NOTES (record.py)
# ===========================================================================
#
# 1. REVIEW: resolverSerialize() duplicated
#    SqlRelatedRecordResolver.resolverSerialize() and
#    SqlRelatedSelectionResolver.resolverSerialize() have nearly identical
#    bodies (pop 'db', add '_serialized_app_db'). Consider extracting
#    into a ``_SerializableResolverMixin`` or shared helper method.
#
# 2. REVIEW: _set_result ignores the parameter
#    The ``SqlRecord.result`` setter receives a ``result`` parameter but
#    always creates an empty ``Bag()``. This means that
#    ``self.result = Bag(self.dbtable.sampleValues())`` in ``out_sample``
#    does NOT store the sample values -- it works only because the getter
#    calls ``adapterResult()`` which overwrites ``_result``. Side effect:
#    ``out_newrecord`` and ``out_sample`` execute an unnecessary query
#    if ``_result`` was None.
#
# 3. REVIEW: truthiness on pkey in __init__
#    ``if pkey and len(dbtable.pkeys)>1`` fails for pkey=0 (int)
#    or pkey='' (empty string). Using ``if pkey is not None`` would be
#    more robust.
#
# 4. REVIEW: _loadRecord_DynItemOneOne -- identical branches
#    The conditional ``if joiner.get('virtual'): ... else: ...``
#    executes exactly the same code in both branches. Probably the
#    ``virtual`` branch had different logic in the past; it is now
#    redundant.
#
# 5. REVIEW: commented-out code ``#if True or resolver_one/many is True:``
#    Present in _loadRecord_DynItemMany, _loadRecord_DynItemOneOne, and
#    _loadRecord_DynItemOne. Was a toggle to enable/disable resolvers;
#    the ``else`` branch is no longer reachable. The commented-out code
#    can be removed.
#
# 6. REVIEW: commented-out weakref in SqlRecordBag._set_db/_get_db
#    The ``weakref.ref(db)`` and ``self._db()`` code is commented out.
#    Evaluate whether reference cycles are a practical problem.
#
# 7. REVIEW: unused parameter ``index`` in aggregateRecords
#    The ``index`` parameter is never read in the method body.
#
# 8. REVIEW: unused parameters ``resolver_one``/``resolver_many``
#    In _loadRecord_DynItemMany ``resolver_one`` is ignored;
#    in _loadRecord_DynItemOneOne/One ``resolver_many`` is ignored.
#    Probably kept for signature uniformity, but documenting this
#    explicitly would improve clarity.
# ===========================================================================
