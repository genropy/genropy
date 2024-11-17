import sys
import os.path
from collections import defaultdict

import gnr.web.gnrwebpage as gwp
import gnr.web.gnrwebpage_proxy.jstools as jst

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from tests.app.common import BaseGnrAppTest

class MockRequest(object):
    def __init__(self, attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

class MockResponse(object):
    def __init__(self):
        self.headers = {}

class MockRegister(object):
    def connection(self, connection):
        return dict(user=None, user_tags='', user_id=0, user_name="pytest")
    def new_page(self, page_id, item, data=None):
        return dict(page_id=page_id, data=data)

class MockPath(object):
    def __init__(self, path):
        self.mock_path = path
    def path(self, *args):
        
        p = [self.mock_path]
        p.extend(args)
        return os.path.join(*p)
    
    def url(self, *args):
        p = ['/']
        p.extend(args)
        return os.path.join(*p)
    
class MockSite(object):
    def __init__(self, name, app):
        _test_base_dir = os.path.join(os.path.dirname(__file__), "datafiles")
        self.name = name
        self.config = Bag(defaultdict(str))
        self.currentPage = None
        self.gnrapp = app
        self.extraFeatures = dict()
        self.site_path = os.path.join(_test_base_dir, "site")
        self.pages_dir = os.path.join(_test_base_dir, "pages")
        self.filepath = os.path.join(_test_base_dir, "files")
        self.register  = MockRegister()
        self.wsk = None
        
    def getStatic(self, site_name):
        return MockPath(self.site_path)
        
class TestJsTools(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.data_path = os.path.join(os.path.dirname(__file__), "datafiles")

    def _get_file_path(self, filename):
        return os.path.join(self.data_path, filename)
    
    def test_jsmin(self):
        app = GnrApp("gnrdevelop")
        mocksite = MockSite("mysite", app=app)
        page = gwp.GnrWebPage(site=mocksite,
                              filepath=mocksite.filepath,
                              request=MockRequest(dict(user_agent="pippo", url="/",
                                                       url_root="/",
                                                       remote_addr="127.0.0.1",
                                                       headers={})),
                              response=MockResponse(),
                              request_kwargs={"_connection_id": 1})
        tools = jst.GnrWebJSTools(page)

        #files_to_test = list(map(self._get_file_path, ["1.js", "2.js", "3.js"]))
        #tools.closurecompile(files_to_test)
            
        
        
