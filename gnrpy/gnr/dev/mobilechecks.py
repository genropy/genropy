import inspect
import requests

class MobileAppChecks(object):
    """
    This object will perform configuration and deployment tests
    to verify that all of the mobile-app related configuration are in place
    """

    def __init__(self, site, base_url=None):
        self.site = site
        # FIXME: if base_url is not provided, retrieve from
        # configuration or from running site
        self.base_url = base_url if base_url else self.site.config.getNode("wsgi").getAttr("external_host")

    def _verify_config_item(self, path):
        status = True
        description = "Path presence confirmed"
        if not self.site.gnrapp.config.getNode(path):
            status = False
            description = "Path configuration is missing"
        return (status, description)

    def test_ios_config(self):
        """'mobile_app.ios' path presence in instance configuration """
        return self._verify_config_item("mobile_app.ios")

    def test_android_config(self):
        """'mobile_app.android' path presence in instance configuration """
        return self._verify_config_item("mobile_app.android")

    def _verify_url_presence(self, sub_path):
        final_url = self.base_url + sub_path
        try:
            r = requests.get(final_url)
            return (r.ok, r.reason)
        except:
            return (False, "Test error - can't connect to verify")

    def test_main_cordova_ios_assets(self):
        """Verify Cordova IOS assets deployment"""
        sub_path = "/_cordova_asset/ios/cordova.js"
        return self._verify_url_presence(sub_path)
    
    def test_multisite_cordova_ios_assets(self):
        """Verify Multi-Site Cordova IOS assets deployment"""
        sub_path = "/_cordova_asset/ios/cordova.js"
        return self._verify_url_presence(sub_path)
    
    def test_ios_deeplinking(self):
        """Verify IOS deeplinking deployment"""
        sub_path = "/.well-known/apple-app-site-association"
        return self._verify_url_presence(sub_path)

    def test_android_deeplinking(self):
        """Verify Android deeplinking deployment"""
        sub_path = "/.well-known/apple-app-site-association"
        return self._verify_url_presence(sub_path)
    
        
    def run(self):
        """
        Execute all the tests
        """
        results = {}
        # Retrieve all test methods
        methods = [
            getattr(self, name) for name in dir(self)
            if name.startswith("test_")
            and callable(getattr(self, name))
            and name != inspect.currentframe().f_code.co_name 
        ]
        for method in methods:
            result, description = method()
            results[method.__name__] = dict(test=method.__doc__,
                                            result = result,
                                            description = description)
        return results
        
    
