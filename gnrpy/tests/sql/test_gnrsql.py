from gnr.sql import gnrsql as gs
from .common import BaseGnrSqlTest, configurePackage

class TestGnrSql(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = gs.GnrSqlDb()

    def test_dbpar(self):
        r = self.db.dbpar("$HOME")
        assert r.startswith("/")

        r = self.db.dbpar(None)
        assert r is None

    def test_properties(self):
        assert self.db.debug is None
        assert not self.db.dbstores
        assert self.db.reuse_relation_tree is None
        assert self.db.auto_static_enabled is None
        assert self.db.localizer is not None

        
        
