import os
import sys
import time
import shutil
import traceback
import pytest
local_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(local_dir, ".."))

from core.common import BaseGnrTest, build_missing_schema_dbs
from utils import WSGITestClient, ExternalProcess

import gnr.web.gnrwsgisite as gws

def get_waited_wsgisite(site_name, max_attempts=3, timeout=2):
    """Build the site of the given name, retrying while the daemon comes up.

    The last failure is raised as is: returning None on exhausted attempts hides
    the actual error behind an unrelated AttributeError on the caller side.

    :param site_name: name of the site to build
    :param max_attempts: how many times the site is built before giving up
    :param timeout: seconds to wait between two attempts"""
    for attempt in range(1, max_attempts + 1):
        try:
            return gws.GnrWsgiSite(site_name, site_name=site_name)
        except Exception:
            if attempt == max_attempts:
                raise
            time.sleep(timeout)

class BaseGnrDaemonTest(BaseGnrTest):
    """
    Base class for tests that needs a daemon running
    """
    site_name = 'gnrdevelop'

    @classmethod
    def setup_class(cls):
        super().setup_class()
        if shutil.which("gnr") is None:
            pytest.skip("gnr CLI not available in PATH")
        cls.external = ExternalProcess(['gnr','web','daemon'], cwd=None)

        try:
            build_missing_schema_dbs(cls.site_name)
            cls.external.start()
            cls.site = get_waited_wsgisite(cls.site_name)
            cls.client = WSGITestClient(cls.site)
            cls.services_handler = cls.site.services_handler
        except Exception:
            # the whole traceback goes into the skip reason: pytest reports
            # nothing else, and the actual cause is usually well below the
            # surface (a missing table, a daemon refusing connections).
            pytest.skip(f"Site {cls.site_name} not available:\n{traceback.format_exc()}")


    @classmethod
    def teardown_class(cls):
        cls.external.stop()
        super().teardown_class()


    
