import os
import os.path

from gnr.core.gnrbag import Bag


class InstanceMaker(object):
    """Handle the autocreation of the ``instances`` folder.

    To autocreate the ``instances`` folder, please type in your console::

        gnrmkinstance instancesname

    where ``instancesname`` is the name of your ``instances`` folder.
    """

    def __init__(
        self,
        instance_name,
        base_path=None,
        packages=None,
        authentication=True,
        authentication_pkg=None,
        db_dbname=None,
        db_implementation=None,
        db_host=None,
        db_port=None,
        db_user=None,
        db_password=None,
        use_dbstores=False,
        config=None,
        main_package=None,
    ):
        self.instance_name = instance_name
        self.base_path = base_path or "."
        self.packages = packages or []
        self.db_dbname = db_dbname or instance_name
        self.authentication = authentication
        self.main_package = main_package
        if self.authentication:
            self.authentication_pkg = authentication_pkg
            if not self.authentication_pkg and self.packages:
                package = self.packages[0]
                if isinstance(package, tuple) or isinstance(package, list):
                    package = package[0]
                self.authentication_pkg = package
            if not self.authentication_pkg:
                self.authentication_pkg = "adm"
        self.db_implementation = db_implementation
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.db_password = db_password
        self.use_dbstores = use_dbstores
        self.config = config
        self.instance_path = os.path.join(self.base_path, self.instance_name)
        self.config_path = os.path.join(self.instance_path, "config")

    def do(self):
        instanceconfig = self.do_instance()
        self.do_site(instanceconfig)
        instanceconfig_xml_path = os.path.join(self.config_path, "instanceconfig.xml")
        instanceconfig.toXml(instanceconfig_xml_path, typevalue=False, pretty=True)

    def do_instance(self):
        custom_path = os.path.join(self.instance_path, "custom")
        data_path = os.path.join(self.instance_path, "data")
        instanceconfig_xml_path = os.path.join(self.config_path, "instanceconfig.xml")
        folders_to_make = [self.instance_path, self.config_path, custom_path, data_path]
        if self.use_dbstores:
            dbstores_path = os.path.join(self.instance_path, "dbstores")
            folders_to_make.append(dbstores_path)
        for path in folders_to_make:
            if not os.path.isdir(path):
                os.makedirs(path, exist_ok=True)
        if not os.path.isfile(instanceconfig_xml_path):
            if not self.config:
                instanceconfig = Bag()
                db_options = dict()
                for option in (
                    "dbname",
                    "implementation",
                    "host",
                    "port",
                    "username",
                    "password",
                ):
                    value = getattr(self, "db_%s" % option, None)
                    if value:
                        db_options[option] = value
                instanceconfig.setItem("db", None, **db_options)
                instanceconfig.setItem("packages", None)
                for package in self.packages:
                    if isinstance(package, tuple) or isinstance(package, list):
                        package, package_path = package
                        instanceconfig.setItem(
                            "packages.%s" % package.replace(":", "_"),
                            None,
                            path=package_path,
                            pkgcode=package,
                        )
                    else:
                        instanceconfig.setItem(
                            "packages.%s" % package.replace(":", "_"),
                            None,
                            pkgcode=package,
                        )
                if self.authentication:
                    instanceconfig.setItem(
                        "authentication", None, pkg=self.authentication_pkg
                    )
                    instanceconfig.setItem(
                        "authentication.py_auth",
                        None,
                        defaultTags="user",
                        pkg="adm",
                        method="authenticate",
                    )
            else:
                instanceconfig = self.config
            return instanceconfig

    def do_site(self, instanceconfig):
        """TODO"""
        self.site_path = os.path.join(self.instance_path, "site")
        root_py_path = os.path.join(self.instance_path, "root.py")
        siteconfig_xml_path = os.path.join(self.config_path, "siteconfig.xml")
        if not os.path.isdir(self.site_path):
            os.makedirs(self.site_path, exist_ok=True)
        if not os.path.isfile(root_py_path):
            root_py = open(root_py_path, "w")
            root_py.write(
                """
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
                wsgi_options = dict()
                wsgi_options.setdefault("mainpackage", self.main_package)
                for option in ("reload", "debug", "port", "mainpackage"):
                    value = getattr(self, "wsgi_%s" % option, None)
                    if value:
                        wsgi_options[option] = value
                siteconfig.setItem("wsgi", None, **wsgi_options)
            else:
                siteconfig = self.config
            instanceconfig.addItem("site", siteconfig)
