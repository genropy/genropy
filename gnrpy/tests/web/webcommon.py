import os
import sys
local_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(local_dir, ".."))

from core.common import BaseGnrTest # noqa
from utils import WSGITestClient, ExternalProcess

import gnr.web.gnrwsgisite as gws

def get_waited_wsgisite(site_name):
    max_attempts = 3
    attempt = 0
    timeout = 2
    
    while attempt < max_attempts:
        try:
            site = gws.GnrWsgiSite(site_name, site_name=site_name)
            return site
        except Exception as e:
            time.sleep(timeout)
            attempt += 1
    raise Exception(f"Can't connect to local daemon after {attempt} attempts")

class BaseGnrDaemonTest(BaseGnrTest):
    """
    Base class for tests that needs a daemon running
    """
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.external = ExternalProcess(['gnr','web','daemon'], cwd=None)

        try:
            cls.external.start()
            cls.site_name = 'gnrdevelop'
            cls.site = get_waited_wsgisite(cls.site_name)
            cls.client = WSGITestClient(cls.site)
            cls.services_handler = cls.site.services_handler
        except Exception as e:
            # re-raise to take care of the problem, but ensuring the external
            # process is being terminated.
            cls.teardown_class()
            raise
        
    @classmethod
    def teardown_class(cls):
        cls.external.stop()
        super().teardown_class()


    
