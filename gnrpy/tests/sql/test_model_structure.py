# -*- coding: utf-8 -*-
"""Exhaustive structural tests for gnrsqlmodel.

Tests ALL public methods and properties of:
- DbTableObj (table.py)
- DbColumnObj, DbVirtualColumnObj, AliasColumnWrapper (columns.py)
- DbModelObj, DbPackageObj (obj.py)
- DbModel (model.py)
- RelationTreeResolver (resolvers.py)
- Containers (containers.py)
- Helpers (helpers.py)

Uses the test_invoice project (SQLite) as the real model.
"""

import os
import tempfile

import pytest
from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsql_exceptions import GnrSqlMissingTable
from gnr.sql.gnrsqlmodel.columns import AliasColumnWrapper
from core.common import BaseGnrAppTest

class TestModelStructure(BaseGnrAppTest):
    app_name = 'test_invoice'

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = cls.app.db
        
# ===================================================================
# 1. DbTableObj — Basic properties
# ===================================================================

class TestTableProperties(TestModelStructure):
    
    def test_fullname(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.fullname == 'invc.customer'

    def test_pkg_name(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.pkg.name == 'invc'

    def test_pkey_id(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.pkey == 'id'

    def test_pkey_code(self):
        tbl = self.db.model.table('invc.state')
        assert tbl.pkey == 'code'

    def test_pkeys(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.pkeys == ['id']

    def test_sqlname(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.sqlname == 'invc_customer'

    def test_sqlfullname_contains_sqlname(self):
        tbl = self.db.model.table('invc.customer')
        assert 'invc_customer' in tbl.sqlfullname

    def test_sqlschema(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.sqlschema == 'invc'

    def test_rowcaption_with_caption_field(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.rowcaption == '$account_name'

    def test_name_plural(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.name_plural == '!!Customers'

    def test_draftField(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.draftField == '__is_draft'

    def test_logicalDeletionField(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.logicalDeletionField == '__del_ts'

    def test_lastTS(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.lastTS == '__mod_ts'

    def test_maintable_none_for_regular_table(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.maintable is None

    def test_multi_tenant_none(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.multi_tenant is None

    def test_name(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.name == 'customer'

    def test_name_long(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.name_long == '!!Customer'

    def test_adapted_sqlname(self):
        tbl = self.db.model.table('invc.customer')
        assert 'invc_customer' in tbl.adapted_sqlname

    def test_noChangeMerge_empty(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.noChangeMerge == ''

    def test_newrecord_caption(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.newrecord_caption == '!!Customer'


# ===================================================================
# 2. DbTableObj — Physical columns
# ===================================================================

class TestTableColumns(TestModelStructure):

    def test_columns_not_none(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.columns is not None

    def test_columns_has_account_name(self):
        tbl = self.db.model.table('invc.customer')
        assert 'account_name' in tbl.columns

    def test_columns_has_id(self):
        tbl = self.db.model.table('invc.customer')
        assert 'id' in tbl.columns

    def test_columns_has_system_fields(self):
        tbl = self.db.model.table('invc.customer')
        for fld in ('__ins_ts', '__del_ts', '__mod_ts', '__ins_user', '__is_draft'):
            assert fld in tbl.columns

    def test_column_resolve_physical(self):
        tbl = self.db.model.table('invc.customer')
        col = tbl.column('account_name')
        assert col is not None
        assert col.dtype == 'T'

    def test_column_resolve_pkey(self):
        tbl = self.db.model.table('invc.customer')
        col = tbl.column('id')
        assert col is not None

    def test_column_resolve_relation_path(self):
        tbl = self.db.model.table('invc.customer')
        col = tbl.column('@state.name')
        assert col is not None

    def test_column_resolve_alias(self):
        tbl = self.db.model.table('invc.customer')
        col = tbl.column('state_name')
        assert col is not None
        assert isinstance(col, AliasColumnWrapper)
        assert col.relation_path == '@state.name'

    def test_column_nonexistent_returns_none(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.column('NONEXISTENT_COLUMN_XYZ') is None

    def test_column_with_dollar_prefix(self):
        tbl = self.db.model.table('invc.customer')
        col = tbl.column('$account_name')
        assert col is not None

    def test_starColumns_returns_list(self):
        tbl = self.db.model.table('invc.customer')
        stars = tbl.starColumns()
        assert isinstance(stars, list)
        assert len(stars) == 16
        assert all(s.startswith('$') for s in stars)

    def test_pluggedColumns(self):
        tbl = self.db.model.table('invc.customer')
        plugged = tbl.pluggedColumns()
        assert isinstance(plugged, list)


# ===================================================================
# 3. DbTableObj — Virtual columns
# ===================================================================

class TestTableVirtualColumns(TestModelStructure):

    def test_virtual_columns_not_none(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.virtual_columns is not None

    def test_formula_with_select(self):
        tbl = self.db.model.table('invc.customer')
        assert 'n_invoices' in tbl.virtual_columns

    def test_formula_with_sql_formula(self):
        tbl = self.db.model.table('invc.customer')
        assert 'full_address' in tbl.virtual_columns

    def test_formula_with_exists(self):
        tbl = self.db.model.table('invc.customer')
        assert 'has_invoices' in tbl.virtual_columns

    def test_alias_column(self):
        tbl = self.db.model.table('invc.customer')
        assert 'state_name' in tbl.virtual_columns

    def test_py_column(self):
        tbl = self.db.model.table('invc.customer')
        assert 'customer_score' in tbl.virtual_columns

    def test_join_column(self):
        tbl = self.db.model.table('invc.invoice')
        assert 'discount_tier_id' in tbl.virtual_columns

    def test_bag_item_column(self):
        tbl = self.db.model.table('invc.product')
        assert 'detail_weight' in tbl.virtual_columns
        assert 'detail_color' in tbl.virtual_columns

    def test_getVirtualColumn_found(self):
        tbl = self.db.model.table('invc.customer')
        vc = tbl.getVirtualColumn('n_invoices')
        assert vc is not None

    def test_getVirtualColumn_not_found(self):
        tbl = self.db.model.table('invc.customer')
        with pytest.raises(AttributeError):
            tbl.getVirtualColumn('NONEXISTENT_VC_XYZ')

    def test_virtualColumnAttributes_alias(self):
        tbl = self.db.model.table('invc.customer')
        vca = tbl.virtualColumnAttributes('state_name')
        assert isinstance(vca, dict)
        assert vca['relation_path'] == '@state.name'

    def test_static_virtual_columns(self):
        tbl = self.db.model.table('invc.invoice_row')
        svc = tbl.static_virtual_columns
        assert isinstance(svc, Bag)
        assert 'invoice_date_static' in svc

    def test_composite_columns(self):
        tbl = self.db.model.table('invc.customer')
        cc = tbl.composite_columns
        assert isinstance(cc, Bag)

    def test_dynamic_columns(self):
        tbl = self.db.model.table('invc.customer')
        dc = tbl.dynamic_columns
        assert isinstance(dc, Bag)
        assert '__allowed_for_partition' in dc

    def test_full_virtual_columns(self):
        """full_virtual_columns requires PostgreSQL (customVirtualColumns uses string_to_array).
        On SQLite we verify it raises OperationalError."""
        import sqlite3
        tbl = self.db.model.table('invc.customer')
        try:
            fvc = tbl.full_virtual_columns
            # If it works (PostgreSQL), verify content
            assert fvc is not None
            assert 'n_invoices' in fvc
        except sqlite3.OperationalError:
            pytest.skip('full_virtual_columns requires PostgreSQL')


# ===================================================================
# 4. DbTableObj — Relations and navigation
# ===================================================================

class TestTableRelations(TestModelStructure):

    def test_relations_is_bag(self):
        tbl = self.db.model.table('invc.customer')
        assert isinstance(tbl.relations, Bag)

    def test_relations_has_physical_columns(self):
        rels = self.db.model.table('invc.customer').relations
        assert 'id' in rels
        assert 'account_name' in rels
        assert 'state' in rels

    def test_relations_has_fk_relation(self):
        rels = self.db.model.table('invc.customer').relations
        assert '@state' in rels

    def test_relations_has_reverse_relation(self):
        rels = self.db.model.table('invc.customer').relations
        assert '@invoices' in rels

    def test_relations_fk_invoice_customer(self):
        rels = self.db.model.table('invc.invoice').relations
        assert '@customer_id' in rels

    def test_relations_join_column(self):
        rels = self.db.model.table('invc.invoice').relations
        assert '@discount_tier_id' in rels

    def test_relations_virtual_without_fk_not_present(self):
        rels = self.db.model.table('invc.customer').relations
        assert 'n_invoices' not in rels
        assert 'full_address' not in rels
        assert 'has_invoices' not in rels

    def test_relations_virtual_with_fk_present(self):
        rels = self.db.model.table('invc.customer').relations
        assert '@last_invoice_id' in rels

    def test_relations_nested_is_bag(self):
        rels = self.db.model.table('invc.invoice').relations
        nested = rels['@customer_id']
        assert isinstance(nested, Bag)
        assert 'account_name' in nested

    def test_relations_one(self):
        tbl = self.db.model.table('invc.invoice')
        ro = tbl.relations_one
        assert isinstance(ro, Bag)
        assert 'customer_id' in ro

    def test_relations_one_keys(self):
        tbl = self.db.model.table('invc.invoice')
        keys = list(tbl.relations_one.keys())
        assert 'customer_id' in keys
        assert 'first_product_id' in keys
        assert 'discount_tier_id' in keys

    def test_relations_many(self):
        tbl = self.db.model.table('invc.customer')
        rm = tbl.relations_many
        assert isinstance(rm, Bag)
        assert 'invc_invoice_customer_id' in rm

    def test_relatingColumns(self):
        tbl = self.db.model.table('invc.customer')
        rc = tbl.relatingColumns
        assert isinstance(rc, list)
        assert 'invc.invoice.customer_id' in rc

    def test_getRelation(self):
        tbl = self.db.model.table('invc.invoice')
        r = tbl.getRelation('@customer_id')
        assert r == {'many': 'invc.invoice.customer_id', 'one': 'invc.customer.id'}

    def test_getRelationBlock(self):
        tbl = self.db.model.table('invc.invoice')
        rb = tbl.getRelationBlock('@customer_id')
        assert rb['mode'] == 'O'
        assert rb['mpkg'] == 'invc'
        assert rb['mtbl'] == 'invoice'
        assert rb['mfld'] == 'customer_id'
        assert rb['opkg'] == 'invc'
        assert rb['otbl'] == 'customer'
        assert rb['ofld'] == 'id'

    def test_getJoiner(self):
        tbl = self.db.model.table('invc.invoice')
        j = tbl.getJoiner('invc.customer')
        assert j is not None
        assert j['mode'] == 'O'
        assert j['many_relation'] == 'invc.invoice.customer_id'
        assert j['one_relation'] == 'invc.customer.id'
        assert j['foreignkey'] is True

    def test_getJoiner_not_found(self):
        tbl = self.db.model.table('invc.invoice')
        j = tbl.getJoiner('invc.region')
        assert j is None

    def test_manyRelationsList(self):
        tbl = self.db.model.table('invc.customer')
        mrl = tbl.manyRelationsList()
        assert ('invc.invoice', 'customer_id') in mrl

    def test_manyRelationsList_cascadeOnly(self):
        tbl = self.db.model.table('invc.customer')
        mrl = tbl.manyRelationsList(cascadeOnly=True)
        assert isinstance(mrl, list)
        assert ('invc.invoice', 'customer_id') not in mrl

    def test_manyRelationsList_cascade_exists(self):
        tbl = self.db.model.table('invc.invoice')
        mrl = tbl.manyRelationsList(cascadeOnly=True)
        assert ('invc.invoice_note', 'invoice_id') in mrl
        assert ('invc.invoice_row', 'invoice_id') in mrl

    def test_oneRelationsList(self):
        tbl = self.db.model.table('invc.invoice')
        orl = tbl.oneRelationsList()
        assert ('invc.customer', 'id', 'customer_id') in orl

    def test_oneRelationsList_foreignkeyOnly(self):
        tbl = self.db.model.table('invc.invoice')
        orl = tbl.oneRelationsList(foreignkeyOnly=True)
        assert ('invc.customer', 'id', 'customer_id') in orl
        virtual_rels = [r for r in orl if r[2] == 'first_product_id']
        assert len(virtual_rels) == 0

    def test_dependencies(self):
        tbl = self.db.model.table('invc.invoice')
        deps = tbl.dependencies
        assert isinstance(deps, list)
        assert ('invc.customer', False) in deps

    def test_resolveRelationPath_direct(self):
        tbl = self.db.model.table('invc.invoice')
        assert tbl.resolveRelationPath('@customer_id') == '@customer_id'

    def test_fullRelationPath_simple(self):
        tbl = self.db.model.table('invc.customer')
        result = tbl.fullRelationPath('@state.name')
        assert result == '@state.name'

    def test_getTableJoinerPath(self):
        tbl = self.db.model.table('invc.customer')
        paths = tbl.getTableJoinerPath('invc.invoice')
        assert isinstance(paths, list)
        assert len(paths) >= 1


# ===================================================================
# 5. DbTableObj — Subtables and table aliases
# ===================================================================

class TestTableSubtablesAliases(TestModelStructure):

    def test_subtables_exist(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.subtables is not None
        keys = list(tbl.subtables.keys())
        assert 'residential' in keys
        assert 'commercial' in keys
        assert 'government' in keys
        assert 'trade' in keys

    def test_subtable_lookup(self):
        tbl = self.db.model.table('invc.customer')
        sub = tbl.subtable('residential')
        assert sub is not None
        assert sub.attributes['condition'] == "$customer_type_code = 'RES'"

    def test_subtable_getCondition(self):
        tbl = self.db.model.table('invc.customer')
        sub = tbl.subtable('residential')
        params = {}
        cond = sub.getCondition(sqlparams=params)
        assert "$customer_type_code" in cond

    def test_table_aliases_not_none(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.table_aliases is not None


# ===================================================================
# 6. DbTableObj — Serialization
# ===================================================================

class TestTableSerialization(TestModelStructure):

    def test_toJson_structure(self):
        tbl = self.db.model.table('invc.customer')
        j = tbl.toJson()
        assert j['code'] == 'customer'
        assert j['pkey'] == 'id'
        assert isinstance(j['columns'], list)
        assert len(j['columns']) > 0

    def test_toJson_column_entry(self):
        tbl = self.db.model.table('invc.customer')
        j = tbl.toJson()
        codes = [c['code'] for c in j['columns']]
        assert 'account_name' in codes

    def test_bagItemFormula(self):
        tbl = self.db.model.table('invc.product')
        kwargs = {}
        result = tbl.bagItemFormula(
            bagcolumn='$details', itempath='specs.weight', dtype='N', kwargs=kwargs
        )
        assert isinstance(result, str)
        assert 'xpath' in result
        assert 'numeric' in result
        assert 'var_calculated_path' in kwargs
        assert kwargs['var_calculated_path'] == '/GenRoBag/specs/weight/text()'


# ===================================================================
# 7. DbColumnObj — Properties
# ===================================================================

class TestColumnObj(TestModelStructure):

    def test_dtype_text(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.dtype == 'T'

    def test_dtype_date(self):
        col = self.db.model.table('invc.invoice').column('date')
        assert col.dtype == 'D'

    def test_dtype_money(self):
        col = self.db.model.table('invc.invoice').column('total')
        assert col.dtype == 'N'

    def test_sqlname(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.sqlname == 'account_name'

    def test_sqlfullname(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert 'invc_customer' in col.sqlfullname
        assert 'account_name' in col.sqlfullname

    def test_fullname(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.fullname == 'invc.customer.account_name'

    def test_readonly_false(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.readonly is False

    def test_isReserved_false(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.isReserved is False

    def test_isReserved_true(self):
        col = self.db.model.table('invc.invoice').column('customer_id')
        assert col.isReserved is True

    def test_pkg_name(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.pkg.name == 'invc'

    def test_table_name(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.table.name == 'customer'

    def test_getTag(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.getTag() == 'column'

    def test_relatedTable_fk(self):
        col = self.db.model.table('invc.invoice').column('customer_id')
        rt = col.relatedTable()
        assert rt is not None
        assert rt.fullname == 'invc.customer'

    def test_relatedColumn_fk(self):
        col = self.db.model.table('invc.invoice').column('customer_id')
        rc = col.relatedColumn()
        assert rc is not None
        assert rc.fullname == 'invc.customer.id'

    def test_relatedColumnJoiner_fk(self):
        col = self.db.model.table('invc.invoice').column('customer_id')
        j = col.relatedColumnJoiner()
        assert j is not None
        assert j['many_relation'] == 'invc.invoice.customer_id'
        assert j['one_relation'] == 'invc.customer.id'

    def test_relatedTable_non_fk(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.relatedTable() is None

    def test_relatedColumn_non_fk(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.relatedColumn() is None

    def test_relatedColumnJoiner_non_fk(self):
        col = self.db.model.table('invc.customer').column('account_name')
        assert col.relatedColumnJoiner() is None

    def test_toJson(self):
        col = self.db.model.table('invc.customer').column('account_name')
        j = col.toJson()
        assert j['code'] == 'account_name'
        assert j['name'] == '!!Account name'
        assert j['dtype'] == 'T'
        assert j['column_class'] == 'column'

    def test_toJson_fk_has_related_to(self):
        col = self.db.model.table('invc.invoice').column('customer_id')
        j = col.toJson()
        assert j['related_to'] == 'invc.customer.id'


# ===================================================================
# 8. DbVirtualColumnObj — Properties
# ===================================================================

class TestVirtualColumnObj(TestModelStructure):
    
    def test_alias_relation_path(self):
        vc = self.db.model.table('invc.customer').virtual_columns['state_name']
        assert vc.relation_path == '@state.name'
        assert vc.sql_formula is None
        assert vc.select is None
        assert vc.exists is None
        assert vc.py_method is None

    def test_formula_sql_formula(self):
        vc = self.db.model.table('invc.customer').virtual_columns['full_address']
        assert vc.sql_formula == "$street_address || ', ' || $suburb"
        assert vc.relation_path is None

    def test_formula_select(self):
        vc = self.db.model.table('invc.customer').virtual_columns['n_invoices']
        assert vc.select == {
            'table': 'invc.invoice',
            'columns': 'COUNT(*)',
            'where': '$customer_id=#THIS.id',
        }

    def test_formula_exists(self):
        vc = self.db.model.table('invc.customer').virtual_columns['has_invoices']
        assert vc.exists == {
            'table': 'invc.invoice',
            'where': '$customer_id=#THIS.id',
        }

    def test_py_method(self):
        vc = self.db.model.table('invc.customer').virtual_columns['customer_score']
        assert vc.py_method == 'pyColumn_customer_score'

    def test_join_column(self):
        vc = self.db.model.table('invc.invoice').virtual_columns['discount_tier_id']
        assert vc.join_column is True

    def test_readonly_always_true(self):
        vc = self.db.model.table('invc.customer').virtual_columns['n_invoices']
        assert vc.readonly is True

    def test_getTag(self):
        vc = self.db.model.table('invc.customer').virtual_columns['n_invoices']
        assert vc.getTag() == 'virtual_column'


# ===================================================================
# 9. AliasColumnWrapper
# ===================================================================

class TestAliasColumnWrapper(TestModelStructure):

    def test_wrapper_type(self):
        col = self.db.model.table('invc.customer').column('state_name')
        assert isinstance(col, AliasColumnWrapper)

    def test_wrapper_relation_path(self):
        col = self.db.model.table('invc.customer').column('state_name')
        assert col.relation_path == '@state.name'

    def test_wrapper_delegates_attributes(self):
        col = self.db.model.table('invc.customer').column('state_name')
        assert 'name_long' in col.attributes


# ===================================================================
# 10. DbPackageObj — Properties
# ===================================================================

class TestPackageObj(TestModelStructure):
    
    def test_tables_not_none(self):
        pkg = self.db.model.package('invc')
        assert pkg.tables is not None

    def test_tables_has_customer(self):
        pkg = self.db.model.package('invc')
        assert 'customer' in pkg.tables

    def test_table_lookup(self):
        pkg = self.db.model.package('invc')
        tbl = pkg.table('customer')
        assert tbl is not None
        assert tbl.fullname == 'invc.customer'

    def test_table_missing_raises(self):
        pkg = self.db.model.package('invc')
        with pytest.raises(GnrSqlMissingTable):
            pkg.table('NONEXISTENT_TABLE_XYZ')

    def test_dbtable_proxy(self):
        pkg = self.db.model.package('invc')
        dbt = pkg.dbtable('customer')
        assert dbt is not None
        assert dbt.fullname == 'invc.customer'

    def test_sqlschema(self):
        pkg = self.db.model.package('invc')
        assert pkg.sqlschema == 'invc'

    def test_tableSqlName(self):
        pkg = self.db.model.package('invc')
        tbl = pkg.table('customer')
        assert pkg.tableSqlName(tbl) == 'invc_customer'

    def test_toJson(self):
        pkg = self.db.model.package('invc')
        j = pkg.toJson()
        assert j['code'] == 'invc'
        assert isinstance(j['tables'], list)
        codes = [t['code'] for t in j['tables']]
        assert 'customer' in codes


# ===================================================================
# 11. DbModel — Navigation
# ===================================================================

class TestDbModel(TestModelStructure):

    def test_package_found(self):
        pkg = self.db.model.package('invc')
        assert pkg is not None

    def test_package_not_found(self):
        pkg = self.db.model.package('NONEXISTENT_PKG')
        assert pkg is None

    def test_table_dotted(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl is not None
        assert tbl.fullname == 'invc.customer'

    def test_table_with_pkg(self):
        tbl = self.db.model.table('customer', pkg='invc')
        assert tbl is not None
        assert tbl.fullname == 'invc.customer'

    def test_column_dotted(self):
        col = self.db.model.column('invc.customer.account_name')
        assert col is not None
        assert col.fullname == 'invc.customer.account_name'

    def test_model_relations_lookup(self):
        rels = self.db.model.relations('invc.customer')
        assert rels is not None
        keys = list(rels.keys())
        assert '@state' in keys
        assert '@invoices' in keys

    def test_model_relations_invoice(self):
        rels = self.db.model.relations('invc.invoice')
        keys = list(rels.keys())
        assert '@customer_id' in keys
        assert '@rows' in keys
        assert '@notes' in keys


# ===================================================================
# 12. RelationTreeResolver — Structure (via relations)
# ===================================================================

class TestRelationTreeResolver(TestModelStructure):

    def test_resolver_creates_bag(self):
        tbl = self.db.model.table('invc.customer')
        resolver = tbl.newRelationResolver()
        result = resolver()
        assert isinstance(result, Bag)

    def test_relations_keys_match(self):
        tbl = self.db.model.table('invc.customer')
        expected_physical = ['id', '__ins_ts', '__del_ts', '__mod_ts',
                             '__ins_user', '__is_draft', 'account_name',
                             'street_address', 'suburb', 'state', 'postcode',
                             'customer_type_code', 'payment_type_code',
                             'notes', 'email', 'phone']
        rels = tbl.relations
        for col in expected_physical:
            assert col in rels, f'{col} not in relations'

    def test_relations_fk_entries(self):
        rels = self.db.model.table('invc.customer').relations
        for fk in ('@state', '@customer_type_code', '@payment_type_code'):
            assert fk in rels, f'{fk} not in relations'

    def test_relations_reverse_entries(self):
        rels = self.db.model.table('invc.customer').relations
        assert '@invoices' in rels
        assert '@invoice_rows_by_customer' in rels

    def test_relations_joiner_attribute(self):
        rels = self.db.model.table('invc.invoice').relations
        attrs = rels.getAttr('@customer_id')
        assert attrs is not None
        joiner = attrs['joiner']
        assert joiner['mode'] == 'O'
        assert joiner['one_relation'] == 'invc.customer.id'
        assert joiner['many_relation'] == 'invc.invoice.customer_id'

    def test_relations_nested_navigation(self):
        rels = self.db.model.table('invc.invoice').relations
        cust_bag = rels['@customer_id']
        assert isinstance(cust_bag, Bag)
        assert 'account_name' in cust_bag
        assert 'email' in cust_bag

    def test_virtual_fk_in_relations(self):
        rels = self.db.model.table('invc.customer').relations
        assert '@last_invoice_id' in rels

    def test_virtual_non_fk_not_in_relations(self):
        rels = self.db.model.table('invc.customer').relations
        for vc_name in ('n_invoices', 'full_address', 'has_invoices',
                         'customer_rank', 'customer_score'):
            assert vc_name not in rels, f'{vc_name} should not be in relations'


# ===================================================================
# 13. DbModelObj base — Common properties
# ===================================================================

class TestDbModelObjBase(TestModelStructure):

    def test_dbroot(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.dbroot is self.db

    def test_db_property(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.db is self.db

    def test_adapter(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.adapter is not None

    def test_getTag_table(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.getTag() == 'table'

    def test_getAttr_single(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.getAttr('pkey') == 'id'

    def test_getAttr_default(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.getAttr('nonexistent_attr', 'fallback') == 'fallback'

    def test_getAttr_full_dict(self):
        tbl = self.db.model.table('invc.customer')
        attrs = tbl.getAttr()
        assert isinstance(attrs, dict)
        assert 'pkey' in attrs

    def test_name_short(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.name_short is not None

    def test_name_full(self):
        tbl = self.db.model.table('invc.customer')
        assert tbl.name_full is not None

    def test_bool_always_true(self):
        tbl = self.db.model.table('invc.customer')
        assert bool(tbl) is True


# ===================================================================
# 14. Containers
# ===================================================================

class TestContainers(TestModelStructure):

    def test_index_sqlname(self):
        tbl = self.db.model.table('invc.customer')
        idx_keys = list(tbl.indexes.keys())
        assert len(idx_keys) >= 1
        first_idx = tbl.indexes[idx_keys[0]]
        assert 'idx' in first_idx.sqlname

    def test_index_table(self):
        tbl = self.db.model.table('invc.customer')
        idx_keys = list(tbl.indexes.keys())
        first_idx = tbl.indexes[idx_keys[0]]
        assert first_idx.table.name == 'customer'

    def test_index_for_fk_column(self):
        tbl = self.db.model.table('invc.customer')
        assert 'customer_state_key' in tbl.indexes

    def test_subtable_getCondition_with_params(self):
        tbl = self.db.model.table('invc.customer')
        sub = tbl.subtable('residential')
        params = {}
        cond = sub.getCondition(sqlparams=params)
        assert '$customer_type_code' in cond


# ===================================================================
# 15. Helpers
# ===================================================================

class TestHelpers(TestModelStructure):

    def test_bagItemFormula_text(self):
        from gnr.sql.gnrsqlmodel.helpers import bagItemFormula
        kw = {}
        result = bagItemFormula(bagcolumn='$details', itempath='a.b', dtype='T', kwargs=kw)
        assert 'xpath' in result
        assert 'var_calculated_path' in kw
        assert kw['var_calculated_path'] == '/GenRoBag/a/b/text()'

    def test_bagItemFormula_numeric(self):
        from gnr.sql.gnrsqlmodel.helpers import bagItemFormula
        kw = {}
        result = bagItemFormula(bagcolumn='$details', itempath='x.y', dtype='N', kwargs=kw)
        assert 'numeric' in result

    def test_bagItemFormula_positional_index(self):
        from gnr.sql.gnrsqlmodel.helpers import bagItemFormula
        kw = {}
        bagItemFormula(bagcolumn='$col', itempath='#0.item', dtype='T', kwargs=kw)
        assert '*[1]' in kw['var_calculated_path']

    def test_bagItemFormula_xml_attribute(self):
        from gnr.sql.gnrsqlmodel.helpers import bagItemFormula
        kw = {}
        bagItemFormula(bagcolumn='$col', itempath='a.b?myattr', dtype='T', kwargs=kw)
        assert '@myattr' in kw['var_calculated_path']

    def test_toolFormula(self):
        from gnr.sql.gnrsqlmodel.helpers import toolFormula
        kw = {'name_long': 'My Tool'}
        result = toolFormula('mytool', dtype='T', kwargs=kw)
        assert '_tools/mytool' in result
        assert '<a' in result

    def test_toolFormula_image(self):
        from gnr.sql.gnrsqlmodel.helpers import toolFormula
        kw = {}
        result = toolFormula('mytool', dtype='P', kwargs=kw)
        assert '<img' in result


# ===================================================================
# 16. Cross-table relation consistency
# ===================================================================

class TestCrossTableConsistency(TestModelStructure):

    def test_fk_chain_customer_invoice_row_product(self):
        inv = self.db.model.table('invc.invoice')
        inv_row = self.db.model.table('invc.invoice_row')
        assert inv.getJoiner('invc.customer') is not None
        assert inv_row.getJoiner('invc.invoice') is not None
        assert inv_row.getJoiner('invc.product') is not None

    def test_fk_chain_customer_state_region(self):
        cust = self.db.model.table('invc.customer')
        state = self.db.model.table('invc.state')
        assert cust.getJoiner('invc.state') is not None
        assert state.getJoiner('invc.region') is not None

    def test_joiner_symmetry(self):
        """Verify joiner from invoice to customer is consistent:
        invoice.customer_id FK -> customer.id"""
        inv = self.db.model.table('invc.invoice')
        j_inv = inv.getJoiner('invc.customer')
        assert j_inv['many_relation'] == 'invc.invoice.customer_id'
        assert j_inv['one_relation'] == 'invc.customer.id'
        assert j_inv['foreignkey'] is True

    def test_joiner_reverse_via_joincolumn(self):
        """customer.getJoiner('invc.invoice') finds the joinColumn last_invoice_id,
        not the FK customer_id"""
        cust = self.db.model.table('invc.customer')
        j_cust = cust.getJoiner('invc.invoice')
        assert j_cust['many_relation'] == 'invc.customer.last_invoice_id'
        assert j_cust['one_relation'] == 'invc.invoice.id'
        assert j_cust['foreignkey'] is False

    def test_relations_one_many_coherence(self):
        inv = self.db.model.table('invc.invoice')
        cust = self.db.model.table('invc.customer')
        assert 'customer_id' in inv.relations_one
        cust_many = cust.relations_many
        assert 'invc_invoice_customer_id' in cust_many

    def test_all_tables_have_pkey(self):
        pkg = self.db.model.package('invc')
        for tbl_name, tbl_obj in pkg.tables.items():
            assert tbl_obj.pkey, f'{tbl_name} has no pkey'

    def test_all_fk_columns_have_relation(self):
        inv = self.db.model.table('invc.invoice')
        fk_col = inv.column('customer_id')
        assert fk_col.relatedColumnJoiner() is not None
        assert fk_col.relatedTable().fullname == 'invc.customer'

    def test_deep_alias_resolves(self):
        inv_row = self.db.model.table('invc.invoice_row')
        col = inv_row.column('customer_region')
        assert col is not None
