import os
import os.path


class PackageMaker(object):
    """Handle the autocreation of the ``packages`` folder.

    To autocreate the ``packages`` folder, please type in your console::

        gnr dev mkpackage packagesname

    where ``packagesname`` is the name of your ``packages`` folder.
    """

    def __init__(
        self,
        package_name,
        base_path=None,
        sqlschema=None,
        sqlprefix=True,
        name_short=None,
        name_long=None,
        name_full=None,
        login_url=None,
        comment=None,
        helloworld=False,
    ):
        self.package_name = package_name
        self.base_path = base_path or "."
        self.name_short = name_short or self.package_name.capitalize()
        self.name_full = name_full or self.package_name.capitalize()
        self.name_long = name_long or self.package_name.capitalize()
        self.sqlschema = sqlschema or self.package_name.lower()
        self.sqlprefix = sqlprefix
        self.comment = comment or "%s package" % self.package_name
        self.login_url = login_url or "%s/login" % self.package_name
        self.helloworld = helloworld
        self.package_path = os.path.join(self.base_path, self.package_name)
        self.model_path = os.path.join(self.package_path, "model")
        self.cli_path = os.path.join(self.package_path, "cli")
        self.lib_path = os.path.join(self.package_path, "lib")
        self.webpages_path = os.path.join(self.package_path, "webpages")
        self.resources_path = os.path.join(self.package_path, "resources")
        self.framedindex_path = os.path.join(self.webpages_path, "index.py")
        self.main_py_path = os.path.join(self.package_path, "main.py")

    def do(self):
        """Creates the files of the ``packages`` folder"""
        for path in (
            self.package_path,
            self.model_path,
            self.cli_path,
            self.lib_path,
            self.webpages_path,
            self.resources_path,
        ):
            if not os.path.isdir(path):
                os.makedirs(path, exist_ok=True)

        # create an emptydir file allowing an empty directory to be
        # pushed to repository
        for p in [self.cli_path, self.lib_path, self.resources_path, self.model_path]:
            open(os.path.join(p, ".emptydir"), "w").close()

        # create an empty requirements.txt file, hopefully developers
        # will be reminded by its presence that dependencies can be added
        # in this file
        open(os.path.join(self.package_path, "requirements.txt"), "w").close()

        # create an placeholder README.md file, since it's a policy
        # that has been established to have a README for each package
        # refs #83
        with open(os.path.join(self.package_path, "README.md"), "w") as readme_fp:
            head = f"Package '{self.package_name}'"
            readme_fp.write(head)
            readme_fp.write("\n")
            readme_fp.write("=" * len(head))

        sqlprefixstring = ""
        if not os.path.exists(self.main_py_path):
            if self.sqlprefix is not None:
                if self.sqlprefix not in (True, False):
                    self.sqlprefix = "'%s'" % self.sqlprefix
                sqlprefixstring = "sqlprefix=%s," % (self.sqlprefix)
            main_py_options = dict(
                comment=self.comment,
                sqlschema=self.sqlschema,
                sqlprefixstring=sqlprefixstring,
                name_short=self.name_short,
                name_long=self.name_long,
                name_full=self.name_full,
                login_url=self.login_url,
            )
            main_py = open(self.main_py_path, "w")
            main_py.write(
                """#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='%(comment)s',sqlschema='%(sqlschema)s',%(sqlprefixstring)s
                    name_short='%(name_short)s', name_long='%(name_long)s', name_full='%(name_full)s')
                    
    def config_db(self, pkg):
        pass
        
class Table(GnrDboTable):
    pass
"""
                % main_py_options
            )
            main_py.close()

        if not os.path.exists(self.framedindex_path):
            with open(self.framedindex_path, "w") as indexpage:
                indexpage.write(
                    """# -*- coding: utf-8 -*-
            
class GnrCustomWebPage(object):
    py_requires = 'plainindex'
    """
                )
        if self.helloworld:
            with open(
                os.path.join(self.webpages_path, "hello_world.py"), "w"
            ) as helloworld:
                helloworld.write(
                    """# -*- coding: utf-8 -*-
            
class GnrCustomWebPage(object):
    def main_root(self,root,**kwargs):
        root.h1('Hello world',text_align='center')
    """
                )
