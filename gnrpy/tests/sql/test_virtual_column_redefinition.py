from gnr.sql.gnrsql import GnrSqlDb

from .common import configureDb


class RedefiningCastMixin(object):
    def config_db(self, pkg):
        tbl = pkg.table('cast')
        tbl.aliasColumn('alias_to_formula', '@person_id.name')
        tbl.formulaColumn('alias_to_formula', "'from_formula'")
        tbl.formulaColumn('formula_to_alias', "'from_formula'")
        tbl.aliasColumn('formula_to_alias', '@person_id.name')
        tbl.aliasColumn('relabeled', '@person_id.name', name_long='Old label')
        tbl.virtual_column('relabeled', name_long='New label')


class TestVirtualColumnRedefinition:
    @classmethod
    def setup_class(cls):
        cls.db = GnrSqlDb()
        configureDb(cls.db)
        cls.db.tableMixin('video.cast', RedefiningCastMixin())
        cls.db.startup()

    def vc_attributes(self, name):
        return self.db.packageSrc('video').table('cast').getAttr('virtual_columns.%s' % name)

    def sqltext(self, column):
        return self.db.table('video.cast').query(columns='$%s' % column, limit=1).sqltext

    def test_alias_redefined_as_formula(self):
        attrs = self.vc_attributes('alias_to_formula')
        assert 'relation_path' not in attrs
        assert attrs['sql_formula'] == "'from_formula'"
        sql = self.sqltext('alias_to_formula')
        assert "'from_formula'" in sql
        assert 'people' not in sql

    def test_formula_redefined_as_alias(self):
        attrs = self.vc_attributes('formula_to_alias')
        assert 'sql_formula' not in attrs
        assert attrs['relation_path'] == '@person_id.name'
        sql = self.sqltext('formula_to_alias')
        assert "'from_formula'" not in sql
        assert 'people' in sql

    def test_relabel_keeps_kind(self):
        attrs = self.vc_attributes('relabeled')
        assert attrs['relation_path'] == '@person_id.name'
        assert attrs['name_long'] == 'New label'
        assert 'people' in self.sqltext('relabeled')
