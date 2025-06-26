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

    @classmethod
    def _get_base_service(cls, service_type, **kwargs):
        return cls.site.getService(service_type,
                                   **kwargs)

    @classmethod    
    def teardown_class(cls):
        if not "GITHUB_WORKFLOW" in os.environ:
            cls.pg_instance.stop()

     

