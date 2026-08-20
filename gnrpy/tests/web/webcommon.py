import os
import sys
import time
import shutil
import pytest
local_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(local_dir, ".."))

from core.common import BaseGnrTest
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

class BaseGnrDaemonTest(BaseGnrTest):
    """
    Base class for tests that needs a daemon running
    """
    @classmethod
    def setup_class(cls):
        if shutil.which("gnr") is None:
            # skip before super().setup_class(): nothing to clean up yet
            pytest.skip("gnr CLI not available in PATH")
        super().setup_class()
        cls.external = ExternalProcess(['gnr','web','daemon'], cwd=None)
        try:
            cls.external.start()
            cls.site_name = 'gnrdevelop'
            cls.site = get_waited_wsgisite(cls.site_name)
            cls.client = WSGITestClient(cls.site)
            cls.services_handler = cls.site.services_handler
        except Exception as e:
            # pytest.skip raises, so teardown_class would never run:
            # clean up the daemon and the temp conf dir first
            cls.teardown_class()
            pytest.skip(f"Daemon not available: {e}")

    @classmethod
    def teardown_class(cls):
        external = getattr(cls, "external", None)
        if external is not None:
            try:
                external.stop()
            finally:
                cls.external = None
        super().teardown_class()


    
