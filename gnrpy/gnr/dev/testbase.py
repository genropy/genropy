import os
import sys
from testing.postgresql import Postgresql
import pytest


from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.lib.services import ServiceHandler

excludewin32 = pytest.mark.skipif(sys.platform == "win32",
                                  reason="testing.postgresql doesn't run on Windows")

@excludewin32
class DbBasedTest(object):
    @classmethod
    def setup_class(cls):
        cls.instance_name = os.environ.get("GNR_TESTING_INSTANCE_NAME")
        cls.site = GnrWsgiSite(cls.instance_name)
        cls.app = cls.site.db.application

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
    def _get_base_service(cls, service_type, service_implementation,
                          service_name, **kwargs):
        sh = ServiceHandler(cls.site)
        service = sh.service_types[service_type]
        return service.implementations[service_implementation](cls.site, **kwargs)
    

    @classmethod    
    def teardown_class(cls):
        if not "GITHUB_WORKFLOW" in os.environ:
            cls.pg_instance.stop()

     

