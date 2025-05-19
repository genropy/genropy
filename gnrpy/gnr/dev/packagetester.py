import os
from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.app.gnrapp import GnrApp
from gnr.lib.services import ServiceHandler, BaseServiceType

class PackageTester(object):
    @classmethod
    def setup_class(cls):
        cls.instance_name = os.environ.get("GNR_TESTING_INSTANCE_NAME")
        cls.site = GnrWsgiSite(cls.instance_name)
        cls.app = cls.site.db.application

    @classmethod
    def _get_base_service(cls, service_type, service_implementation,
                          service_name, **kwargs):
        sh = ServiceHandler(cls.site)
        service = sh.service_types[service_type]
        return service.implementations[service_implementation](cls.site, **kwargs)
    

    
