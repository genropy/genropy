#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_record : SQL record and resolvers
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

from gnr.core import gnrstring
from gnr.core.gnrbag import Bag, BagResolver
from gnr.sql.gnrsqldata.compiler import SqlQueryCompiler
from gnr.sql.gnrsql_exceptions import SelectionExecutionError, RecordDuplicateError, \
    RecordNotExistingError, RecordSelectionError


class SqlRelatedRecordResolver(BagResolver):
    """TODO"""
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

    def resolverSerialize(self):
        """TODO"""
        attr = {}
        attr['resolvermodule'] = self.__class__.__module__
        attr['resolverclass'] = self.__class__.__name__
        attr['args'] = list(self._initArgs)
        attr['kwargs'] = dict(self._initKwargs)
        attr['kwargs'].pop('db')
        attr['kwargs']['_serialized_app_db'] = 'maindb'
        return attr

    def load(self):
        """TODO"""
        pkg, tbl, related_field = self.target_fld.split('.')
        dbtable = '%s.%s' % (pkg, tbl)
        recordpars = dict()
        recordpars[str(related_field)] = self.relation_value
        if self.parentNode.attr.get('_storefield'):
            recordpars['_storename'] = self.parentNode.parentbag[self.parentNode.attr.get('_storefield')]
        record = SqlRecord(self.db.table(dbtable), joinConditions=self.joinConditions,
                           sqlContextName=self.sqlContextName,
                           ignoreMissing=self.ignoreMissing, ignoreDuplicate=self.ignoreDuplicate,
                           virtual_columns=self.virtual_columns,
                           bagFields=self.bagFields, **recordpars)
        return record.output(self.mode)


class SqlRelatedSelectionResolver(BagResolver):
    """TODO"""
    classKwargs = {'cacheTime': 0, 'readOnly': True, 'db': None,
                   'columns': None, 'mode': None, 'sqlparams': None, 'joinConditions': None, 'sqlContextName': None,
                   'target_fld': None, 'relation_value': None, 'condition': None, 'bagFields': None,'virtual_columns':None}

    def resolverSerialize(self):
        """TODO"""
        attr = {}
        attr['resolvermodule'] = self.__class__.__module__
        attr['resolverclass'] = self.__class__.__name__
        attr['args'] = list(self._initArgs)
        attr['kwargs'] = dict(self._initKwargs)
        attr['kwargs'].pop('db')
        attr['kwargs']['_serialized_app_db'] = 'maindb'
        return attr

    def load(self):
        """TODO"""
        pkg, tbl, related_field = self.target_fld.split('.')
        dbtable = '%s.%s' % (pkg, tbl)
        query = self.db.table(dbtable).relatedQuery(field=related_field,value=self.relation_value,where=self.condition,
                                                    sqlContextName=self.sqlContextName, **self.sqlparams)
        return query.selection().output(self.mode, recordResolver=(self.mode == 'grid'),virtual_columns=self.virtual_columns)

class SqlRecord(object):
    """TODO"""
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
        """TODO

        :param target_fld: TODO
        :param from_fld: TODO
        :param condition: set a :ref:`sql_condition` for the join
        :param one_one: boolean. TODO"""
        cond = dict(condition=condition, one_one=one_one, params=kwargs)
        self.joinConditions['%s_%s' % (target_fld.replace('.', '_'), from_fld.replace('.', '_'))] = cond

    def output(self, mode, **kwargs):
        """TODO

        :param mode: TODO"""
        if hasattr(self, 'out_%s' % mode):
            return getattr(self, 'out_%s' % mode)(**kwargs) #calls the output method
        else:
            raise SelectionExecutionError('Not existing mode: %s' % mode)

    def _get_compiled(self):
        if self._compiled is None:
            self._compiled = self.compileQuery()
        return self._compiled

    compiled = property(_get_compiled)

    def compileQuery(self):
        """TODO"""
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
        if not self.compiled.where:
            raise RecordSelectionError(
                    "Insufficient parameters for selecting a record: %s" % (self.dbtable.fullname, ))
        params = self.sqlparams
        if self.pkey is not None:
            params['pkey'] = self.pkey
            #raise '%s \n\n%s' % (str(params), str(self.compiled.get_sqltext(self.db)))
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


    def aggregateRecords(self,data,index):
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

    def _set_result(self,result):
        self._result = Bag()

    result = property(_get_result,_set_result)

    def out_newrecord(self, resolver_one=True, resolver_many=True):
        """TODO

        :param resolver_one: boolean. TODO
        :param resolver_many: boolean. TODO"""
        result = SqlRecordBag(self.db, self.dbtable.fullname)
        self.result = Bag()
        self.loadRecord(result, resolver_many=resolver_many, resolver_one=resolver_one)

        newdefaults = self.dbtable.defaultValues()
        for k, v in list(newdefaults.items()):
            result[k] = v

        return result


    def out_sample(self, resolver_one=True, resolver_many=True,sample_kwargs=None):
        """TODO

        :param resolver_one: boolean. TODO
        :param resolver_many: boolean. TODO"""
        result = SqlRecordBag(self.db, self.dbtable.fullname)
        self.result = Bag(self.dbtable.sampleValues())
        self.loadRecord(result, resolver_many=resolver_many, resolver_one=resolver_one)
        if sample_kwargs:
            result.update(sample_kwargs)
        return result

    def out_bag(self, resolver_one=True, resolver_many=True):
        """TODO

        :param resolver_one: boolean. TODO
        :param resolver_many: boolean. TODO"""
        result = SqlRecordBag(self.db, self.dbtable.fullname)
        if self.result is not None:
            self.loadRecord(result, resolver_many=resolver_many,resolver_one=resolver_one)
        return result


    def out_template(self,recordtemplate=None):
        record=Bag()
        self.loadRecord(record,resolver_many=True, resolver_one=True)
        return gnrstring.templateReplace(recordtemplate,record,safeMode=True)

    def out_record(self):
        """TODO"""
        result = Bag()
        if self.result:
            self.loadRecord(result,resolver_many=False, resolver_one=False)
        return result

    def out_json(self):
        """TODO"""
        return gnrstring.toJson(self.out_dict())

    def out_dict(self):
        """TODO"""
        pyColumnsDict = dict([(k,h) for k,h in self.compiled.pyColumns])
        result = dict([(str(k)[3:], self.result[k]) for k in list(self.result.keys())])
        for k,v in list(result.items()):
            result[k] =  pyColumnsDict[k](result,field=k) if k in pyColumnsDict else result[k]
        return result

    def loadRecord(self,result,resolver_one=None,resolver_many=None):
        self._loadRecord(result,self.result,self.compiled.resultmap,resolver_one=resolver_one,resolver_many=resolver_many)
        if self.compiled.pyColumns:
            for field,handler in self.compiled.pyColumns:
                if handler:
                    result[field] = handler(result,field=field)


    def _loadRecord_DynItemMany(self,joiner,info,sqlresult,resolver_one,resolver_many,virtual_columns):
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
        #if True or resolver_many is True:
        value = SqlRelatedSelectionResolver(
                columns='*', db=self.db, cacheTime=-1,
                target_fld=target_fld,
                relation_value=info['_relation_value'],
                mode='grid', joinConditions=self.joinConditions,
                sqlContextName=self.sqlContextName,
                virtual_columns=virtual_columns,
                sqlparams = sqlparams)
        #else:
        info['_many_order_by'] = order_by
        info['_sqlContextName'] = self.sqlContextName
        info['_resolver_name'] = resolver_many
        info['_virtual_columns'] = virtual_columns
        return value,info

    def _loadRecord_DynItemOneOne(self,joiner,info,sqlresult,resolver_one,resolver_many,virtual_columns):
        opkg, otbl, ofld = joiner['one_relation'].split('.')
        info['_from_fld'] = joiner['one_relation']
        info['_target_fld'] = joiner['many_relation']
        info['one_one'] = joiner['one_one']
        info['_onDelete'] = joiner.get('onDelete')
        if joiner.get('virtual'):
            relation_value = sqlresult['%s0_%s' %(self.aliasPrefix,ofld)]
        else:
            relation_value = sqlresult['%s0_%s' %(self.aliasPrefix,ofld)]
        #if True or resolver_one is True:
        value = SqlRelatedRecordResolver(db=self.db, cacheTime=-1,
                                         target_fld=info['_target_fld'],
                                         relation_value=relation_value,
                                         mode='bag',
                                         bagFields=True,
                                         ignoreMissing=True,
                                         virtual_columns=virtual_columns,
                                         joinConditions=self.joinConditions,
                                         sqlContextName=self.sqlContextName)
        #else:
        info['_resolver_name'] = resolver_one
        info['_sqlContextName'] = self.sqlContextName
        info['_relation_value'] = relation_value
        info['_virtual_columns'] = virtual_columns

        return value,info


    def _loadRecord_DynItemOne(self,joiner,info,sqlresult,resolver_one,resolver_many,virtual_columns):
        if joiner.get('eager_one'):
            info['_eager_one']=joiner['eager_one']
        mpkg, mtbl, mfld = joiner['many_relation'].split('.')
        info['_from_fld'] = joiner['many_relation']
        info['_target_fld'] = joiner['one_relation']
        relation_value = sqlresult['%s0_%s' %(self.aliasPrefix,mfld)]
        #if True or resolver_one is True:
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

    def _onChangedValueCb(self,node=None,evt=None,info=None,**kwargs):
        if evt=='upd_value':
            rnode = node.parentbag.getNode('@%s' %node.label)
            if rnode and rnode.resolver:
                rnode.resolver(relation_value=node.value)

    def _loadRecord(self, result, sqlresult,fields, resolver_one=None, resolver_many=None):
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
    """TODO"""
    def __init__(self, db=None, tablename=None):
        Bag.__init__(self)
        self.db = db
        self.tablename = tablename
        self.isNew = True

    def save(self, **kwargs):
        """TODO"""
        for k, v in list(kwargs.items()):
            self[k] = v
        if self.isNew:
            self.db.table(self.tablename).insert(self)
            self.isNew = False
        else:
            self.db.table(self.tablename).update(self)

    def _set_db(self, db):
        if db is None:
            self._db = db
        else:
            #self._db = weakref.ref(db)
            self._db = db

    def _get_db(self):
        if self._db:
            #return self._db()
            return self._db

    db = property(_get_db, _set_db)
