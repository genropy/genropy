#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_compiler : SQL query compiler
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
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
    """SqlCompiledQuery is a private class used by the :class:`SqlQueryCompiler` class.
       It is used to store all parameters needed to compile a query string."""

    def __init__(self, maintable, relationDict=None,maintable_as=None):
        """Initialize the SqlCompiledQuery class

        :param maintable: the name of the main table to query. For more information, check the
                          :ref:`maintable` section.
        :param relationDict: a dict to assign a symbolic name to a :ref:`relation`. For more information
                             check the :ref:`relationdict` documentation section"""
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
        """Compile the sql query string based on current query parameters and the specific db
        adapter for the current db in use.

        :param db: am instance of the :class:`GnrSqlDb <gnr.sql.gnrsql.GnrSqlDb>` class"""
        kwargs = {}
        for k in (
        'maintable', 'distinct', 'columns', 'joins', 'where', 'group_by', 'having', 'order_by', 'limit', 'offset',
        'for_update'):
            kwargs[k] = getattr(self, k)
        return db.adapter.compileSql(maintable_as=self.maintable_as,**kwargs)



class SqlQueryCompiler(object):
    """SqlQueryCompiler is a private class used by SqlQuery and SqlRecord to build an SqlCompiledQuery instance.

    The ``__init__`` method passes:

    :param tblobj: the main table to query: an instance of SqlTable, you can get it using db.table('pkgname.tablename')
    :param joinConditions: special conditions for joining related tables. See the
                           :meth:`setJoinCondition() <gnr.sql.gnrsqldata.SqlQuery.setJoinCondition()>`
                           method
    :param sqlContextName: the name of the sqlContext to be reported for subsequent related selection.
                            (see the
                           :meth:`setJoinCondition() <gnr.web.gnrwebpage.GnrWebPage.setJoinCondition>` method)
    :param sqlparams: a dict of parameters used in "WHERE" clause
    :param locale: the current locale (e.g: en, en_us, it)"""
    def __init__(self, tblobj, joinConditions=None, sqlContextName=None, sqlparams=None, locale=None,aliasPrefix = None):
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

    def aliasCode(self,n):
        return '%s%i' %(self.aliasPrefix,n)


    def init(self, lazy=None, eager=None):
        """TODO

        :param lazy: TODO.
        :param eager: TODO.
        """
        self._explodingRows = False
        self._explodingTables = []
        self.lazy = lazy or []
        self.eager = eager or []
        self.aliases = {self.tblobj.sqlfullname: self.aliasCode(0)}
        self.fieldlist = []

    def getFieldAlias(self, fieldpath, curr=None,basealias=None, parent=None):
        """Internal method. Translate fields path and related fields path in a valid sql string for the column.

        It translates ``@relname.@rel2name.colname`` to ``t4.colname``.

        It has nothing to do with the AS operator, nor the name of the output columns.

        It automatically adds the join tables as needed.

        It can be recursive to resolve :ref:`table_virtualcolumn`s.

        :param fieldpath: a field path. (e.g: '$colname'; e.g: '@relname.@rel2name.colname')
        :param curr: TODO.
        :param basealias: TODO. """

        def expandThis(m):
            fld = m.group(1)
            return self.getFieldAlias(fld,curr=curr,basealias=alias)

        def expandPref(m):
            """#PREF(myprefpath,default)"""
            prefpath = m.group(1)
            dflt=m.group(2)[1:] if m.group(2) else None
            return str(curr_tblobj.pkg.getPreference(prefpath,dflt))

        def expandEnv(m):
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
                env_tblobj = curr_tblobj
            handler = getattr(env_tblobj, 'env_%s' % what, None)
            if handler:
                return handler()
            else:
                return 'Not found %s' % what
        pathlist = fieldpath.split('.')
        fld = pathlist.pop()
        curr = curr or self.relations
        newpath = []
        basealias = basealias or self.aliasCode(0)
        if pathlist:
            alias, curr = self._findRelationAlias(list(pathlist), curr, basealias, newpath, parent=parent)
        else:
            alias = basealias
        curr_tblobj = self.db.table(curr.tbl_name, pkg=curr.pkg_name)
        if not fld in curr.keys():
            fldalias = curr_tblobj.model.getVirtualColumn(fld,sqlparams=self.sqlparams)
            if fldalias == None:
                raise GnrSqlMissingField('Missing field %s in table %s.%s (requested field %s)' % (
                fld, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))
            elif fldalias.relation_path and not fldalias.composed_of:

                # call getFieldAlias recursively
                return self.getFieldAlias(fldalias.relation_path, curr=curr,
                                          basealias=alias, parent='.'.join(pathlist))

                ### FIXME: refs #120 - left to support investigation
                #pathlist.append(fldalias.relation_path)
                #newfieldpath = '.'.join(pathlist)        # replace the field alias with the column relation_path
                # then call getFieldAlias again with the real path
                #return self.getFieldAlias(f"{'.'.join(pathlist)}.{fldalias.relation_path}", #curr=curr,
                #                                          basealias=basealias), #parent='.'.join(pathlist))  # call getFieldAlias recursively


            elif fldalias.sql_formula or fldalias.select or fldalias.exists:
                sql_formula = fldalias.sql_formula
                attr = dict(fldalias.attributes)
                if sql_formula is True:
                    sql_formula = getattr(curr_tblobj,'sql_formula_%s' %fld)(attr)
                select_dict = dictExtract(attr,'select_')
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
                sql_formula = self.macro_expander.replace(sql_formula,'TSRANK,TSHEADLINE')
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
                #self.cpl.pyColumns.append((fld,getattr(self.tblobj.dbtable,fldalias.py_method,None)))
                self.cpl.pyColumns.append((fld,getattr(fldalias.table.dbtable,fldalias.py_method,None)))
                return 'NULL'
            else:
                raise GnrSqlMissingColumn('Invalid column %s in table %s.%s (requested field %s)' % (
                fld, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))
        return '%s.%s' % (self.db.adapter.asTranslator(alias), curr_tblobj.column(fld).adapted_sqlname)

    def _findRelationAlias(self, pathlist, curr, basealias, newpath, parent=None):
        """Internal method: called by getFieldAlias to get the alias (t1, t2...) for the join table.
        It is recursive to resolve paths like ``@rel.@rel2.@rel3.column``"""
        p = pathlist.pop(0)
        currNode = curr.getNode(p)
        if not currNode:
            raise GnrSqlMissingField(f"Relation {p} not found")
        joiner = currNode.attr['joiner']
        if joiner == None:
            tblalias = self.db.table(curr.tbl_name, pkg=curr.pkg_name).model.table_aliases[p]
            if tblalias == None:
                #DUBBIO: non esiste più GnrSqlBadRequest
                #from gnr.sql.gnrsql import
                #raise GnrSqlBadRequest('Missing field %s in requested field %s' % (p, fieldpath))
                raise GnrSqlMissingField('Missing field %s in table %s.%s (requested field %s)' % (
                p, curr.pkg_name, curr.tbl_name, '.'.join(newpath)))
            else:
                pathlist = tblalias.relation_path.split(
                        '.') + pathlist # set the alias table relation_path in the current path
        else:                                                           # then call _findRelationAlias recursively
            alias, newpath = self._getRelationAlias(currNode, newpath, basealias, parent=parent)
            basealias = alias
            curr = curr[p]
        if pathlist:
            alias, curr = self._findRelationAlias(pathlist, curr, basealias, newpath, parent=f"{parent}.{p}" if parent else p)
        return alias, curr

    #def _getJoinerCnd(self, joiner):

    def _getRelationAlias(self, relNode, path, basealias, parent=None):
        """Internal method: returns the alias (t1, t2...) for the join table of the current relation.
        If the relation is traversed for the first time, it builds the join clause.
        Here case_insensitive relations and joinConditions are addressed.

        :param attrs: TODO
        :param path: TODO
        :param basealias: TODO"""
        #ref = attrs['many_relation'].split('.')[-1]
        joiner = relNode.attr['joiner']
        ref = joiner['many_relation'].split('.', 1)[-1] #fix 25-11-09
        newpath = path + [ref]
        pw = tuple(newpath+[basealias])
        if pw in self.aliases: # if the requested join table is yet added by previous columns
            if pw in self._explodingTables:
                if not self._currColKey in self.cpl.explodingColumns:
                    self.cpl.explodingColumns.append(self._currColKey)
            return self.aliases[pw], newpath # return the joint table alias
       # alias = '%s%i' % (self.aliasPrefix,len(self.aliases))    # else add it to the join clauses
        alias = self.aliasCode(len(self.aliases))
        self.aliases[pw] = alias
        manyrelation = False
        if joiner['mode'] == 'O':
            target_tbl = self.dbmodel.table(joiner['one_relation'])
            target_column = joiner['one_relation'].split('.')[-1]
            from_tbl = self.dbmodel.table(joiner['many_relation'])
            from_column = joiner['many_relation'].split('.')[-1]
        else:
            target_tbl = self.dbmodel.table(joiner['many_relation'])
            target_column = joiner['many_relation'].split('.')[-1]
            from_tbl = self.dbmodel.table(joiner['one_relation'])
            from_column = joiner['one_relation'].split('.')[-1]
            manyrelation = not joiner.get('one_one', False)
        #target_sqlschema = target_tbl.sqlschema
        #target_sqltable = target_tbl.sqlname
        ignore_tenant = joiner.get('ignore_tenant')
        target_sqlfullname = target_tbl._get_sqlfullname(ignore_tenant=ignore_tenant)
        joinerList = []
        target_sqlcolumn = None
        from_sqlcolumn = from_tbl.sqlnamemapper[from_column] if not joiner.get('virtual') else None
        if from_sqlcolumn:
            joinerList.append((from_sqlcolumn,target_tbl.sqlnamemapper[target_column]))
        elif from_tbl.column(from_column).attributes.get('composed_of'):
            from_columns = from_tbl.column(from_column).composed_of
            target_columns = target_tbl.column(target_column).composed_of
            if not target_columns:
                raise  GnrSqlException('Relation with multikey works only with compositeColumns')
            target_sqlcolumns = [target_tbl.sqlnamemapper[tc] for tc in target_columns.split(',')]
            joinerList = list(zip([from_tbl.sqlnamemapper[from_column] for from_column in from_columns.split(',')], target_sqlcolumns))
        else:
            target_sqlcolumn = target_tbl.sqlnamemapper[target_column]
        joindict = dict()
        adaptedAlias = self.db.adapter.adaptSqlName(alias)
        adaptedBaseAlias = self.db.adapter.adaptSqlName(basealias)
        if 'join_on' in joiner:
            joiner['cnd'] = joiner['join_on']
        if joiner.get('cnd'):
            cnd = joiner.get('cnd')
            cnd = BETWEENFINDER.sub(self.expandBetween, cnd)
            #cnd = self.updateFieldDict(joiner['cnd'], reldict=joindict)
        elif joiner.get('between'):
            # TODO: Depreacate: use #BETWEEN instead
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
            cnd = f'lower({adaptedAlias}.{target_sqlcolumn}) = lower({adaptedBaseAlias}.{from_sqlcolumn})'
        elif joinerList:
            cnd = ' AND '.join([f'({adaptedBaseAlias}.{from_column})={adaptedAlias}.{target_sqlcolumn}' for from_column,target_sqlcolumn in joinerList])
        elif joiner.get('virtual'):
            cnd = f'(${from_column})={adaptedAlias}.{target_sqlcolumn}'
        if parent:
            cnd =COLRELFINDER.sub(lambda g:f'{parent}.'+g.group(0).replace('$',''),cnd)
        cnd = self.updateFieldDict(cnd, reldict=joindict)
        if joindict:
            for f in joindict.values():
                self.getFieldAlias(f)
            self.cpl.relationDict.update(joindict)
        if self.joinConditions:
            from_fld, target_fld = self._tablesFromRelation(joiner)
            extracnd, one_one = self.getJoinCondition(target_fld, from_fld, alias,relation=relNode.label)
            if extracnd:
                extracnd = self.embedFieldPars(extracnd)
                extracnd = self.updateFieldDict(extracnd)
                cnd = '(%s AND %s)' % (cnd, extracnd)
                if one_one:
                    manyrelation = False # if in the model a relation is defined as one_one
        self.cpl.joins.append(f'LEFT JOIN {target_sqlfullname} AS {self.db.adapter.adaptSqlName(alias)} ON ({cnd})')
        # if a relation many is traversed the number of returned rows are more of the rows in the main table.
        # the columns causing the increment of rows number are saved for use by SqlSelection._aggregateRows
        if manyrelation:
            if not self._currColKey in self.cpl.explodingColumns:
                self.cpl.explodingColumns.append(self._currColKey)
            self._explodingTables.append(pw)
            self._explodingRows = True
        return alias, newpath

    def getJoinCondition(self, target_fld, from_fld, alias,relation=None):
        """Internal method:  get optional condition for a join clause from the joinConditions dict.

        A joinCondition is a dict containing:

        * *condition*: the condition as a WHERE clause, the columns of the target table are referenced as $tbl.colname
        * *params*: a dict of params used in the condition clause
        * *one_one*: ``True`` if a many relation becomes a one relation due to the condition

        :param target_fld: TODO
        :param from_fld: TODO
        :param alias: TODO"""
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
        """Internal method: search for columns or related columns in a string, add found columns to
        the relationDict (reldict) and replace related columns (``@rel.colname``) with a symbolic name
        like ``$_rel_colname``. Return a string containing only columns expressed in the form ``$colname``,
        so the found relations can be converted in sql strings (see :meth:`getFieldAlias()` method) and
        replaced into the returned string with templateReplace (see :meth:`compiledQuery()`).

        :param teststring: TODO
        :param reldict: a dict of custom names for db columns: {'asname':'@relation_name.colname'}"""
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
        """Internal method: return a list of columns from a fake column starting with ``*``

        :param flt: it can be:

                    * ``*``: returns all columns of the current table
                    * ``*prefix_``: returns all columns of the current table starting with ``prefix_``
                    * ``*@rel1.@rel2``: returns all columns of rel2 target table
                    * ``*@rel1.@rel2.prefix_``: returns all columns of rel2 target table starting with ``prefix_``

        :param bagFields: boolean. If ``True``, include fields of type Bag (``X``) when columns is ``*`` or contains
                          ``*@relname.filter``."""
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

    def embedFieldPars(self,sql):
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
        """Prepare the SqlCompiledQuery to get the sql query for a selection.

        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        :param where: the sql "WHERE" clause. For more information check the :ref:`sql_where` section
        :param order_by: corresponding to the sql "ORDER BY" operator. For more information check the
                         :ref:`sql_order_by` section
        :param distinct: boolean, ``True`` for getting a "SELECT DISTINCT"
        :param limit: number of result's rows. Corresponding to the sql "LIMIT" operator. For more
                      information, check the :ref:`sql_limit` section
        :param offset: the same of the sql "OFFSET"
        :param group_by: the sql "GROUP BY" clause. For more information check the :ref:`sql_group_by` section
        :param having: the sql "HAVING" clause. For more information check the :ref:`sql_having`
        :param for_update: boolean. If ``True``, lock the selected records of the main table (SELECT ... FOR UPDATE OF ...)
        :param relationDict: a dict to assign a symbolic name to a :ref:`relation`. For more information
                             check the :ref:`relationdict` documentation section
        :param bagFields: boolean. If ``True``, include fields of Bag type (``X``) when the ``columns``
                          parameter is ``*`` or contains ``*@relname.filter``
        :param count: boolean. If ``True``, optimize the sql query to get the number of resulting rows
                      (like count(*))
        :param excludeLogicalDeleted: boolean. If ``True``, exclude from the query all the records that are
                                      "logical deleted"
        :param excludeDraft: TODO
        :param addPkeyColumn: boolean. If ``True``, add a column with the pkey attribute"""
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
        if distinct:
            distinct = 'DISTINCT '
        elif distinct is None or distinct == '':
            if self._explodingRows:
                if not aggregate:              # if there is not yet a group_by
                    distinct = 'DISTINCT '     # add a DISTINCT to remove unusefull rows: eg. a JOIN used only for a where, not for columns
                    if order_by:
                        xorderby= gnrstring.split((('%s '%order_by.lower()).replace(' ascending ','').replace(' descending ','').replace(' asc ','').replace(' desc','')),',')
                        lowercol=columns.lower()
                        for i,xrd in enumerate(xorderby):
                            if not xrd.strip() in lowercol:
                                columns = '%s, \n%s AS __ord_col_%s' % (columns, xrd,i)
                    #order_by=None
                    if count:
                        columns = '%s.%s' % (self.aliasCode(0),self.tblobj.pkey)
                        # Count the DISTINCT maintable pkeys, instead of count(*) which will give the number of JOIN rows.
                        # That gives the count of rows on the main table: the result is different from the actual number
                        # of rows returned by the query, but it is correct in terms of main table records.
                        # It is the right behaviour ???? Yes in some cases: see SqlSelection._aggregateRows
        self.cpl.distinct = distinct
        self.cpl.columns = self.macro_expander.replace(columns,'TSRANK,TSHEADLINE')
        self.cpl.where = where
        self.cpl.group_by = group_by
        self.cpl.having = having
        self.cpl.order_by = self.macro_expander.replace(order_by,'TSRANK')
        self.cpl.limit = limit
        self.cpl.offset = offset
        self.cpl.for_update = for_update
        #raise str(self.cpl.get_sqltext(self.db))  # uncomment it for hard debug
        return self.cpl

    def compiledRecordQuery(self, lazy=None, eager=None, where=None,
                            bagFields=True, for_update=False, relationDict=None, virtual_columns=None):
        """Prepare the :class:`SqlCompiledQuery` class to get the sql query for a selection.

        :param lazy: TODO.
        :param eager: TODO.
        :param where: the sql "WHERE" clause. For more information check the :ref:`sql_where` section.

        :param bagFields: boolean, True to include fields of type Bag (``X``) when columns is * or contains *@relname.filter
        :param for_update: TODO
        :param relationDict: a dict to assign a symbolic name to a :ref:`relation`. For more information
                             check the :ref:`relationdict` documentation section
        :param virtual_columns: TODO."""
        self.cpl = SqlCompiledQuery(self.tblobj.sqlfullname, relationDict=relationDict)
        if 'pkey' not in self.cpl.relationDict and self.tblobj.pkey:
            self.cpl.relationDict['pkey'] = self.tblobj.pkey
        self.init(lazy=lazy, eager=eager)
        colPars = {}
        joindict = {}
        virtual_columns = virtual_columns or []
        virtual_columns = virtual_columns or []
        if isinstance(virtual_columns, str):
            virtual_columns = gnrstring.splitAndStrip(virtual_columns, ',')
        for fieldname, value, attrs in self.relations.digest('#k,#v,#a'):
            xattrs = {k:v for k, v in attrs.items() if not k in ['tag', 'comment', 'table', 'pkg']}
            #if not (bagFields or (attrs.get('dtype') != 'X')):
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
            self.cpl.resultmap.setItem(fieldname,None,xattrs)
        self._handle_virtual_columns(virtual_columns)
        self.cpl.where = self._recordWhere(where=where)
        self.cpl.columns = ',\n       '.join(self.fieldlist)
        self.cpl.for_update = for_update
        for key, value in list(joindict.items()):
            colPars[key] = self.getFieldAlias(value)
        self.cpl.joins = [gnrstring.templateReplace(j, colPars) for j in self.cpl.joins]

        return self.cpl


    def _getRelationMode(self,joiner):
        if joiner['mode'] == 'O':
            return 'DynItemOne'
        isOneOne=joiner.get('one_one')
        if not isOneOne and self.joinConditions:
            from_fld, target_fld = self._tablesFromRelation(joiner)
            extracnd, isOneOne = self.getJoinCondition(target_fld, from_fld, '%s0' %self.aliasPrefix)
        return 'DynItemOneOne' if isOneOne else 'DynItemMany'


    def _handle_virtual_columns(self, virtual_columns):
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
                pass
            xattrs['as'] = as_name
            self.fieldlist.append('%s AS %s' % (field, as_name))
            self.cpl.resultmap.setItem(path_name, None, xattrs)
            #self.cpl.dicttemplate[path_name] = as_name

    def expandBag(self, m):
        fld = m.group(1)
        asfld = m.group(3)
        self.cpl.evaluateBagColumns.append(((asfld or fld).replace('$',''),False))
        return fld if not asfld else '{} AS {}'.format(fld, asfld)

    def expandBagcols(self, m):
        fld = m.group(1)
        asfld = m.group(3)
        self.cpl.evaluateBagColumns.append(((asfld or fld).replace('$',''),True))
        return fld if not asfld else '{} AS {}'.format(fld, asfld)

    def expandBetween(self, m):
        # SQL  ... #BETWEEN($dataLavoro,$dataInizioValidita,$dataFineValidita) ...
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
        #TODO: verificare se inclusivo o meno su intervallo superiore
        return result

    def expandPeriod(self, m):
        """TODO

        :param m: TODO"""
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

    def _recordWhere(self, where=None): # usato da record resolver e record getter
        if where:
            self.updateFieldDict(where)
            colPars = {}
            for key, value in list(self.cpl.relationDict.items()):
                colPars[key] = self.getFieldAlias(value)
            where = gnrstring.templateReplace(where, colPars)
        return where

    def _tablesFromRelation(self, attrs):
        if attrs['mode'] == 'O':
            target_fld = attrs['one_relation']
            from_fld = attrs['many_relation']
        else:
            target_fld = attrs['many_relation']
            from_fld = attrs['one_relation']
        return from_fld, target_fld
