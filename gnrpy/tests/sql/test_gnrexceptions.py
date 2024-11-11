from gnr.sql import gnrsql_exceptions as ge

class TestGnrSqlExceptions():
    obi_mesg = "hello:there8927U@#UJ@HK#!@"

    def test_main_exception(self):
        e = ge.GnrSqlException(self.obi_mesg)
        assert e.code == "GNRSQL-001"
        assert e.description == self.obi_mesg
        
    def test_nonexisting_exception(self):
        e = ge.GnrNonExistingDbException(self.obi_mesg)
        assert e.dbname == self.obi_mesg

    def test_excution_exception(self):
        something_sql = "SELECT * FROM sky;"
        something_params = dict(name="Ceres")
        e = ge.GnrSqlExecutionException("OB1", self.obi_mesg,
                                        something_sql, something_params)
        assert e.code == "OB1"
        assert e.message == self.obi_mesg
        assert e.sql == something_sql
        assert e.params == something_params 
