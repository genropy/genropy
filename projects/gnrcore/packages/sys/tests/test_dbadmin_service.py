import os
import sys
import pytest
from testing.postgresql import Postgresql
import psycopg

from gnr.dev.packagetester import PackageTester

excludewin32 = pytest.mark.skipif(sys.platform == "win32",
                                  reason="testing.postgresl doesn't run on Windows")

@excludewin32
class TestDbAdminService(PackageTester):
    
    @classmethod
    def setup_class(cls):
        super().setup_class()
        if "GITHUB_WORKFLOW" in os.environ:
            cls.pg_conf = dict(host="127.0.0.1",
                               port="5432",
                               user="postgres",
                               password="postgres")
        else:
            cls.pg_instance = Postgresql()
            cls.pg_conf = cls.pg_instance.dsn()

        cls.service = cls._get_base_service(
            service_type="dbadmin",
            service_implementation="postgres",
            service_name="testing",
            dbadmin_host=cls.pg_conf.get('host'),
            dbadmin_port=cls.pg_conf.get('port'),
            dbadmin_user=cls.pg_conf.get('user'),
            dbadmin_password=cls.pg_conf.get("password", 'user')
        )

    @classmethod    
    def teardown_class(cls):
        if not "GITHUB_WORKFLOW" in os.environ:
            cls.pg_instance.stop()

    def test_database_create_list_delete(self):
        NEW_DB_NAME = 'service_dbadmin_testing'

        dblist = self.service.database_list()
        assert NEW_DB_NAME not in dblist
        
        # create
        self.service.database_create(NEW_DB_NAME)
        dblist = self.service.database_list()
        assert NEW_DB_NAME in dblist

        # list
        assert isinstance(dblist, list)
        assert "postgres" in dblist

        # delete
        self.service.database_delete(NEW_DB_NAME)
        dblist = self.service.database_list()
        assert NEW_DB_NAME not in dblist
        
    def test_user_ops(self):
        NEW_USER = "KillerJoke"

        userlist = self.service.user_list()
        assert NEW_USER not in userlist
        # create
        self.service.user_create(NEW_USER)
        userlist = self.service.user_list()
        assert NEW_USER in userlist

        # change password
        self.service.user_change_password(NEW_USER, "antani")


        # permissions
        self.service.user_set_all_privileges(NEW_USER, "postgres")

        # delete

        # cant' be deleted due to object references
        with pytest.raises(psycopg.errors.DependentObjectsStillExist):
            self.service.user_delete(NEW_USER)
        userlist = self.service.user_list()
        assert NEW_USER in userlist

        NEW_USER2 = "KillerJoke2"
        self.service.user_create(NEW_USER2)
        userlist = self.service.user_list()
        assert NEW_USER2 in userlist
        self.service.user_delete(NEW_USER2)
        userlist = self.service.user_list()
        assert NEW_USER2 not in userlist
        
        

