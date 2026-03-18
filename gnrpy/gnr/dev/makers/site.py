import os
from gnr.core.gnrbag import Bag


class SiteMaker(object):
    # deprecated
    """Handle the autocreation of the ``sites`` folder.

    To autocreate the ``sites`` folder, please type in your console::

        gnrmksite sitesname

    where 'sitesname' is the name of your ``sites`` folder.
    """

    def __init__(
        self,
        site_name,
        base_path=None,
        resources=None,
        instance=None,
        dojo_version="11",
        wsgi_port=None,
        wsgi_reload=None,
        wsgi_mainpackage=None,
        wsgi_debug=None,
        config=None,
    ):
        self.site_name = site_name
        self.base_path = base_path or "."
        self.resources = resources or []
        self.instance = instance
        self.wsgi_port = wsgi_port
        self.wsgi_reload = wsgi_reload
        self.wsgi_mainpackage = wsgi_mainpackage
        self.wsgi_debug = wsgi_debug
        self.dojo_version = dojo_version
        self.config = config

    def do(self):
        """TODO"""
        self.site_path = os.path.join(self.base_path, self.site_name)
        pages_path = os.path.join(self.site_path, "pages")
        root_py_path = os.path.join(self.site_path, "root.py")
        siteconfig_xml_path = os.path.join(self.site_path, "siteconfig.xml")
        if not os.path.isdir(self.site_path):
            os.makedirs(self.site_path, exist_ok=True)
        if not os.path.isdir(pages_path):
            os.makedirs(pages_path, exist_ok=True)
        if not os.path.isfile(root_py_path):
            root_py = open(root_py_path, "w")
            root_py.write(
                """#!/usr/bin/env python2.6
import sys
sys.stdout = sys.stderr
from gnr.web.gnrwsgisite import GnrWsgiSite
site = GnrWsgiSite(__file__)

def application(environ,start_response):
    return site(environ,start_response)

if __name__ == '__main__':
    from gnr.web.server import NewServer
    server=NewServer(__file__)
    server.run()"""
            )
            root_py.close()
        if not os.path.isfile(siteconfig_xml_path):
            if not self.config:
                siteconfig = Bag()
                if self.instance:
                    siteconfig.setItem("instances.%s" % self.instance, None)
                for resource in self.resources:
                    if isinstance(resource, tuple) or isinstance(resource, list):
                        resource, resource_path = resource
                        siteconfig.setItem(
                            "resources.%s" % resource, None, path=resource_path
                        )
                    else:
                        siteconfig.setItem("resources.%s" % resource, None)
                wsgi_options = dict()
                for option in ("reload", "debug", "port", "mainpackage"):
                    value = getattr(self, "wsgi_%s" % option, None)
                    if value:
                        wsgi_options[option] = value
                siteconfig.setItem("wsgi", None, **wsgi_options)
                siteconfig["connection_timeout"] = None
                siteconfig["connection_refresh"] = None
                siteconfig.setItem("dojo", None, version=self.dojo_version)
            else:
                siteconfig = self.config
            siteconfig.toXml(siteconfig_xml_path, typevalue=False, pretty=True)
