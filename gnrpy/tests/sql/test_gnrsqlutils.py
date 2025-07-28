from gnr.sql import gnrsqlutils as gsu # noqa: F401
from gnr.sql import gnrsql as gs
from .common import BaseGnrSqlTest

class TestGnrSqlUtils(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = gs.GnrSqlDb()

    def test_start(self):
        m = self.db.importModelFromDb()
        assert m is None
        
        # checker = gsu.SqlModelChecker(self.db)
        # modelChanges = checker.checkDb()
        # print(modelChanges)
        # modelBagChanges = checker.bagChanges
        # print(modelBagChanges)
        
        
        
